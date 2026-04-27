import argparse
import json
import time
from pathlib import Path

from app.search.bm25 import BM25Index
from app.search.vector import VectorIndex


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build BM25 and vector search indexes.")
    parser.add_argument("--input", default="data/processed/docs.jsonl", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    docs = load_jsonl(args.input)
    if not docs:
        raise SystemExit(f"No documents found in {args.input}. Run python -m app.ingest before building indexes.")

    start = time.perf_counter()
    BM25Index().build(docs)
    bm25_seconds = time.perf_counter() - start
    print(f"BM25 build time: {bm25_seconds:.2f}s")

    start = time.perf_counter()
    VectorIndex().build(docs)
    vector_seconds = time.perf_counter() - start
    print(f"Vector build time: {vector_seconds:.2f}s")


if __name__ == "__main__":
    main()
