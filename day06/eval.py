"""Measure the FAQ Agent: hybrid router vs. all-LLM on the seen and holdout questions.

Every question is run twice through router.route():
  mode "router"  - the normal rules from rules.json (LLM fallback)
  mode "all_llm" - an empty rules dict, so everything goes to Haiku

Writes results.csv (the `useful` column is left blank for hand grading: Y / P / N).
Before any API call it prints the number of LLM calls and an estimated cost, and
asks for confirmation (pass --yes to skip the prompt).
"""

import argparse
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "day04"))

from router import (  # noqa: E402
    FAQS_PATH,
    INPUT_PRICE_PER_MTOK,
    LLM_INSTRUCTION,
    MAX_TOKENS,
    MODEL,
    OUTPUT_PRICE_PER_MTOK,
    compute_cost,
    get_client,
    load_policy,
    load_rules,
    match_categories,
    normalize,
    route,
)

HOLDOUT_PATH = HERE.parent / "day04" / "holdout.json"
OUT_PATH = HERE / "results.csv"

CHARS_PER_TOKEN = 4  # rough estimate for English text
TYPICAL_OUTPUT_TOKENS = 100  # answers are 2-3 sentences

COLUMNS = [
    "id", "set", "mode", "question", "expected_category", "path",
    "matched_categories", "rule_category_correct", "answer", "latency_ms",
    "input_tokens", "output_tokens", "cost_usd", "useful",
]


def load_questions() -> list[tuple[str, dict]]:
    """Return (set_name, faq) pairs: seen first, then holdout."""
    pairs = []
    for set_name, path in (("seen", FAQS_PATH), ("holdout", HOLDOUT_PATH)):
        for faq in json.loads(path.read_text(encoding="utf-8")):
            pairs.append((set_name, faq))
    return pairs


def estimate(questions, rules, policy) -> tuple[int, float, float]:
    """Return (llm_calls, typical_cost, worst_case_cost). No API calls."""
    calls = 0
    input_tokens = 0
    for _, faq in questions:
        q = faq["question"]
        # all_llm mode always calls the LLM; router mode only when not exactly 1 match
        n = 1 + (len(match_categories(normalize(q), rules)) != 1)
        calls += n
        chars = len(policy) + len(LLM_INSTRUCTION) + len(q)
        input_tokens += n * chars // CHARS_PER_TOKEN
    typical = compute_cost(input_tokens, calls * TYPICAL_OUTPUT_TOKENS)
    worst = compute_cost(input_tokens, calls * MAX_TOKENS)
    return calls, typical, worst


def write_csv(path: Path, rows: list[dict]) -> None:
    # utf-8-sig so Excel opens non-ASCII characters in answers correctly
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    parser.add_argument("--out", type=Path, default=OUT_PATH, help="CSV to write")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    rules = load_rules()
    policy = load_policy()
    questions = load_questions()
    modes = (("router", rules), ("all_llm", {}))

    calls, typical, worst = estimate(questions, rules, policy)
    print(f"Model: {MODEL} | questions: {len(questions)} x {len(modes)} modes = {len(questions) * len(modes)} rows")
    print(f"LLM calls: {calls}")
    print(f"Estimated cost: ~${typical:.4f} (worst case ${worst:.4f} if every answer hits {MAX_TOKENS} tokens)")
    print(f"(prices: ${INPUT_PRICE_PER_MTOK}/MTok in, ${OUTPUT_PRICE_PER_MTOK}/MTok out; token counts are estimates)")
    if not args.yes and input("Continue? [y/N] ").strip().lower() not in ("y", "yes"):
        print("Aborted; nothing written.")
        return

    client = get_client() if calls else None
    rows = []
    try:
        for set_name, faq in questions:
            for mode, mode_rules in modes:
                result = route(faq["question"], mode_rules, policy, client)
                path = result["path"]
                matched = result["matched_categories"]
                rows.append({
                    "id": faq["id"],
                    "set": set_name,
                    "mode": mode,
                    "question": faq["question"],
                    "expected_category": faq["expected_category"],
                    "path": path,
                    "matched_categories": "|".join(matched),
                    "rule_category_correct": (matched[0] == faq["expected_category"]) if path == "rule" else "",
                    "answer": result["answer"],
                    "latency_ms": round(result["latency_ms"]),
                    "input_tokens": result["input_tokens"],
                    "output_tokens": result["output_tokens"],
                    "cost_usd": round(result["cost_usd"], 6),
                    "useful": "",
                })
                print(f"{faq['id']:<8} {mode:<8} path={path}")
    except SystemExit as e:  # route() exits on API errors; keep the rows finished so far
        write_csv(args.out, rows)
        print(f"\nStopped after {len(rows)} rows ({e}). Partial results saved to {args.out}")
        sys.exit(1)

    write_csv(args.out, rows)

    print(f"\nSaved {len(rows)} rows to {args.out}")
    total_in = sum(r["input_tokens"] for r in rows)
    total_out = sum(r["output_tokens"] for r in rows)
    print(f"Actual LLM calls: {sum(r['path'] == 'llm' for r in rows)} | tokens in/out: {total_in}/{total_out} "
          f"| cost ${sum(r['cost_usd'] for r in rows):.6f}")
    for mode, _ in modes:
        group = [r for r in rows if r["mode"] == mode]
        rule_rows = [r for r in group if r["path"] == "rule"]
        correct = sum(r["rule_category_correct"] is True for r in rule_rows)
        line = f"{mode:<8}: {len(rule_rows)} rule / {len(group) - len(rule_rows)} llm"
        if rule_rows:
            line += f" | rule precision {correct}/{len(rule_rows)}"
        print(line)


if __name__ == "__main__":
    main()
