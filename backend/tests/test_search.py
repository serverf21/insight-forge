import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.index import main
from app.search.bm25 import BM25Index
from app.search.vector import VectorIndex


class ToyModel:
    def __init__(self, dimension: int = 3) -> None:
        self.dimension = dimension

    def get_sentence_embedding_dimension(self) -> int:
        return self.dimension

    def encode(self, texts, **kwargs):
        rows = []
        for text in texts:
            lowered = text.lower()
            rows.append(
                [
                    lowered.count("apple") + lowered.count("fruit"),
                    lowered.count("banana"),
                    lowered.count("car") + lowered.count("engine"),
                ][: self.dimension]
            )
        vectors = np.asarray(rows, dtype="float32")
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / np.maximum(norms, 1.0)


def toy_docs() -> list[dict]:
    return [
        {"doc_id": "apple-doc", "title": "Apple", "text": "apple fruit orchard"},
        {"doc_id": "banana-doc", "title": "Banana", "text": "banana fruit yellow"},
        {"doc_id": "car-doc", "title": "Car", "text": "engine wheel road"},
    ]


def test_bm25_index_returns_deterministic_ordering(tmp_path):
    index = BM25Index(index_dir=tmp_path / "bm25")
    index.build(toy_docs())

    assert index.query("apple fruit", top_k=3)[0][0] == "apple-doc"
    assert [doc_id for doc_id, _ in index.query("engine", top_k=3)] == [
        "car-doc",
        "apple-doc",
        "banana-doc",
    ]


def test_bm25_index_rejects_empty_corpus(tmp_path):
    index = BM25Index(index_dir=tmp_path / "bm25")

    with pytest.raises(ValueError, match="Cannot build BM25 index from an empty document corpus"):
        index.build([])


def test_vector_index_query_returns_requested_number_of_results(tmp_path):
    index = VectorIndex(index_dir=tmp_path / "vector", model=ToyModel())
    index.build(toy_docs())

    results = index.query("apple", top_k=2)

    assert len(results) == 2
    assert results[0][0] == "apple-doc"


def test_vector_index_rejects_empty_corpus(tmp_path):
    index = VectorIndex(index_dir=tmp_path / "vector", model=ToyModel())

    with pytest.raises(ValueError, match="Cannot build vector index from an empty document corpus"):
        index.build([])


def test_vector_load_mismatched_dimension_raises_runtime_error(tmp_path):
    index_dir = tmp_path / "vector"
    index = VectorIndex(index_dir=index_dir, model=ToyModel(dimension=3))
    index.build(toy_docs())

    meta_path = index_dir / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["dimension"] = 2
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    mismatched = VectorIndex(index_dir=index_dir, model=ToyModel(dimension=3))

    with pytest.raises(
        RuntimeError,
        match=r"Index dimension mismatch: expected 3, got 2\. Rebuild with python -m app\.index",
    ):
        mismatched.load()


def test_index_cli_exits_cleanly_for_empty_jsonl(tmp_path, monkeypatch):
    empty_jsonl = tmp_path / "docs.jsonl"
    empty_jsonl.write_text("", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["app.index", "--input", str(empty_jsonl)])

    with pytest.raises(SystemExit, match="No documents found"):
        main()
