"""Calibrate the "no answer" distance cut-off on the tune questions (no LLM calls).

For every question with set == "tune", retrieve the top 3 chunks (superseded filtered), take the
best (smallest) distance and classify it:

  HIT        an expected doc is in the top 3
  MISS       expected docs exist but none was retrieved
  NO-ANSWER  expected_docs is empty (the corpus has no answer)

Then sweep cut-offs 1.10 to 1.30: a question is blocked when its best distance is above the cut-off.
Holdout questions are dropped as soon as the file is loaded and never used.

  python calibrate.py
"""

import json

from search import QUESTIONS_FILE, open_collection, retrieve

K = 3
CUTOFFS = [round(1.10 + 0.01 * i, 2) for i in range(21)]


def flatten(docs):
    """tq-09 has expected_docs [["RB-010"]]; accept nested lists as well as a flat list."""
    return [d for item in docs for d in (flatten(item) if isinstance(item, list) else [item])]


def classify(expected, top_docs):
    if not expected:
        return "NO-ANSWER"
    return "HIT" if any(d in top_docs for d in expected) else "MISS"


def main():
    questions = [q for q in json.loads(QUESTIONS_FILE.read_text(encoding="utf-8")) if q["set"] == "tune"]
    for q in questions:
        q["expected_docs"] = flatten(q["expected_docs"])
    collection = open_collection()

    rows = []
    for q in questions:
        results = retrieve(collection, q["question"], K)
        top_docs = [r["doc_id"] for r in results]
        best = min(r["distance"] for r in results)
        rows.append((q["id"], classify(q["expected_docs"], top_docs), best, q["expected_docs"], top_docs))
    rows.sort(key=lambda r: r[2])

    print(f"{'id':<7}{'class':<11}{'best':<8}{'expected':<14}top-{K}")
    for qid, cls, best, expected, top_docs in rows:
        print(f"{qid:<7}{cls:<11}{best:<8.3f}{','.join(expected) or '-':<14}{' '.join(top_docs)}")

    counts = {c: sum(r[1] == c for r in rows) for c in ("HIT", "MISS", "NO-ANSWER")}
    print(f"\n{len(rows)} tune questions: {counts['HIT']} HIT, {counts['MISS']} MISS, "
          f"{counts['NO-ANSWER']} NO-ANSWER")

    def best_of(cls):
        return [r[2] for r in rows if r[1] == cls]

    hit_best, none_best = best_of("HIT"), best_of("NO-ANSWER")
    if hit_best:
        print(f"Highest HIT best distance:       {max(hit_best):.3f}")
    if none_best:
        print(f"Lowest NO-ANSWER best distance:  {min(none_best):.3f}")

    print(f"\n{'cut-off':<9}{'NO-ANSWER blocked':<20}{'HITs wrongly blocked':<22}MISSes blocked")
    sweep = []
    for c in CUTOFFS:
        blocked = {cls: sum(1 for r in rows if r[1] == cls and r[2] > c) for cls in counts}
        sweep.append((c, blocked))
        print(f"{c:<9.2f}{blocked['NO-ANSWER']}/{counts['NO-ANSWER']:<17}"
              f"{blocked['HIT']}/{counts['HIT']:<19}{blocked['MISS']}/{counts['MISS']}")

    safe = [s for s in sweep if s[1]["HIT"] == 0]
    if safe:
        top = max(s[1]["NO-ANSWER"] for s in safe)
        c, blocked = next(s for s in safe if s[1]["NO-ANSWER"] == top)  # lowest cut-off among ties
        print(f"\nRecommended cut-off: {c:.2f} (blocks {top}/{counts['NO-ANSWER']} NO-ANSWER, 0 HITs, "
              f"{blocked['MISS']}/{counts['MISS']} MISSes)")
        if top == 0:
            print("Note: no NO-ANSWER question is blocked in 1.10-1.30; the boundary may lie outside this range.")
    else:
        c, blocked = min(sweep, key=lambda s: (s[1]["HIT"], -s[1]["NO-ANSWER"]))
        print(f"\nNo cut-off in 1.10-1.30 blocks zero HITs. Fewest wrongly blocked: {c:.2f} "
              f"({blocked['HIT']} HITs, {blocked['NO-ANSWER']}/{counts['NO-ANSWER']} NO-ANSWER blocked)")


if __name__ == "__main__":
    main()
