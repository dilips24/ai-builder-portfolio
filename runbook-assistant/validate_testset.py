"""Validate test_questions.json against the corpus in data\\ (no LLM calls, no dependencies).

Errors (exit code 1): bad JSON, missing or mistyped fields, duplicate ids, unknown expected docs,
no_answer questions with expected_docs or must_include, non-no_answer questions with empty
expected_docs, answerable / superseded_trap questions with empty must_include.

Prints counts by type x set and by style, and which docs no question expects (coverage gaps).

  python validate_testset.py
  python validate_testset.py --file some_other_questions.json
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
QUESTIONS_FILE = HERE / "test_questions.json"
DATA_DIR = HERE / "data"

REQUIRED = ["id", "question", "expected_docs", "type", "style", "must_include", "set"]
TYPES = ["answerable", "no_answer", "superseded_trap", "ambiguous"]
STYLES = ["ticket", "question"]
SETS = ["tune", "holdout"]
MUST_HAVE_FACTS = {"answerable", "superseded_trap"}


def load_docs():
    """doc id -> True if the doc is marked superseded. INDEX.md is not a doc."""
    docs = {}
    for path in sorted(DATA_DIR.glob("*.md")):
        match = re.match(r"([A-Z]+-\d+)", path.name)
        if match:
            text = path.read_text(encoding="utf-8")
            docs[match.group(1)] = "SUPERSEDED by" in text
    return docs


def is_str_list(value):
    return isinstance(value, list) and all(isinstance(v, str) and v.strip() for v in value)


def check(questions, docs):
    errors = []

    def err(qid, message):
        errors.append(f"ERROR {qid}: {message}")

    ids = Counter(q.get("id") for q in questions if isinstance(q, dict))
    for qid, n in ids.items():
        if n > 1:
            err(qid, f"id appears {n} times")

    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            err(f"#{i}", "not a JSON object")
            continue
        qid = q.get("id") if isinstance(q.get("id"), str) and q.get("id") else f"#{i}"
        missing = [f for f in REQUIRED if f not in q]
        if missing:
            err(qid, f"missing field(s): {', '.join(missing)}")
        for field in ("id", "question"):
            if field in q and not (isinstance(q[field], str) and q[field].strip()):
                err(qid, f"{field} must be a non-empty string")
        for field in ("expected_docs", "must_include"):
            if field in q and not is_str_list(q[field]):
                err(qid, f"{field} must be a list of non-empty strings")
        for field, allowed in (("type", TYPES), ("style", STYLES), ("set", SETS)):
            if field in q and q[field] not in allowed:
                err(qid, f"{field} {q[field]!r} not in {allowed}")

        expected = q.get("expected_docs") if is_str_list(q.get("expected_docs")) else []
        must = q.get("must_include") if is_str_list(q.get("must_include")) else []
        for doc in expected:
            if doc not in docs:
                err(qid, f"expected doc {doc} not found in data\\")
        qtype = q.get("type")
        if qtype == "no_answer":
            if expected:
                err(qid, f"no_answer must have empty expected_docs, has {expected}")
            if must:
                err(qid, f"no_answer must have empty must_include, has {must}")
        elif "type" in q and "expected_docs" in q and not expected:
            err(qid, f"{qtype} must have at least one expected doc")
        if qtype in MUST_HAVE_FACTS and "must_include" in q and not must:
            err(qid, f"{qtype} must have at least one must_include fact")
    return errors


def summarize(questions, docs):
    valid = [q for q in questions if isinstance(q, dict)]
    by_type_set = Counter((q.get("type"), q.get("set")) for q in valid)

    print(f"\nType x set ({len(valid)} questions)")
    print(f"  {'type':<17}{'tune':>6}{'holdout':>9}{'total':>7}")
    for t in TYPES:
        tune, hold = by_type_set[(t, "tune")], by_type_set[(t, "holdout")]
        print(f"  {t:<17}{tune:>6}{hold:>9}{tune + hold:>7}")
    tune = sum(by_type_set[(t, "tune")] for t in TYPES)
    hold = sum(by_type_set[(t, "holdout")] for t in TYPES)
    print(f"  {'total':<17}{tune:>6}{hold:>9}{tune + hold:>7}")

    styles = Counter(q.get("style") for q in valid)
    print("\nStyle")
    for s in STYLES:
        print(f"  {s:<17}{styles[s]:>6}")

    cited = Counter(d for q in valid if is_str_list(q.get("expected_docs")) for d in q["expected_docs"])
    never = [d for d in docs if cited[d] == 0]
    print(f"\nCoverage: {len(docs) - len(never)} of {len(docs)} docs are expected by at least one question")
    if never:
        print("  Never expected:")
        for d in never:
            note = "  (superseded, should never be cited)" if docs[d] else ""
            print(f"    {d}{note}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--file", type=Path, default=QUESTIONS_FILE, help="questions file to check")
    args = parser.parse_args()

    try:
        questions = json.loads(args.file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR {args.file}: {exc}")
        print("FAILED: 1 error(s)")
        return 1
    if not isinstance(questions, list):
        print(f"ERROR {args.file}: top level must be a JSON list")
        print("FAILED: 1 error(s)")
        return 1

    docs = load_docs()
    errors = check(questions, docs)
    for line in errors:
        print(line)
    summarize(questions, docs)

    print()
    if errors:
        print(f"FAILED: {len(errors)} error(s)")
        return 1
    print(f"OK: {len(questions)} questions, 0 errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
