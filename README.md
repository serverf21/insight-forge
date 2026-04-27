# Insight Forge

Hybrid search and KPI dashboard monorepo for local experimentation over a small Wikipedia corpus.

Run commands from the repo root. If you are inside `backend/`, prefix repo-root paths with `../`.

## Architecture

```text
                         +-----------------------------+
                         | React + Vite frontend       |
                         | Search / KPIs / Eval / Logs |
                         +--------------+--------------+
                                        |
                                  /api proxy
                                        |
                         +--------------v--------------+
                         | FastAPI backend              |
                         | routes.py / HybridSearcher   |
                         +------+----------+------------+
                                |          |
                    +-----------v--+    +--v----------------+
                    | BM25 index   |    | Vector index       |
                    | rank-bm25    |    | MiniLM + FAISS IP  |
                    +-----------+--+    +--+----------------+
                                |          |
                         +------v----------v------+
                         | data/processed/docs    |
                         | data/index/* artifacts |
                         +------------+-----------+
                                      |
                         +------------v-----------+
                         | SQLite metrics/log DB  |
                         | experiments.csv        |
                         +------------------------+
```

## 1-Minute Quickstart

```bash
python3 --version && node --version && npm --version
bash up.sh
open http://localhost:5173
```

`up.sh` preflights Python `>=3.11`, Node `>=18`, and npm; creates `.venv`; installs dependencies; downloads 300 Simple Wikipedia documents when needed; ingests JSONL; builds BM25/vector indexes; installs frontend dependencies; and starts:

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

Stop both services with `Ctrl+C`, or in another shell:

```bash
bash down.sh
```

## Tests

Run all backend tests:

```bash
.venv/bin/python -m pytest backend/
```

Focused suites:

```bash
.venv/bin/python -m pytest backend/tests/test_ingest.py
.venv/bin/python -m pytest backend/tests/test_search.py
.venv/bin/python -m pytest backend/tests/test_hybrid.py
.venv/bin/python -m pytest backend/tests/test_api.py
.venv/bin/python -m pytest backend/tests/test_eval.py
.venv/bin/python -m pytest backend/tests/test_regressions.py
```

Frontend build check:

```bash
npm run build --prefix frontend
```

## Data Pipeline

Ingest raw `.txt` and `.md` files:

```bash
PYTHONPATH="$PWD/backend" .venv/bin/python -m app.ingest \
  --input data/raw \
  --out data/processed
```

Build BM25 and vector indexes:

```bash
PYTHONPATH="$PWD/backend" .venv/bin/python -m app.index \
  --input data/processed/docs.jsonl
```

Expected artifacts:

- `data/processed/docs.jsonl`
- `data/index/bm25/index.pkl`
- `data/index/bm25/docmap.json`
- `data/index/vector/index.faiss`
- `data/index/vector/docmap.json`
- `data/index/vector/meta.json`

## Evaluation

Run one evaluation pass:

```bash
PYTHONPATH="$PWD/backend" .venv/bin/python -m app.eval \
  --queries data/eval/queries.jsonl \
  --qrels data/eval/qrels.json \
  --alpha 0.5 \
  --model all-MiniLM-L6-v2
```

Results append to `data/metrics/experiments.csv` with `timestamp`, `git_commit`, `alpha`, `model`, `preprocessing`, `ndcg10`, `recall10`, and `mrr10`.

## API

Useful endpoints:

- `GET /health`
- `POST /search`
- `GET /metrics`
- `GET /logs`
- `GET /experiments`

Frontend development uses the Vite proxy:

```text
/api/* -> http://localhost:8000/*
```

## SQLite Schema

| table | columns |
|---|---|
| `_schema_version` | `id`, `version` |
| `query_logs` | `id`, `request_id`, `query`, `alpha`, `top_k`, `result_count`, `latency_ms`, `error`, `user_agent`, `created_at` |
| `experiment_runs` | `id`, `timestamp`, `git_commit`, `alpha`, `model`, `ndcg10`, `recall10`, `mrr10` |

The DB lives at `data/metrics/insight_forge.db` by default. Override with `INSIGHT_FORGE_DATABASE_URL`.

## Sanity Checks

BM25/vector artifact smoke test:

```bash
PYTHONPATH="$PWD/backend" .venv/bin/python -m app.search.sanity_check \
  --query "Alan Turing computer science" \
  --top-k 3
```

Hybrid invariant check:

```bash
PYTHONPATH="$PWD/backend" .venv/bin/python -m app.search.hybrid_sanity_check \
  --query "Alan Turing computer science" \
  --top-k 5 \
  --alpha 0.5
```

Script syntax:

```bash
bash -n up.sh
bash -n down.sh
```

## Known Limitations

- The corpus bootstrap downloads a Simple Wikipedia dataset shard and may take several minutes on first run.
- The first vector query can be slow while `sentence-transformers` loads `all-MiniLM-L6-v2` on CPU.
- `IndexFlatIP` is exact and simple, but memory/query cost grows linearly with corpus size.
- SQLite is intended for local, single-node use; concurrent multi-user deployments should move logs and metrics to Postgres.
- The frontend KPI request-volume chart is a local rolling snapshot of `/metrics`, not a historical time-series store.
- Rate limiting is per-process via SlowAPI defaults; distributed deployments need shared limiter storage.

## Reviewer Checklist

- `bash -n up.sh` and `bash -n down.sh` pass.
- `up.sh` exits early with actionable messages if Python, Node, or npm are missing or too old.
- `bash up.sh` from a clean clone completes within 30 minutes on a machine with Python `>=3.11`, Node `>=18`, npm, and network access.
- `GET /health` returns `status`, `version`, and `commit_hash`.
- `POST /search` returns per-result `bm25_score`, `vector_score`, and `hybrid_score`.
- `GET /metrics` returns Prometheus-style text.
- `GET /experiments` renders the evaluation CSV in the frontend.
- `GET /logs` supports severity and date filters.
- `.venv/bin/python -m pytest backend/` passes.
