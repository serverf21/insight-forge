import math
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import init_db
from app.search.hybrid import HybridSearcher
from app.search.vector import VectorIndex


class FixedDimModel:
    def __init__(self, dimension: int) -> None:
        self.dimension = dimension

    def get_sentence_embedding_dimension(self) -> int:
        return self.dimension


class FakeIndex:
    def __init__(self, scores: list[tuple[str, float]]) -> None:
        self.scores = scores

    def query(self, q: str, top_k: int) -> list[tuple[str, float]]:
        return self.scores[:top_k]


def test_vector_dimension_mismatch_raises_rebuild_message(tmp_path):
    index_dir = tmp_path / "vector"
    index_dir.mkdir()
    (index_dir / "index.faiss").write_bytes(b"placeholder")
    (index_dir / "docmap.json").write_text('["doc-1"]', encoding="utf-8")
    (index_dir / "meta.json").write_text('{"dimension": 384}', encoding="utf-8")

    index = VectorIndex(index_dir=index_dir, model=FixedDimModel(768))

    with pytest.raises(
        RuntimeError,
        match=r"Index dimension mismatch: expected 768, got 384\. Rebuild with python -m app\.index",
    ):
        index.load()


def test_sqlite_migration_repairs_user_agent_without_default(tmp_path):
    db_path = tmp_path / "broken.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE query_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id VARCHAR(64) NOT NULL,
                    query TEXT NOT NULL,
                    alpha FLOAT NOT NULL DEFAULT 0.5,
                    top_k INTEGER NOT NULL DEFAULT 10,
                    result_count INTEGER NOT NULL DEFAULT 0,
                    latency_ms FLOAT NOT NULL DEFAULT 0.0,
                    error TEXT NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    user_agent TEXT NOT NULL
                )
                """
            )
        )
        with pytest.raises(Exception):
            connection.execute(
                text(
                    """
                    INSERT INTO query_logs
                    (request_id, query, alpha, top_k, result_count, latency_ms, error)
                    VALUES ('r1', 'before', 0.5, 10, 0, 1.0, '')
                    """
                )
            )

    init_db(engine)

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO query_logs
                (request_id, query, alpha, top_k, result_count, latency_ms, error, created_at)
                VALUES ('r2', 'after', 0.5, 10, 1, 2.0, '', CURRENT_TIMESTAMP)
                """
            )
        )
        value = connection.execute(text("SELECT user_agent FROM query_logs WHERE request_id = 'r2'")).scalar_one()

    assert value == "unknown"


def test_hybrid_equal_scores_do_not_emit_nan(tmp_path):
    docs_path = tmp_path / "docs.jsonl"
    docs_path.write_text(
        "\n".join(
            [
                '{"doc_id":"a","title":"A","text":"alpha"}',
                '{"doc_id":"b","title":"B","text":"beta"}',
                '{"doc_id":"c","title":"C","text":"gamma"}',
            ]
        ),
        encoding="utf-8",
    )
    searcher = HybridSearcher(
        docs_path=docs_path,
        bm25_index=FakeIndex([("a", 1.0), ("b", 1.0), ("c", 1.0)]),
        vector_index=FakeIndex([("a", 0.3), ("b", 0.2), ("c", 0.1)]),
    )

    results = searcher.search("same bm25", top_k=3, alpha=0.5)

    for result in results:
        assert math.isfinite(result.bm25_score)
        assert math.isfinite(result.vector_score)
        assert math.isfinite(result.hybrid_score)
