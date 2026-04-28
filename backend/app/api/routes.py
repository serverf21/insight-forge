import csv
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db.models import QueryLog, RelevanceFeedback
from app.db.session import SessionLocal, init_db
from app.search.hybrid import HybridSearcher, SearchResult


VERSION = "1.0.0"
limiter = Limiter(key_func=get_remote_address)
router = APIRouter()


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(default=10, ge=1, le=50)
    alpha: float = Field(default=0.5, ge=0.0, le=1.0)


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int
    latency_ms: float


class FeedbackRequest(BaseModel):
    request_id: str = Field(..., min_length=1, max_length=64)
    doc_id: str = Field(..., min_length=1, max_length=64)
    relevant: bool


class FeedbackResponse(BaseModel):
    status: str
    feedback_id: int


def get_db(request: Request):
    factory = getattr(request.app.state, "db_session_factory", SessionLocal)
    db = factory()
    try:
        yield db
    finally:
        db.close()


def get_searcher(request: Request) -> HybridSearcher:
    searcher = getattr(request.app.state, "searcher", None)
    if searcher is None:
        searcher = HybridSearcher()
        request.app.state.searcher = searcher
    return searcher


def get_commit_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "dev"


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": VERSION, "commit_hash": get_commit_hash()}


@router.post("/search", response_model=SearchResponse)
@limiter.limit("60/minute")
def search(
    request: Request,
    payload: SearchRequest,
    db: Session = Depends(get_db),
    searcher: HybridSearcher = Depends(get_searcher),
) -> SearchResponse:
    request_id = str(uuid.uuid4())
    start = time.perf_counter()
    error = ""
    results: list[SearchResult] = []

    try:
        results = searcher.search(payload.query, top_k=payload.top_k, alpha=payload.alpha)
        return SearchResponse(
            results=results,
            total=len(results),
            latency_ms=(time.perf_counter() - start) * 1000,
        )
    except Exception as exc:
        error = str(exc)
        raise HTTPException(status_code=500, detail=error) from exc
    finally:
        latency_ms = (time.perf_counter() - start) * 1000
        db.add(
            QueryLog(
                request_id=request_id,
                query=payload.query,
                alpha=payload.alpha,
                top_k=payload.top_k,
                result_count=len(results),
                latency_ms=latency_ms,
                error=error,
            )
        )
        db.commit()


@router.post("/feedback", response_model=FeedbackResponse)
def feedback(payload: FeedbackRequest, db: Session = Depends(get_db)) -> FeedbackResponse:
    row = RelevanceFeedback(
        request_id=payload.request_id,
        doc_id=payload.doc_id,
        relevant=payload.relevant,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return FeedbackResponse(status="recorded", feedback_id=row.id)


@router.get("/metrics")
def metrics(db: Session = Depends(get_db)) -> Response:
    rows = list(db.scalars(select(QueryLog).order_by(desc(QueryLog.created_at)).limit(1000)))
    latencies = sorted(row.latency_ms for row in rows)
    body = "\n".join(
        [
            f"search_requests_total {len(rows)}",
            f"search_zero_results_total {sum(1 for row in rows if row.result_count == 0 and not row.error)}",
            f"search_latency_p50_ms {_percentile(latencies, 0.50):.4f}",
            f"search_latency_p95_ms {_percentile(latencies, 0.95):.4f}",
            "",
        ]
    )
    return Response(content=body, media_type="text/plain; version=0.0.4")


@router.get("/logs")
def logs(
    severity: Optional[str] = Query(default=None),
    from_ts: Optional[datetime] = Query(default=None),
    to_ts: Optional[datetime] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    statement = select(QueryLog)
    if severity == "error":
        statement = statement.where(QueryLog.error != "")
    elif severity == "info":
        statement = statement.where(QueryLog.error == "")
    if from_ts is not None:
        statement = statement.where(QueryLog.created_at >= from_ts)
    if to_ts is not None:
        statement = statement.where(QueryLog.created_at <= to_ts)

    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = list(db.scalars(statement.order_by(desc(QueryLog.created_at)).limit(limit).offset(offset)))
    return {"total": total, "items": [_query_log_to_dict(row) for row in rows]}


@router.get("/experiments")
def experiments() -> list[dict[str, str]]:
    path = Path("data/metrics/experiments.csv")
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    index = int(round((len(values) - 1) * percentile))
    return values[index]


def _query_log_to_dict(row: QueryLog) -> dict[str, object]:
    return {
        "id": row.id,
        "request_id": row.request_id,
        "query": row.query,
        "alpha": row.alpha,
        "top_k": row.top_k,
        "result_count": row.result_count,
        "latency_ms": row.latency_ms,
        "error": row.error,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


init_db()
