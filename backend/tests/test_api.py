import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.main import app
from app.db.models import Base
from app.search.hybrid import SearchResult


class FakeSearcher:
    def search(self, query: str, top_k: int = 10, alpha: float = 0.5):
        return [
            SearchResult(
                doc_id="doc-1",
                title="Test Document",
                snippet="A short snippet",
                bm25_score=2.0,
                vector_score=0.5,
                hybrid_score=0.75,
            )
        ][:top_k]


def make_client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'api.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    app.state.searcher = FakeSearcher()
    app.state.db_session_factory = testing_session
    return TestClient(app)


def test_health_has_commit_hash(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "1.0.0"
    assert "commit_hash" in body
    assert isinstance(body["commit_hash"], str)


def test_search_returns_score_breakdown(tmp_path):
    client = make_client(tmp_path)

    response = client.post("/search", json={"query": "test", "top_k": 1, "alpha": 0.5})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert "latency_ms" in body
    result = body["results"][0]
    assert "bm25_score" in result
    assert "vector_score" in result
    assert "hybrid_score" in result


def test_search_rejects_empty_query(tmp_path):
    client = make_client(tmp_path)

    response = client.post("/search", json={"query": "", "top_k": 1, "alpha": 0.5})

    assert response.status_code == 422


def test_metrics_prometheus_format(tmp_path):
    client = make_client(tmp_path)
    client.post("/search", json={"query": "test", "top_k": 1, "alpha": 0.5})

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text
    assert "search_requests_total " in body
    assert "search_zero_results_total " in body
    assert "search_latency_p50_ms " in body
    assert "search_latency_p95_ms " in body


def test_feedback_records_row(tmp_path):
    client = make_client(tmp_path)

    response = client.post(
        "/feedback",
        json={"request_id": "req-1", "doc_id": "doc-1", "relevant": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "recorded"
    assert isinstance(body["feedback_id"], int)


def test_feedback_rejects_empty_request_id(tmp_path):
    client = make_client(tmp_path)

    response = client.post(
        "/feedback",
        json={"request_id": "", "doc_id": "doc-1", "relevant": True},
    )

    assert response.status_code == 422


def test_feedback_rejects_empty_doc_id(tmp_path):
    client = make_client(tmp_path)

    response = client.post(
        "/feedback",
        json={"request_id": "req-1", "doc_id": "", "relevant": True},
    )

    assert response.status_code == 422
