import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.search.hybrid import HybridSearcher, SearchResult, minmax_normalize


class FakeIndex:
    def __init__(self, results: list[tuple[str, float]]) -> None:
        self.results = results

    def query(self, q: str, top_k: int) -> list[tuple[str, float]]:
        return self.results[:top_k]


def write_docs(path: Path) -> None:
    rows = [
        '{"doc_id":"a","title":"Alpha","text":"Alpha text about apples."}',
        '{"doc_id":"b","title":"Beta","text":"Beta text about bananas."}',
        '{"doc_id":"c","title":"Gamma","text":"Gamma text about cars."}',
    ]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def test_no_nan_scores_when_all_bm25_scores_are_equal(tmp_path):
    docs_path = tmp_path / "docs.jsonl"
    write_docs(docs_path)
    searcher = HybridSearcher(
        docs_path=docs_path,
        bm25_index=FakeIndex([("a", 2.0), ("b", 2.0), ("c", 2.0)]),
        vector_index=FakeIndex([("a", 0.3), ("b", 0.2), ("c", 0.1)]),
    )

    results = searcher.search("query", top_k=3)

    assert minmax_normalize([2.0, 2.0, 2.0]) == pytest.approx([1 / 3, 1 / 3, 1 / 3])
    for result in results:
        assert math.isfinite(result.bm25_score)
        assert math.isfinite(result.vector_score)
        assert math.isfinite(result.hybrid_score)


def test_alpha_one_ranking_matches_pure_bm25_ordering(tmp_path):
    docs_path = tmp_path / "docs.jsonl"
    write_docs(docs_path)
    searcher = HybridSearcher(
        docs_path=docs_path,
        bm25_index=FakeIndex([("b", 10.0), ("a", 5.0), ("c", 1.0)]),
        vector_index=FakeIndex([("c", 0.9), ("a", 0.2), ("b", 0.1)]),
    )

    results = searcher.search("query", top_k=3, alpha=1.0)

    assert [result.doc_id for result in results] == ["b", "a", "c"]


def test_alpha_zero_ranking_matches_pure_vector_ordering(tmp_path):
    docs_path = tmp_path / "docs.jsonl"
    write_docs(docs_path)
    searcher = HybridSearcher(
        docs_path=docs_path,
        bm25_index=FakeIndex([("b", 10.0), ("a", 5.0), ("c", 1.0)]),
        vector_index=FakeIndex([("c", 0.9), ("a", 0.2), ("b", 0.1)]),
    )

    results = searcher.search("query", top_k=3, alpha=0.0)

    assert [result.doc_id for result in results] == ["c", "a", "b"]


def test_search_result_fields_are_present_and_typed(tmp_path):
    docs_path = tmp_path / "docs.jsonl"
    write_docs(docs_path)
    searcher = HybridSearcher(
        docs_path=docs_path,
        bm25_index=FakeIndex([("a", 2.0)]),
        vector_index=FakeIndex([("a", 0.5)]),
    )

    [result] = searcher.search("query", top_k=1)

    assert isinstance(result, SearchResult)
    assert isinstance(result.doc_id, str)
    assert isinstance(result.title, str)
    assert isinstance(result.snippet, str)
    assert isinstance(result.bm25_score, float)
    assert isinstance(result.vector_score, float)
    assert isinstance(result.hybrid_score, float)
    assert result.model_fields.keys() == {
        "doc_id",
        "title",
        "snippet",
        "bm25_score",
        "vector_score",
        "hybrid_score",
    }
