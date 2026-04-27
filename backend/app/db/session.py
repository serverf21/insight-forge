import os
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.db.models import Base


SCHEMA_VERSION = 3
DATABASE_URL = os.getenv("INSIGHT_FORGE_DATABASE_URL", "sqlite:///data/metrics/insight_forge.db")

if DATABASE_URL.startswith("sqlite:///"):
    db_path = Path(DATABASE_URL.replace("sqlite:///", "", 1))
    if not db_path.is_absolute():
        db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


QUERY_LOG_COLUMNS = {
    "request_id": "TEXT NOT NULL DEFAULT ''",
    "query": "TEXT NOT NULL DEFAULT ''",
    "alpha": "FLOAT NOT NULL DEFAULT 0.5",
    "top_k": "INTEGER NOT NULL DEFAULT 10",
    "result_count": "INTEGER NOT NULL DEFAULT 0",
    "latency_ms": "FLOAT NOT NULL DEFAULT 0.0",
    "error": "TEXT NOT NULL DEFAULT ''",
    "created_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
    "user_agent": "TEXT NOT NULL DEFAULT 'unknown'",
}

EXPERIMENT_RUN_COLUMNS = {
    "timestamp": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
    "git_commit": "VARCHAR(64) NOT NULL DEFAULT ''",
    "alpha": "FLOAT NOT NULL DEFAULT 0.5",
    "model": "VARCHAR(255) NOT NULL DEFAULT ''",
    "ndcg10": "FLOAT NOT NULL DEFAULT 0.0",
    "recall10": "FLOAT NOT NULL DEFAULT 0.0",
    "mrr10": "FLOAT NOT NULL DEFAULT 0.0",
}


def init_db(db_engine=engine) -> None:
    Base.metadata.create_all(bind=db_engine)
    inspector = inspect(db_engine)

    with db_engine.begin() as connection:
        _ensure_columns(connection, inspector, "query_logs", QUERY_LOG_COLUMNS)
        _ensure_columns(connection, inspector, "experiment_runs", EXPERIMENT_RUN_COLUMNS)
        _repair_query_log_user_agent_default(connection)

        version = connection.execute(text("SELECT version FROM _schema_version WHERE id = 1")).scalar()
        if version is None:
            connection.execute(text("INSERT INTO _schema_version (id, version) VALUES (1, :version)"), {"version": SCHEMA_VERSION})
        elif int(version) < SCHEMA_VERSION:
            connection.execute(text("UPDATE _schema_version SET version = :version WHERE id = 1"), {"version": SCHEMA_VERSION})


def _ensure_columns(connection, inspector, table_name: str, expected_columns: dict[str, str]) -> None:
    existing = {column["name"] for column in inspector.get_columns(table_name)}
    for column_name, ddl in expected_columns.items():
        if column_name not in existing:
            connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}"))


def _repair_query_log_user_agent_default(connection) -> None:
    columns = connection.execute(text("PRAGMA table_info(query_logs)")).mappings().all()
    user_agent = next((column for column in columns if column["name"] == "user_agent"), None)
    if user_agent is None:
        return

    if not user_agent["notnull"] or user_agent["dflt_value"] is not None:
        return

    connection.execute(text("ALTER TABLE query_logs RENAME TO query_logs_legacy"))
    Base.metadata.tables["query_logs"].create(bind=connection)
    legacy_columns = [column["name"] for column in columns if column["name"] != "user_agent"]
    column_list = ", ".join(legacy_columns)
    connection.execute(
        text(
            f"INSERT INTO query_logs ({column_list}, user_agent) "
            f"SELECT {column_list}, 'unknown' FROM query_logs_legacy"
        )
    )
    connection.execute(text("DROP TABLE query_logs_legacy"))
