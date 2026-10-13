"""Ingest the Northwind runbook corpus into a persistent ChromaDB collection.

Reads only data/*.md (skipping INDEX.md), chunks each doc by "## " section,
and stores the chunks with Chroma's default embedding model. No LLM calls.
Re-runnable: the collection is deleted and recreated on every run.

Run (venv active): python ingest.py
"""

import re
from pathlib import Path

import chromadb
import yaml

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
CHROMA_DIR = HERE / "chroma_db"
COLLECTION = "runbooks"

REQUIRED_KEYS = ["id", "title", "doc_type", "service", "severity", "owner_team", "last_updated"]
FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)


def parse_doc(path):
    """Return (metadata, body) for one markdown file with YAML front matter."""
    match = FRONT_MATTER.match(path.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"{path.name}: no front matter found")
    front, body = match.groups()
    meta = yaml.safe_load(front)
    missing = [k for k in REQUIRED_KEYS if k not in meta]
    if missing:
        raise ValueError(f"{path.name}: front matter missing {missing}")
    metadata = {
        "doc_id": str(meta["id"]),
        "title": str(meta["title"]),
        "doc_type": str(meta["doc_type"]),
        "service": str(meta["service"]),
        "severity": str(meta["severity"]),
        "owner_team": str(meta["owner_team"]),
        "last_updated": str(meta["last_updated"]),  # YAML parses bare dates to date objects
        "superseded": "SUPERSEDED by" in body,
    }
    return metadata, body


def chunk_body(body):
    """Split a doc body into (section, text) pairs on '## ' headings.

    Text between the H1 and the first '## ' (e.g. the SUPERSEDED banner) is kept
    as an 'Overview' chunk rather than dropped.
    """
    body = re.sub(r"\A\s*# [^\n]*\n", "", body)  # drop the H1 title line
    parts = re.split(r"(?m)^(?=## )", body)
    chunks = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part.startswith("## "):
            section = part.splitlines()[0][3:].strip()
        else:
            section = "Overview"
        chunks.append((section, part))
    return chunks


def main():
    paths = sorted(p for p in DATA_DIR.glob("*.md") if p.name != "INDEX.md")

    ids, documents, metadatas = [], [], []
    for path in paths:
        meta, body = parse_doc(path)
        for n, (section, text) in enumerate(chunk_body(body)):
            ids.append(f"{meta['doc_id']}#{n}")
            documents.append(f"[{meta['doc_id']} | {meta['title']} | {section}]\n{text}")
            metadatas.append({**meta, "section": section, "chunk_index": n})

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection(COLLECTION)
    except Exception:  # collection does not exist yet (first run)
        pass
    collection = client.create_collection(COLLECTION)
    collection.add(ids=ids, documents=documents, metadatas=metadatas)

    words = [len(d.split()) for d in documents]
    print(f"Docs read:      {len(paths)}")
    print(f"Chunks created: {len(ids)}")
    print(f"Words/chunk:    avg {sum(words) / len(words):.1f}, min {min(words)}, max {max(words)}")
    print("3 largest chunks:")
    for i in sorted(range(len(ids)), key=lambda i: words[i], reverse=True)[:3]:
        print(f"  {ids[i]} | {metadatas[i]['section']} | {words[i]} words")
    print(f"Stored in collection '{COLLECTION}' at {CHROMA_DIR}")


if __name__ == "__main__":
    main()
