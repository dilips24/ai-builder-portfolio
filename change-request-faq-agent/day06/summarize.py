"""Summarize day06/results.csv into day06/summary.md.

One markdown table per mode x set (rule / llm / all columns). The `useful`
column is graded by hand: Y=1, P=0.5, N=0; blank rows are ignored.
No API calls.
"""

import argparse
import csv
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
USEFUL_SCORE = {"Y": 1.0, "P": 0.5, "N": 0.0}
MODES = ("router", "all_llm")
SETS = ("seen", "holdout")


def p95(values: list[float]) -> float:
    """Nearest-rank 95th percentile."""
    ordered = sorted(values)
    return ordered[max(math.ceil(0.95 * len(ordered)) - 1, 0)]


def column(rows: list[dict]) -> dict[str, str]:
    """Metric cells for one group of rows (one path, or all)."""
    if not rows:
        return {k: "-" for k in ("answers", "graded", "useful", "avg_lat", "p95_lat", "avg_cost")}
    scores = [USEFUL_SCORE[r["useful"].strip().upper()] for r in rows if r["useful"].strip().upper() in USEFUL_SCORE]
    latencies = [float(r["latency_ms"]) for r in rows]
    costs = [float(r["cost_usd"]) for r in rows]
    return {
        "answers": str(len(rows)),
        "graded": f"{len(scores)}/{len(rows)}",
        "useful": f"{sum(scores) / len(scores):.0%}" if scores else "n/a",
        "avg_lat": f"{sum(latencies) / len(latencies):,.0f}",
        "p95_lat": f"{p95(latencies):,.0f}",
        "avg_cost": f"${sum(costs) / len(costs):.6f}",
    }


def section(mode: str, set_name: str, rows: list[dict]) -> str:
    rule = [r for r in rows if r["path"] == "rule"]
    llm = [r for r in rows if r["path"] == "llm"]
    n = len(rows)
    total_cost = sum(float(r["cost_usd"]) for r in rows)
    blended = total_cost / n if n else 0.0
    # compare case-insensitively: Excel rewrites True as TRUE when the CSV is graded
    correct = sum(r["rule_category_correct"].strip().lower() == "true" for r in rule)
    precision = f"{correct}/{len(rule)} ({correct / len(rule):.0%})" if rule else "n/a"

    cols = {"Rule": column(rule), "LLM": column(llm), "All": column(rows)}
    labels = [
        ("Answers", "answers"),
        ("Graded", "graded"),
        ("Useful rate", "useful"),
        ("Avg latency (ms)", "avg_lat"),
        ("p95 latency (ms)", "p95_lat"),
        ("Avg cost / answer", "avg_cost"),
    ]
    lines = [
        f"### {mode} / {set_name}",
        "",
        f"Questions: {n} | answered by rules: {len(rule) / n:.0%} | rule precision (right category): {precision} | "
        f"blended cost / question: ${blended:.6f} | projected per 10,000 questions: ${blended * 10_000:,.2f}",
        "",
        "| Metric | Rule | LLM | All |",
        "|---|---|---|---|",
    ]
    for label, key in labels:
        lines.append(f"| {label} | " + " | ".join(cols[c][key] for c in ("Rule", "LLM", "All")) + " |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="src", type=Path, default=HERE / "results.csv")
    parser.add_argument("--out", type=Path, default=HERE / "summary.md")
    args = parser.parse_args()

    with args.src.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    parts = ["# Results summary", ""]
    for mode in MODES:
        for set_name in SETS:
            group = [r for r in rows if r["mode"] == mode and r["set"] == set_name]
            if group:
                parts += [section(mode, set_name, group), ""]
    parts += [
        "Notes:",
        "- Useful rate: graded by hand, Y=1, P=0.5, N=0; ungraded rows are excluded (see Graded).",
        "- Rule precision counts only whether the rule picked the expected category, not whether the answer helped.",
        "- p95 is nearest-rank; with fewer than 20 answers it is effectively the maximum.",
        "- Cost uses Claude Haiku 4.5 prices from `day04/router.py`. The 10,000-question projection assumes the same rules/LLM mix as this test set.",
        "",
    ]
    args.out.write_text("\n".join(parts), encoding="utf-8")
    print(f"Saved {args.out}")


if __name__ == "__main__":
    main()
