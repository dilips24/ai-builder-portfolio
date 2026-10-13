"""Raw semantic search over the runbook ChromaDB collection (no filtering, no LLM calls).

  python search.py "question"        top-k chunks for one question
  python search.py --all             run every question in test_questions.json,
                                     print a table and save search_results.csv
  --k N                              number of chunks to return (default 3)

Run `python ingest.py` first to build the collection.
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import chromadb

HERE = Path(__file__).resolve().parent
CHROMA_DIR = HERE / "chroma_db"
COLLECTION = "runbooks"
QUESTIONS_FILE = HERE / "test_questions.json"
RESULTS_CSV = HERE / "search_results.csv"


def open_collection():
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        return client.get_collection(COLLECTION)
    except Exception:
        sys.exit(f"Collection '{COLLECTION}' not found in {CHROMA_DIR}. Run `python ingest.py` first.")


def retrieve(collection, question, k):
    """Return the top-k chunks for a question as a list of dicts, nearest first."""
    res = collection.query(query_texts=[question], n_results=k)
    return [
        {
            "chunk_id": cid,
            "doc_id": meta["doc_id"],
            "section": meta["section"],
            "superseded": meta["superseded"],
            "distance": dist,
            "text": doc,
        }
        for cid, meta, dist, doc in zip(
            res["ids"][0], res["metadatas"][0], res["distances"][0], res["documents"][0]
        )
    ]


def preview(text, width=150):
    """First `width` characters of the chunk, skipping the '[id | title | section]' header line."""
    lines = text.split("\n", 1)
    body = lines[1] if lines[0].startswith("[") and len(lines) > 1 else text
    return re.sub(r"\s+", " ", body).strip()[:width]


def print_single(collection, question, k):
    print(f"Question: {question}\n")
    for rank, hit in enumerate(retrieve(collection, question, k), start=1):
        print(
            f"{rank}. {hit['doc_id']} | {hit['section']} | distance {hit['distance']:.3f} | "
            f"superseded={'yes' if hit['superseded'] else 'no'}"
        )
        print(f"   {preview(hit['text'])}\n")


def run_all(collection, k):
    questions = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
    rows = []
    hits = expecting = 0
    for q in questions:
        results = retrieve(collection, q["question"], k)
        top_docs = [r["doc_id"] for r in results]
        distances = [r["distance"] for r in results]
        best = min(distances)
        expected = q["expected_docs"]
        if expected:
            expecting += 1
            verdict = "HIT" if any(d in top_docs for d in expected) else "MISS"
            hits += verdict == "HIT"
        else:
            verdict = "NONE-EXPECTED"
        rows.append((q["id"], expected, top_docs, distances, verdict, best))

    print(f"{'id':<7}{'expected':<14}{'top-' + str(k) + ' (doc_id distance)':<{k * 16 + 2}}result")
    for qid, expected, top_docs, distances, verdict, best in rows:
        top = "  ".join(f"{d} {x:.3f}" for d, x in zip(top_docs, distances))
        result = f"NONE-EXPECTED (best {best:.3f})" if verdict == "NONE-EXPECTED" else verdict
        print(f"{qid:<7}{','.join(expected) or '-':<14}{top:<{k * 16 + 2}}{result}")
    print(f"\nhit@{k} = {hits}/{expecting}" + (f" = {hits / expecting:.2f}" if expecting else ""))

    with RESULTS_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "expected_docs", f"top{k}_doc_ids", f"top{k}_distances", "result", "best_distance"])
        for qid, expected, top_docs, distances, verdict, best in rows:
            writer.writerow(
                [qid, ";".join(expected), ";".join(top_docs),
                 ";".join(f"{x:.3f}" for x in distances), verdict, f"{best:.3f}"]
            )
    print(f"Saved {RESULTS_CSV}")


def main():
    parser = argparse.ArgumentParser(description="Raw semantic search over the runbook collection.")
    parser.add_argument("question", nargs="?", help="question to search for")
    parser.add_argument("--all", action="store_true", help="run every question in test_questions.json")
    parser.add_argument("--k", type=int, default=3, help="number of chunks to return (default 3)")
    args = parser.parse_args()
    if not args.question and not args.all:
        parser.error("give a question or --all")
    if args.k < 1:
        parser.error("--k must be at least 1")

    collection = open_collection()
    if args.all:
        run_all(collection, args.k)
    else:
        print_single(collection, args.question, args.k)


if __name__ == "__main__":
    main()
