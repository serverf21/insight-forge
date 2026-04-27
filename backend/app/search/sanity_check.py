import argparse
import json
from pathlib import Path

from app.search.bm25 import BM25Index
from app.search.vector import VectorIndex


def load_doc_lookup(path: Path) -> dict[str, dict]:
    docs = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        doc = json.loads(line)
        docs[str(doc["doc_id"])] = doc
    return docs


def print_results(label: str, results: list[tuple[str, float]], docs: dict[str, dict]) -> None:
    print(label)
    for rank, (doc_id, score) in enumerate(results, start=1):
        doc = docs.get(doc_id, {})
        title = doc.get("title", "<missing title>")
        source = doc.get("source", "<missing source>")
        print(f"{rank}. {title} ({doc_id}) score={score:.4f} source={source}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one BM25 query and one vector query against built indexes.")
    parser.add_argument("--query", default="Alan Turing computer science", help="Query text to run.")
    parser.add_argument("--top-k", default=5, type=int, help="Number of results per index.")
    parser.add_argument("--docs", default="data/processed/docs.jsonl", type=Path, help="Processed docs JSONL path.")
    parser.add_argument("--bm25-dir", default="data/index/bm25", type=Path, help="BM25 index directory.")
    parser.add_argument("--vector-dir", default="data/index/vector", type=Path, help="Vector index directory.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    docs = load_doc_lookup(args.docs)
    if not docs:
        raise SystemExit(f"No documents found in {args.docs}")

    bm25_results = BM25Index(index_dir=args.bm25_dir).query(args.query, args.top_k)
    vector_results = VectorIndex(index_dir=args.vector_dir).query(args.query, args.top_k)

    print(f"Query: {args.query}")
    print_results("\nBM25", bm25_results, docs)
    print_results("\nVector", vector_results, docs)


if __name__ == "__main__":
    main()
