"""Cited answers from the runbook collection (retrieve top-k chunks, ask Haiku).

  python answer.py "question"
  python answer.py --all             run the questions in test_questions.json and
                                     write answers_v2.csv (blank correct/faithful columns
                                     for hand grading); shows call count and estimated
                                     cost first and asks to confirm
  --set S      with --all: tune, holdout or all (default all)
  --yes        skip the confirmation prompt for --all
  --k N        number of chunks to retrieve (default 3)
  --max-distance D   distance gate (default 1.20): if the best retrieved chunk is
                     farther than D, skip the LLM and answer coverage "none"

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
from typing import Literal

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel

from search import QUESTIONS_FILE, open_collection, retrieve

HERE = Path(__file__).resolve().parent
ENV_FILE = HERE.parent / ".env"  # .env lives at the repo root, same as the FAQ agent

MODEL = "claude-haiku-4-5"
MAX_TOKENS = 800
EST_OUTPUT_TOKENS = 250  # per-call guess, only used for the pre-run cost estimate
MAX_DISTANCE = 1.20
GATE_ANSWER = "No runbook matched this closely enough."
ANSWERS_CSV = HERE / "answers_v2.csv"  # answers.csv is the v1 run (answerable column), kept as is
CSV_COLUMNS = [
    "id", "question", "set", "expected_docs", "retrieved_chunk_ids", "path", "best_distance", "coverage",
    "answer", "citations", "invalid_citations", "input_tokens", "output_tokens", "latency_ms", "cost_usd",
    "correct", "faithful",
]
TEMPERATURE = 0
PRICE_IN_PER_M = 1.00
PRICE_OUT_PER_M = 5.00

SYSTEM_PROMPT = """You are an assistant for on-call engineers. You answer questions using ONLY the runbook chunks provided in the user message. Never use general knowledge.

If the input is a ticket-style or incident description rather than a question, treat it as the question "How do I diagnose and resolve this?".

Rules:
- Put a citation like [RB-008#2] (the chunk id) after every factual statement.
- Set coverage to one of:
  - "full": the chunks answer the question. Give a short, cited, step-by-step answer.
  - "partial": the chunks answer only part of it. Say what the chunks DO cover (with citations), then say what is missing (the missing part is not cited). Add no steps, advice or facts from general knowledge for the missing part.
  - "none": the chunks do not contain the answer. Leave citations empty and make the answer exactly this and nothing more:
  "The runbooks don't answer this question.
  Possibly related:
  - <doc_id>: <title>
  - ..."
For "none", list only retrieved documents (one line per distinct doc_id, title from the chunk header) that are genuinely about the same system or symptom as the question AND have a chunk with distance at or below {max_distance} (each chunk shows its distance). If the question is off-topic for the runbooks (e.g. not about telecom operations at all), or no document qualifies, write only the first line and omit the "Possibly related:" list entirely. Do NOT explain why they don't answer it, do NOT say what the engineer should check or determine, and give no advice, steps or suggestions from general knowledge. Do not guess and do not use chunks that are unrelated to the question.
- Never use a chunk from a document marked SUPERSEDED. If chunks conflict, prefer the one with the newest last_updated (shown on each chunk) and say so.
- Keep answers short and step-by-step, written for an engineer working an incident.
- citations must list every chunk id you cited in the answer."""


class RunbookAnswer(BaseModel):
    coverage: Literal["full", "partial", "none"]
    answer: str
    citations: list[str]


def system_prompt(max_distance):
    return SYSTEM_PROMPT.replace("{max_distance}", f"{max_distance:g}")


def last_updated_by_chunk(collection, hits):
    """chunk_id -> last_updated (retrieve() doesn't return it, so read it from the collection)."""
    got = collection.get(ids=[h["chunk_id"] for h in hits], include=["metadatas"])
    return {cid: m.get("last_updated", "unknown") for cid, m in zip(got["ids"], got["metadatas"])}


def build_user_message(question, hits, updated):
    chunks = "\n\n".join(
        f'<chunk id="{h["chunk_id"]}" last_updated="{updated[h["chunk_id"]]}" distance="{h["distance"]:.3f}">\n'
        f'{h["text"]}\n</chunk>'
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


def best_distance(hits):
    return min((h["distance"] for h in hits), default=float("inf"))


def limit_related(answer, hits, max_distance):
    """Drop 'Possibly related' lines for docs with no chunk at or below max_distance (and the header if none remain)."""
    near = {h["doc_id"] for h in hits if h["distance"] <= max_distance}
    lines = answer.split("\n")
    out, in_list, kept = [], False, 0
    for line in lines:
        if line.strip().lower().startswith("possibly related"):
            in_list = True
            out.append(line)
            continue
        m = re.match(r"\s*-\s*([A-Za-z]+-\d+)", line) if in_list else None
        if m:
            if m.group(1) in near:
                out.append(line)
                kept += 1
            continue
        out.append(line)
    if in_list and kept == 0:
        out = [l for l in out if not l.strip().lower().startswith("possibly related")]
    return "\n".join(out).rstrip()


def cost_usd(in_tok, out_tok):
    return in_tok / 1e6 * PRICE_IN_PER_M + out_tok / 1e6 * PRICE_OUT_PER_M


def answer_question(client, question, hits, updated, max_distance):
    """Gate on the best distance, else one Haiku call over the retrieved chunks.

    Returns a dict with path ("gate" or "llm"); result is None if the reply could not be parsed.
    """
    best = best_distance(hits)
    if best > max_distance:
        return {
            "path": "gate",
            "best_distance": best,
            "result": RunbookAnswer(coverage="none", answer=GATE_ANSWER, citations=[]),
            "stop_reason": "gate",
            "in_tok": 0,
            "out_tok": 0,
            "latency": 0.0,
            "cost": 0.0,
        }

    start = time.perf_counter()
    response = client.messages.parse(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt(max_distance),
        messages=[{"role": "user", "content": build_user_message(question, hits, updated)}],
        output_format=RunbookAnswer,
        extra_body={"temperature": TEMPERATURE},
    )
    latency = time.perf_counter() - start
    in_tok, out_tok = response.usage.input_tokens, response.usage.output_tokens
    result = response.parsed_output
    if result is not None and result.coverage == "none":
        result.answer = limit_related(result.answer, hits, max_distance)
    return {
        "path": "llm",
        "best_distance": best,
        "result": result,
        "stop_reason": response.stop_reason,
        "in_tok": in_tok,
        "out_tok": out_tok,
        "latency": latency,
        "cost": cost_usd(in_tok, out_tok),
    }


def print_single(client, collection, question, k, max_distance):
    hits = retrieve(collection, question, k)
    by_id = {h["chunk_id"]: h for h in hits}
    updated = last_updated_by_chunk(collection, hits)
    try:
        out = answer_question(client, question, hits, updated, max_distance)
    except anthropic.AuthenticationError:
        sys.exit("The API rejected ANTHROPIC_API_KEY. Check the key in .env.")

    result = out["result"]
    if result is None:
        sys.exit(f"Could not parse a structured answer (stop_reason={out['stop_reason']}).")
    invalid = find_invalid_citations(result, set(by_id))

    print(f"Question: {question}\n")
    print(f"Path: {out['path']} | best distance {out['best_distance']:.3f} | Coverage: {result.coverage}\n")
    print(result.answer)

    if result.coverage in ("full", "partial"):
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
    """True if an existing answers CSV has any value in the correct/faithful columns."""
    if not path.exists():
        return False
    with path.open(newline="", encoding="utf-8-sig") as f:
        return any((row.get("correct") or "").strip() or (row.get("faithful") or "").strip()
                   for row in csv.DictReader(f))


def run_all(client, collection, k, yes, max_distance, question_set):
    questions = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
    if question_set != "all":
        questions = [q for q in questions if q.get("set") == question_set]
    if not questions:
        sys.exit(f"No questions in set '{question_set}'.")

    # Retrieval is local and free, so do it up front to estimate the LLM cost before spending anything.
    prepared = []
    est_in = 0
    llm_calls = 0
    for q in questions:
        hits = retrieve(collection, q["question"], k)
        updated = last_updated_by_chunk(collection, hits)
        if best_distance(hits) <= max_distance:
            message = build_user_message(q["question"], hits, updated)
            est_in += (len(system_prompt(max_distance)) + len(message)) // 4
            llm_calls += 1
        prepared.append((q, hits, updated))
    est_out = EST_OUTPUT_TOKENS * llm_calls
    print(f"{len(questions)} questions (set={question_set}): {llm_calls} LLM calls ({MODEL}), "
          f"{len(questions) - llm_calls} gated at distance > {max_distance:g}; "
          f"est. ~{est_in} input / ~{est_out} output tokens (chars/4 estimate), "
          f"est. cost ${cost_usd(est_in, est_out):.4f}")
    if not yes and input("Proceed? [y/N] ").strip().lower() != "y":
        sys.exit("Cancelled.")
    if has_hand_grades(ANSWERS_CSV):
        # Deliberately not skipped by --yes: this would destroy manual work.
        reply = input(f"{ANSWERS_CSV.name} has hand grades that will be overwritten. Continue? [y/N] ")
        if reply.strip().lower() != "y":
            sys.exit(f"Cancelled; {ANSWERS_CSV.name} left untouched.")

    rows = []
    total_cost = total_latency = total_in = total_invalid = 0
    for q, hits, updated in prepared:
        by_id = {h["chunk_id"]: h for h in hits}
        try:
            out = answer_question(client, q["question"], hits, updated, max_distance)
        except anthropic.AuthenticationError:
            sys.exit("The API rejected ANTHROPIC_API_KEY. Check the key in .env.")
        except anthropic.APIError as e:
            out = {"path": "llm", "best_distance": best_distance(hits), "result": None,
                   "stop_reason": f"API error: {e}", "in_tok": 0, "out_tok": 0, "latency": 0.0, "cost": 0.0}

        result = out["result"]
        if result is None:
            coverage, answer, citations, invalid = "", f"ERROR: no parsed answer ({out['stop_reason']})", [], []
        else:
            coverage = result.coverage
            answer, citations = result.answer, result.citations
            invalid = find_invalid_citations(result, set(by_id))

        total_cost += out["cost"]
        total_latency += out["latency"]
        total_in += out["in_tok"]
        total_invalid += len(invalid)
        rows.append({
            "id": q["id"],
            "question": q["question"],
            "set": q.get("set", ""),
            "expected_docs": ";".join(q["expected_docs"]),
            "retrieved_chunk_ids": ";".join(h["chunk_id"] for h in hits),
            "path": out["path"],
            "best_distance": f"{out['best_distance']:.3f}",
            "coverage": coverage,
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
        print(f"{q['id']:<7}path={out['path']:<5} best={out['best_distance']:.3f} coverage={coverage or '?':<8} "
              f"citations={len(citations)} invalid={len(invalid)} latency={out['latency']:.2f}s")

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
    parser.add_argument("--all", action="store_true", help="run the questions in test_questions.json")
    parser.add_argument("--set", dest="question_set", choices=["tune", "holdout", "all"], default="all",
                        help="with --all: which question set to run (default all)")
    parser.add_argument("--yes", action="store_true", help="skip the cost confirmation for --all")
    parser.add_argument("--k", type=int, default=3, help="number of chunks to retrieve (default 3)")
    parser.add_argument("--max-distance", type=float, default=MAX_DISTANCE,
                        help=f"skip the LLM when the best chunk is farther than this (default {MAX_DISTANCE:g})")
    args = parser.parse_args()
    if not args.question and not args.all:
        parser.error("give a question or --all")
    if args.k < 1:
        parser.error("--k must be at least 1")
    if args.max_distance <= 0:
        parser.error("--max-distance must be positive")

    load_dotenv(ENV_FILE)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit(f"ANTHROPIC_API_KEY not set. Add it to {ENV_FILE}.")

    collection = open_collection()
    client = anthropic.Anthropic(api_key=api_key)
    if args.all:
        run_all(client, collection, args.k, args.yes, args.max_distance, args.question_set)
    else:
        print_single(client, collection, args.question, args.k, args.max_distance)


if __name__ == "__main__":
    main()
