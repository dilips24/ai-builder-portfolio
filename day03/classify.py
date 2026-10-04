"""Classify every FAQ in faqs.json into a category, with confidence and a reason.

--mode prompt: JSON is requested only in the system prompt and parsed with
               json.loads, so the output can be malformed.
--mode schema: native structured outputs via client.messages.parse with a
               Pydantic model whose category is a Literal.

Prints per-question results and a summary, and saves results_<mode>.csv.
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Literal, get_args

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field

MODEL = "claude-haiku-4-5"
MAX_TOKENS = 300
TEMPERATURE = 0
# USD per million tokens for Claude Haiku 4.5. Verify against current pricing.
INPUT_PRICE_PER_MTOK = 1.00
OUTPUT_PRICE_PER_MTOK = 5.00

HERE = Path(__file__).resolve().parent
FAQS_PATH = HERE / "faqs.json"

Category = Literal[
    "change_types",
    "lead_time_scheduling",
    "cab_approval",
    "emergency_change",
    "freeze_blackout",
    "rollback_backout",
    "documentation_templates",
    "out_of_scope",
]
CATEGORIES = get_args(Category)


class Classification(BaseModel):
    category: Category
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


BASE_PROMPT = (
    "You classify employee questions for a telecom IT Change Management FAQ. "
    "Pick exactly one category:\n"
    "- change_types: kinds of change (standard, normal, emergency) and which to use\n"
    "- lead_time_scheduling: submission lead times and maintenance-window timing\n"
    "- cab_approval: CAB meetings, agenda cutoffs and who must approve\n"
    "- emergency_change: raising or approving urgent changes during incidents/outages\n"
    "- freeze_blackout: change freezes, blackout periods and exceptions\n"
    "- rollback_backout: backout/rollback plans and rollback-vs-fix-forward decisions\n"
    "- documentation_templates: change request templates, forms and mandatory fields\n"
    "- out_of_scope: anything not about change management (HR, payroll, IT support)\n"
    "Give a confidence between 0.0 and 1.0 and a short reason (one sentence)."
)
PROMPT_MODE_SYSTEM = (
    BASE_PROMPT
    + "\nRespond with only a raw JSON object: no markdown, no code fences, no text "
    "before or after it. The first character of your reply must be { and the last "
    "must be }. Use exactly this form: "
    '{"category": "<one of the categories>", "confidence": <0.0-1.0>, '
    '"reason": "<short string>"}'
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=["prompt", "schema"],
        required=True,
        help="prompt: JSON asked for in the system prompt; schema: native structured outputs",
    )
    return parser.parse_args()


def classify_prompt(client: anthropic.Anthropic, question: str):
    """Return (result dict or None, raw output, input_tokens, output_tokens)."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=PROMPT_MODE_SYSTEM,
        messages=[{"role": "user", "content": question}],
        extra_body={"temperature": TEMPERATURE},
    )
    text = "".join(b.text for b in response.content if b.type == "text")
    try:
        data = json.loads(text)
        result = {
            "category": data["category"],
            "confidence": float(data["confidence"]),
            "reason": str(data["reason"]),
        }
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        result = None
    return result, text, response.usage.input_tokens, response.usage.output_tokens


def classify_schema(client: anthropic.Anthropic, question: str):
    """Return (result dict or None, raw output, input_tokens, output_tokens)."""
    response = client.messages.parse(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=BASE_PROMPT,
        messages=[{"role": "user", "content": question}],
        output_format=Classification,
        extra_body={"temperature": TEMPERATURE},
    )
    parsed = response.parsed_output
    result = parsed.model_dump() if parsed is not None else None
    raw = parsed.model_dump_json() if parsed is not None else ""
    return result, raw, response.usage.input_tokens, response.usage.output_tokens


def main() -> None:
    args = parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # ✓/✗ must print when piped on Windows

    load_dotenv(HERE.parent / ".env")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit(
            "Error: ANTHROPIC_API_KEY is not set. Add a line "
            "ANTHROPIC_API_KEY=<your key> to the .env file in the "
            "ai-builder-portfolio folder."
        )

    faqs = json.loads(FAQS_PATH.read_text(encoding="utf-8"))
    client = anthropic.Anthropic(api_key=api_key)
    classify = classify_prompt if args.mode == "prompt" else classify_schema

    print(f"Model: {MODEL} | mode: {args.mode} | temperature: {TEMPERATURE}\n")

    rows = []
    for faq in faqs:
        start = time.perf_counter()
        try:
            result, raw, input_tokens, output_tokens = classify(client, faq["question"])
        except anthropic.AuthenticationError:
            sys.exit("Error: the API rejected ANTHROPIC_API_KEY. Check the key in .env.")
        except anthropic.APIError as e:
            sys.exit(f"Error: API call failed ({type(e).__name__}): {e.message}")
        latency_ms = (time.perf_counter() - start) * 1000

        valid = result is not None
        predicted = result["category"] if valid else ""
        confidence = result["confidence"] if valid else 0.0
        reason = result["reason"] if valid else ""
        correct = valid and predicted == faq["expected_category"]
        cost = (
            input_tokens / 1_000_000 * INPUT_PRICE_PER_MTOK
            + output_tokens / 1_000_000 * OUTPUT_PRICE_PER_MTOK
        )
        rows.append(
            {
                "id": faq["id"],
                "question": faq["question"],
                "expected": faq["expected_category"],
                "predicted": predicted,
                "confidence": confidence,
                "reason": reason,
                "raw_output": raw,
                "valid_json": valid,
                "correct": correct,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "latency_ms": round(latency_ms),
                "cost_usd": round(cost, 6),
            }
        )
        mark = "✓" if correct else "✗"
        shown = predicted if valid else "INVALID"
        print(
            f"{faq['id']}  predicted={shown:<24} expected={faq['expected_category']:<24} "
            f"conf={confidence:.2f}  {mark}"
        )

    out_path = HERE / f"results_{args.mode}.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    n = len(rows)
    valid_count = sum(r["valid_json"] for r in rows)
    correct_rows = [r for r in rows if r["correct"]]
    wrong_rows = [r for r in rows if not r["correct"]]

    def avg_conf(group: list[dict]) -> str:
        return f"{sum(r['confidence'] for r in group) / len(group):.2f}" if group else "n/a"

    total_tokens = sum(r["input_tokens"] + r["output_tokens"] for r in rows)
    total_cost = sum(r["cost_usd"] for r in rows)
    avg_latency = sum(r["latency_ms"] for r in rows) / n

    print(f"\nValid JSON:               {valid_count}/{n}")
    print(f"Accuracy:                 {len(correct_rows)}/{n} ({len(correct_rows) / n:.0%})")
    print(f"Avg confidence (correct): {avg_conf(correct_rows)}")
    print(f"Avg confidence (wrong):   {avg_conf(wrong_rows)}")
    print(f"Total tokens:             {total_tokens}")
    print(f"Total cost:               ${total_cost:.6f}")
    print(f"Avg latency:              {avg_latency:.0f} ms")
    print(f"\nSaved {out_path}")


if __name__ == "__main__":
    main()
