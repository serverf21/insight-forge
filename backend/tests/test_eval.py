import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.eval import EvaluationMetrics, append_experiment_row, evaluate
from app.search.hybrid import SearchResult


class FakeSearcher:
    def __init__(self, ranked_ids: list[str]) -> None:
        self.ranked_ids = ranked_ids

    def search(self, query: str, top_k: int = 10, alpha: float = 0.5) -> list[SearchResult]:
        return [
            SearchResult(
                doc_id=doc_id,
                title=doc_id,
                snippet="snippet",
                bm25_score=float(len(self.ranked_ids) - rank),
                vector_score=float(len(self.ranked_ids) - rank),
                hybrid_score=float(len(self.ranked_ids) - rank),
            )
            for rank, doc_id in enumerate(self.ranked_ids[:top_k])
        ]


def test_ndcg_at_10_between_zero_and_one():
    metrics = evaluate(
        queries=[{"query_id": "q1", "query": "alpha"}],
        qrels={"q1": ["a", "b"]},
        searcher=FakeSearcher(["a", "c", "b"]),
        alpha=0.5,
    )

    assert 0.0 <= metrics.ndcg10 <= 1.0


def test_csv_row_is_appended_after_each_run(tmp_path):
    output_path = tmp_path / "experiments.csv"
    metrics = EvaluationMetrics(ndcg10=0.1, recall10=0.2, mrr10=0.3)

    append_experiment_row(metrics, alpha=0.5, model="toy", output_path=output_path, git_commit="test")
    append_experiment_row(metrics, alpha=0.7, model="toy", output_path=output_path, git_commit="test")

    rows = list(csv.DictReader(output_path.open("r", encoding="utf-8")))
    assert len(rows) == 2
    assert rows[0]["alpha"] == "0.500"
    assert rows[1]["alpha"] == "0.700"


def test_mrr_at_10_is_one_when_top_result_is_always_relevant():
    metrics = evaluate(
        queries=[
            {"query_id": "q1", "query": "alpha"},
            {"query_id": "q2", "query": "beta"},
        ],
        qrels={"q1": ["a"], "q2": ["a", "b"]},
        searcher=FakeSearcher(["a", "c", "b"]),
        alpha=0.5,
    )

    assert metrics.mrr10 == 1.0
