from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SchemaVersion(Base):
    __tablename__ = "_schema_version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=2)


class QueryLog(Base):
    __tablename__ = "query_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    alpha: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    user_agent: Mapped[str] = mapped_column(Text, nullable=False, default="unknown", server_default="unknown")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )


class ExperimentRun(Base):
    __tablename__ = "experiment_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    git_commit: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    alpha: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    model: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    ndcg10: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recall10: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    mrr10: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class RelevanceFeedback(Base):
    __tablename__ = "relevance_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    doc_id: Mapped[str] = mapped_column(String(64), nullable=False)
    relevant: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
