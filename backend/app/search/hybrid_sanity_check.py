import argparse
import math
from pathlib import Path

from app.search.bm25 import BM25Index
from app.search.hybrid import HybridSearcher, SearchResult
from app.search.vector import VectorIndex


def assert_descending(results: list[SearchResult]) -> None:
    scores = [result.hybrid_score for result in results]
    if scores != sorted(scores, reverse=True):
        raise AssertionError(f"hybrid_score is not descending: {scores}")


def assert_finite(results: list[SearchResult]) -> None:
    for result in results:
        for field in ("bm25_score", "vector_score", "hybrid_score"):
            value = getattr(result, field)
            if math.isnan(value) or math.isinf(value):
                raise AssertionError(f"{field} for {result.doc_id} is not finite: {value}")


def assert_alpha_ordering(searcher: HybridSearcher, query: str, top_k: int) -> None:
    candidate_k = top_k * 3
    expected_bm25 = [doc_id for doc_id, _ in searcher.bm25_index.query(query, candidate_k)][:top_k]
    expected_vector = [doc_id for doc_id, _ in searcher.vector_index.query(query, candidate_k)][:top_k]
    alpha_bm25 = [result.doc_id for result in searcher.search(query, top_k=top_k, alpha=1.0)]
    alpha_vector = [result.doc_id for result in searcher.search(query, top_k=top_k, alpha=0.0)]

    if alpha_bm25 != expected_bm25:
        raise AssertionError(f"alpha=1.0 mismatch: expected {expected_bm25}, got {alpha_bm25}")
    if alpha_vector != expected_vector:
        raise AssertionError(f"alpha=0.0 mismatch: expected {expected_vector}, got {alpha_vector}")


def print_results(label: str, results: list[SearchResult]) -> None:
    print(label)
    for rank, result in enumerate(results, start=1):
        print(
            f"{rank}. {result.title} ({result.doc_id}) "
            f"hybrid={result.hybrid_score:.4f} "
            f"bm25={result.bm25_score:.4f} "
            f"vector={result.vector_score:.4f}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assert hybrid search invariants against built indexes.")
    parser.add_argument("--query", default="Alan Turing computer science")
    parser.add_argument("--top-k", default=5, type=int)
    parser.add_argument("--alpha", default=0.5, type=float)
    parser.add_argument("--docs", default="data/processed/docs.jsonl", type=Path)
    parser.add_argument("--bm25-dir", default="data/index/bm25", type=Path)
    parser.add_argument("--vector-dir", default="data/index/vector", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    searcher = HybridSearcher(
        docs_path=args.docs,
        bm25_index=BM25Index(index_dir=args.bm25_dir),
        vector_index=VectorIndex(index_dir=args.vector_dir),
    )
    results = searcher.search(args.query, top_k=args.top_k, alpha=args.alpha)

    assert_descending(results)
    assert_finite(results)
    assert_alpha_ordering(searcher, args.query, args.top_k)

    print_results(f"Hybrid results for query={args.query!r}, alpha={args.alpha}", results)
    print("Sanity checks passed: descending hybrid scores, finite scores, alpha edge ordering.")


if __name__ == "__main__":
    main()
