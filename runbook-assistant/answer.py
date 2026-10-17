"""Cited answers from the runbook collection (retrieve top-k chunks, ask Haiku).

  python answer.py "question"
  python answer.py --all             run every question in test_questions.json and
                                     write answers.csv (blank correct/faithful columns
                                     for hand grading); shows call count and estimated
                                     cost first and asks to confirm
  --yes        skip the confirmation prompt for --all
  --k N        number of chunks to retrieve (default 3)

Answers only from the retrieved chunks, cites chunk ids, and checks every
citation against the chunks that were actually retrieved. Run `python ingest.py`
first to build the collection. Needs ANTHROPIC_API_KEY in the repo-root .env.
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel

from search import QUESTIONS_FILE, open_collection, retrieve

HERE = Path(__file__).resolve().parent
ENV_FILE = HERE.parent / ".env"  # .env lives at the repo root, same as the FAQ agent

MODEL = "claude-haiku-4-5"
MAX_TOKENS = 800
EST_OUTPUT_TOKENS = 250  # per-call guess, only used for the pre-run cost estimate
ANSWERS_CSV = HERE / "answers.csv"
CSV_COLUMNS = [
    "id", "question", "expected_docs", "retrieved_chunk_ids", "answerable", "answer", "citations",
    "invalid_citations", "input_tokens", "output_tokens", "latency_ms", "cost_usd", "correct", "faithful",
]
TEMPERATURE = 0
PRICE_IN_PER_M = 1.00
PRICE_OUT_PER_M = 5.00

SYSTEM_PROMPT = """You are an assistant for on-call engineers. You answer questions using ONLY the runbook chunks provided in the user message. Never use general knowledge.

Rules:
- Put a citation like [RB-008#2] (the chunk id) after every factual statement.
- If the chunks do not contain the answer, set answerable to false, leave citations empty, and make the answer exactly this and nothing more:
  "The runbooks don't answer this question.
  Possibly related:
  - <doc_id>: <title>
  - ..."
List only retrieved documents (one line per distinct doc_id, title from the chunk header) that are genuinely about the same system or symptom as the question. If the question is off-topic for the runbooks (e.g. not about telecom operations at all), or none of the documents is about the same system or symptom, write only the first line and omit the "Possibly related:" list entirely. Do NOT explain why they don't answer it, do NOT say what the engineer should check or determine, and give no advice, steps or suggestions from general knowledge. Do not guess and do not use chunks that are unrelated to the question.
- Never use a chunk from a document marked SUPERSEDED. If chunks conflict, prefer the one with the newest last_updated (shown on each chunk) and say so.
- Keep answers short and step-by-step, written for an engineer working an incident.
- citations must list every chunk id you cited in the answer."""


class RunbookAnswer(BaseModel):
    answerable: bool
    answer: str
    citations: list[str]


def last_updated_by_chunk(collection, hits):
    """chunk_id -> last_updated (retrieve() doesn't return it, so read it from the collection)."""
    got = collection.get(ids=[h["chunk_id"] for h in hits], include=["metadatas"])
    return {cid: m.get("last_updated", "unknown") for cid, m in zip(got["ids"], got["metadatas"])}


def build_user_message(question, hits, updated):
    chunks = "\n\n".join(
        f'<chunk id="{h["chunk_id"]}" last_updated="{updated[h["chunk_id"]]}">\n{h["text"]}\n</chunk>'
        for h in hits
    )
    return f"{chunks}\n\nQuestion: {question}"


def chunk_title(text):
    """Title from the '[id | title | section]' header line, or '' if absent."""
    first = text.split("\n", 1)[0]
    if first.startswith("[") and first.endswith("]"):
        parts = [p.strip() for p in first[1:-1].split("|")]
        if len(parts) >= 2:
            return parts[1]
    return ""


def find_invalid_citations(result, valid_ids):
    """Citations (listed or inline in the answer) that are not retrieved chunk ids."""
    inline = re.findall(r"\[([^\[\]]+)\]", result.answer)
    cited = list(result.citations) + [c.strip() for group in inline for c in group.split(",")]
    invalid = []
    for c in cited:
        if c not in valid_ids and c not in invalid:
            invalid.append(c)
    return invalid


def cost_usd(in_tok, out_tok):
    return in_tok / 1e6 * PRICE_IN_PER_M + out_tok / 1e6 * PRICE_OUT_PER_M


def answer_question(client, question, hits, updated):
    """One Haiku call over already-retrieved chunks; result is None if the reply could not be parsed."""
    start = time.perf_counter()
    response = client.messages.parse(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_message(question, hits, updated)}],
        output_format=RunbookAnswer,
        extra_body={"temperature": TEMPERATURE},
    )
    latency = time.perf_counter() - start
    in_tok, out_tok = response.usage.input_tokens, response.usage.output_tokens
    return {
        "result": response.parsed_output,
        "stop_reason": response.stop_reason,
        "in_tok": in_tok,
        "out_tok": out_tok,
        "latency": latency,
        "cost": cost_usd(in_tok, out_tok),
    }


def print_single(client, collection, question, k):
    hits = retrieve(collection, question, k)
    by_id = {h["chunk_id"]: h for h in hits}
    updated = last_updated_by_chunk(collection, hits)
    try:
        out = answer_question(client, question, hits, updated)
    except anthropic.AuthenticationError:
        sys.exit("The API rejected ANTHROPIC_API_KEY. Check the key in .env.")

    result = out["result"]
    if result is None:
        sys.exit(f"Could not parse a structured answer (stop_reason={out['stop_reason']}).")
    invalid = find_invalid_citations(result, set(by_id))

    print(f"Question: {question}\n")
    print(f"Answerable: {'yes' if result.answerable else 'no'}\n")
    print(result.answer)

    if result.answerable:
        print("\nSources:")
        for cid in result.citations:
            if cid in by_id:
                h = by_id[cid]
                title = chunk_title(h["text"])
                print(f"  {cid}: {h['doc_id']} | {title or '-'} | {h['section']}")
    if invalid:
        print(f"\nINVALID citations (not in retrieved chunks): {', '.join(invalid)}")

    print(f"\nTokens: {out['in_tok']} in / {out['out_tok']} out | latency {out['latency']:.2f}s | cost ${out['cost']:.6f}")


def has_hand_grades(path):
    """True if an existing answers.csv has any value in the correct/faithful columns."""
    if not path.exists():
        return False
    with path.open(newline="", encoding="utf-8-sig") as f:
        return any((row.get("correct") or "").strip() or (row.get("faithful") or "").strip()
                   for row in csv.DictReader(f))


def run_all(client, collection, k, yes):
    questions = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))

    # Retrieval is local and free, so do it up front to estimate the LLM cost before spending anything.
    prepared = []
    est_in = 0
    for q in questions:
        hits = retrieve(collection, q["question"], k)
        updated = last_updated_by_chunk(collection, hits)
        message = build_user_message(q["question"], hits, updated)
        est_in += (len(SYSTEM_PROMPT) + len(message)) // 4
        prepared.append((q, hits, updated))
    est_out = EST_OUTPUT_TOKENS * len(questions)
    print(f"{len(questions)} LLM calls ({MODEL}), est. ~{est_in} input / ~{est_out} output tokens "
          f"(chars/4 estimate), est. cost ${cost_usd(est_in, est_out):.4f}")
    if not yes and input("Proceed? [y/N] ").strip().lower() != "y":
        sys.exit("Cancelled.")
    if has_hand_grades(ANSWERS_CSV):
        # Deliberately not skipped by --yes: this would destroy manual work.
        reply = input(f"{ANSWERS_CSV.name} has hand grades that will be overwritten. Continue? [y/N] ")
        if reply.strip().lower() != "y":
            sys.exit("Cancelled; answers.csv left untouched.")

    rows = []
    total_cost = total_latency = total_in = total_invalid = 0
    for q, hits, updated in prepared:
        by_id = {h["chunk_id"]: h for h in hits}
        try:
            out = answer_question(client, q["question"], hits, updated)
        except anthropic.AuthenticationError:
            sys.exit("The API rejected ANTHROPIC_API_KEY. Check the key in .env.")
        except anthropic.APIError as e:
            out = {"result": None, "stop_reason": f"API error: {e}", "in_tok": 0, "out_tok": 0,
                   "latency": 0.0, "cost": 0.0}

        result = out["result"]
        if result is None:
            answerable, answer, citations, invalid = "", f"ERROR: no parsed answer ({out['stop_reason']})", [], []
        else:
            answerable = "yes" if result.answerable else "no"
            answer, citations = result.answer, result.citations
            invalid = find_invalid_citations(result, set(by_id))

        total_cost += out["cost"]
        total_latency += out["latency"]
        total_in += out["in_tok"]
        total_invalid += len(invalid)
        rows.append({
            "id": q["id"],
            "question": q["question"],
            "expected_docs": ";".join(q["expected_docs"]),
            "retrieved_chunk_ids": ";".join(h["chunk_id"] for h in hits),
            "answerable": answerable,
            "answer": answer,
            "citations": ";".join(citations),
            "invalid_citations": ";".join(invalid),
            "input_tokens": out["in_tok"],
            "output_tokens": out["out_tok"],
            "latency_ms": round(out["latency"] * 1000),
            "cost_usd": f"{out['cost']:.6f}",
            "correct": "",
            "faithful": "",
        })
        print(f"{q['id']:<7}answerable={answerable or '?':<4} citations={len(citations)} "
              f"invalid={len(invalid)} latency={out['latency']:.2f}s")

    with ANSWERS_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    n = len(rows)
    print(f"\nTotal cost ${total_cost:.6f} | avg latency {total_latency / n:.2f}s | "
          f"avg input tokens {total_in / n:.0f} | invalid citations {total_invalid}")
    print(f"Saved {ANSWERS_CSV}")


def main():
    parser = argparse.ArgumentParser(description="Cited answer from the runbook collection.")
    parser.add_argument("question", nargs="?", help="question to answer")
    parser.add_argument("--all", action="store_true", help="run every question in test_questions.json")
    parser.add_argument("--yes", action="store_true", help="skip the cost confirmation for --all")
    parser.add_argument("--k", type=int, default=3, help="number of chunks to retrieve (default 3)")
    args = parser.parse_args()
    if not args.question and not args.all:
        parser.error("give a question or --all")
    if args.k < 1:
        parser.error("--k must be at least 1")

    load_dotenv(ENV_FILE)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit(f"ANTHROPIC_API_KEY not set. Add it to {ENV_FILE}.")

    collection = open_collection()
    client = anthropic.Anthropic(api_key=api_key)
    if args.all:
        run_all(client, collection, args.k, args.yes)
    else:
        print_single(client, collection, args.question, args.k)


if __name__ == "__main__":
    main()
