"""Route every FAQ in day03/faqs.json: rules first, LLM fallback.

Normalize the question (lowercase, strip punctuation) and test it against the
keyword/regex rules in rules.json. Exactly one matching category -> canned
answer (path=rule, no API call). Zero or 2+ matching categories -> Haiku with
policy.md as the system prompt (path=llm).

Prints per-question results and a summary, and saves router_log.csv.
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

MODEL = "claude-haiku-4-5"
MAX_TOKENS = 300
TEMPERATURE = 0
# USD per million tokens for Claude Haiku 4.5. Verify against current pricing.
INPUT_PRICE_PER_MTOK = 1.00
OUTPUT_PRICE_PER_MTOK = 5.00

HERE = Path(__file__).resolve().parent
FAQS_PATH = HERE.parent / "day03" / "faqs.json"
RULES_PATH = HERE / "rules.json"
POLICY_PATH = HERE / "policy.md"
LOG_PATH = HERE / "router_log.csv"

LLM_INSTRUCTION = "\n\nAnswer in 2-3 sentences, only from the policy."


def normalize(question: str) -> str:
    """Lowercase, replace punctuation with spaces, collapse whitespace."""
    text = re.sub(r"[^\w\s]", " ", question.lower())
    return re.sub(r"\s+", " ", text).strip()


def load_rules() -> dict[str, dict]:
    """Load rules.json and compile every pattern (a bad regex fails here, at startup)."""
    raw = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    return {
        category: {
            "patterns": [re.compile(p) for p in rule["patterns"]],
            "answer": rule["answer"],
        }
        for category, rule in raw.items()
    }


def match_categories(normalized: str, rules: dict[str, dict]) -> list[str]:
    return [
        category
        for category, rule in rules.items()
        if any(p.search(normalized) for p in rule["patterns"])
    ]


def get_client() -> anthropic.Anthropic:
    load_dotenv(HERE.parent / ".env")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit(
            "Error: ANTHROPIC_API_KEY is not set. Add a line "
            "ANTHROPIC_API_KEY=<your key> to the .env file in the "
            "ai-builder-portfolio folder."
        )
    return anthropic.Anthropic(api_key=api_key)


def ask_llm(client: anthropic.Anthropic, policy: str, question: str):
    """Return (answer, input_tokens, output_tokens)."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=policy + LLM_INSTRUCTION,
        messages=[{"role": "user", "content": question}],
        extra_body={"temperature": TEMPERATURE},
    )
    text = "".join(b.text for b in response.content if b.type == "text")
    return text.strip(), response.usage.input_tokens, response.usage.output_tokens


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--faqs",
        type=Path,
        default=FAQS_PATH,
        help="JSON file of questions (default: day03/faqs.json)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=LOG_PATH,
        help="CSV log to write (default: day04/router_log.csv)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # ✓/✗ must print when piped on Windows

    rules = load_rules()
    policy = POLICY_PATH.read_text(encoding="utf-8")
    faqs = json.loads(args.faqs.read_text(encoding="utf-8"))
    client = None  # created on the first LLM call, so an all-rules run needs no key

    print(f"Model: {MODEL} | temperature: {TEMPERATURE} | questions: {len(faqs)}\n")

    rows = []
    for faq in faqs:
        question = faq["question"]
        expected = faq["expected_category"]
        start = time.perf_counter()
        matched = match_categories(normalize(question), rules)

        if len(matched) == 1:
            path = "rule"
            answer = rules[matched[0]]["answer"]
            input_tokens = output_tokens = 0
            rule_correct = matched[0] == expected
        else:
            path = "llm"
            rule_correct = ""
            if client is None:
                client = get_client()
            try:
                answer, input_tokens, output_tokens = ask_llm(client, policy, question)
            except anthropic.AuthenticationError:
                sys.exit("Error: the API rejected ANTHROPIC_API_KEY. Check the key in .env.")
            except anthropic.APIError as e:
                sys.exit(f"Error: API call failed ({type(e).__name__}): {e.message}")
        latency_ms = (time.perf_counter() - start) * 1000

        cost = (
            input_tokens / 1_000_000 * INPUT_PRICE_PER_MTOK
            + output_tokens / 1_000_000 * OUTPUT_PRICE_PER_MTOK
        )
        rows.append(
            {
                "id": faq["id"],
                "question": question,
                "path": path,
                "matched_categories": "|".join(matched),
                "expected_category": expected,
                "rule_correct": rule_correct,
                "latency_ms": round(latency_ms),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": round(cost, 6),
                "answer": answer,
            }
        )
        mark = "" if path == "llm" else ("✓" if rule_correct else "✗")
        print(
            f"{faq['id']}  path={path:<4} matched={'|'.join(matched) or '-':<40} "
            f"expected={expected:<24} {mark}"
        )

    with args.out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    n = len(rows)
    rule_rows = [r for r in rows if r["path"] == "rule"]
    llm_rows = [r for r in rows if r["path"] == "llm"]
    rule_correct_count = sum(r["rule_correct"] is True for r in rule_rows)

    print(f"\nAnswered by rules:  {len(rule_rows)}/{n} ({len(rule_rows) / n:.0%})")
    if rule_rows:
        print(
            f"Rule precision:     {rule_correct_count}/{len(rule_rows)} "
            f"({rule_correct_count / len(rule_rows):.0%})"
        )
    else:
        print("Rule precision:     n/a (no rule answers)")
    for name, group in (("rule", rule_rows), ("llm", llm_rows)):
        if group:
            avg_latency = sum(r["latency_ms"] for r in group) / len(group)
            total_cost = sum(r["cost_usd"] for r in group)
            print(
                f"Path {name:<4}: {len(group):>2} questions | avg latency {avg_latency:.0f} ms "
                f"| total cost ${total_cost:.6f}"
            )
        else:
            print(f"Path {name:<4}:  0 questions | avg latency n/a | total cost $0.000000")
    print(f"\nSaved {args.out}")


if __name__ == "__main__":
    main()
