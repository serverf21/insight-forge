import argparse
import csv
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sklearn.metrics import ndcg_score

from app.search.hybrid import HybridSearcher, SearchResult


PREPROCESSING = "strip-collapse-blank-lines-truncate-400-words"
EXPERIMENTS_PATH = Path("data/metrics/experiments.csv")


@dataclass
class EvaluationMetrics:
    ndcg10: float
    recall10: float
    mrr10: float


def load_queries(path: Path) -> list[dict[str, str]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_qrels(path: Path) -> dict[str, list[str]]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(
    queries: list[dict[str, str]],
    qrels: dict[str, list[str]],
    searcher: HybridSearcher,
    alpha: float,
) -> EvaluationMetrics:
    ndcg_values = []
    recall_values = []
    mrr_values = []

    for query in queries:
        query_id = query["query_id"]
        relevant = set(qrels.get(query_id, []))
        results = searcher.search(query["query"], top_k=10, alpha=alpha)
        ndcg_values.append(ndcg_at_10(results, relevant))
        recall_values.append(recall_at_10(results, relevant))
        mrr_values.append(mrr_at_10(results, relevant))

    return EvaluationMetrics(
        ndcg10=_mean(ndcg_values),
        recall10=_mean(recall_values),
        mrr10=_mean(mrr_values),
    )


def ndcg_at_10(results: list[SearchResult], relevant: set[str]) -> float:
    if not relevant:
        return 0.0

    candidate_ids = [result.doc_id for result in results[:10]]
    for doc_id in relevant:
        if doc_id not in candidate_ids:
            candidate_ids.append(doc_id)

    relevance = [1.0 if doc_id in relevant else 0.0 for doc_id in candidate_ids]
    scores_by_doc = {result.doc_id: result.hybrid_score for result in results[:10]}
    scores = [float(scores_by_doc.get(doc_id, 0.0)) for doc_id in candidate_ids]
    return float(ndcg_score([relevance], [scores], k=10))


def recall_at_10(results: list[SearchResult], relevant: set[str]) -> float:
    if not relevant:
        return 0.0
    retrieved = {result.doc_id for result in results[:10]}
    return len(retrieved & relevant) / len(relevant)


def mrr_at_10(results: list[SearchResult], relevant: set[str]) -> float:
    for rank, result in enumerate(results[:10], start=1):
        if result.doc_id in relevant:
            return 1.0 / rank
    return 0.0


def append_experiment_row(
    metrics: EvaluationMetrics,
    alpha: float,
    model: str,
    output_path: Path = EXPERIMENTS_PATH,
    git_commit: Optional[str] = None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit or get_git_commit(),
        "alpha": f"{alpha:.3f}",
        "model": model,
        "preprocessing": PREPROCESSING,
        "ndcg10": f"{metrics.ndcg10:.6f}",
        "recall10": f"{metrics.recall10:.6f}",
        "mrr10": f"{metrics.mrr10:.6f}",
    }
    fieldnames = list(row.keys())
    write_header = not output_path.exists() or output_path.stat().st_size == 0

    with output_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def print_summary(metrics: EvaluationMetrics, alpha: float, model: str) -> None:
    print("metric,value")
    print(f"alpha,{alpha:.3f}")
    print(f"model,{model}")
    print(f"ndcg10,{metrics.ndcg10:.6f}")
    print(f"recall10,{metrics.recall10:.6f}")
    print(f"mrr10,{metrics.mrr10:.6f}")


def get_git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "dev"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate hybrid search against labeled qrels.")
    parser.add_argument("--queries", default="data/eval/queries.jsonl", type=Path)
    parser.add_argument("--qrels", default="data/eval/qrels.json", type=Path)
    parser.add_argument("--alpha", default=0.5, type=float)
    parser.add_argument("--model", default="all-MiniLM-L6-v2")
    parser.add_argument("--experiments-out", default=EXPERIMENTS_PATH, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    queries = load_queries(args.queries)
    qrels = load_qrels(args.qrels)
    searcher = HybridSearcher()
    metrics = evaluate(queries, qrels, searcher, alpha=args.alpha)
    append_experiment_row(metrics, alpha=args.alpha, model=args.model, output_path=args.experiments_out)
    print_summary(metrics, alpha=args.alpha, model=args.model)


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


if __name__ == "__main__":
    main()
