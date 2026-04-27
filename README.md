# Insight Forge

Hybrid search and KPI dashboard monorepo scaffold.

Run commands from the repo root unless noted otherwise. If you are inside `backend/`, prefix repo-root paths with `../`.

## Quick Start

```bash
bash up.sh
```

`up.sh` creates `.venv`, installs Python requirements, downloads 300 Simple Wikipedia documents if `data/raw/` is empty, ingests documents into JSONL, builds BM25 and vector indexes when artifacts are missing, installs frontend dependencies, and starts both dev servers:

- Backend: http://localhost:8000
- Frontend: http://localhost:5173

Stop both services with `Ctrl+C` from `up.sh`, or run:

```bash
bash down.sh
```

## Manual Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
npm install --prefix frontend
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

Expected index artifacts:

- `data/index/bm25/index.pkl`
- `data/index/bm25/docmap.json`
- `data/index/vector/index.faiss`
- `data/index/vector/docmap.json`
- `data/index/vector/meta.json`

## Tests

Run the full backend test suite:

```bash
.venv/bin/python -m pytest backend/tests
```

Run focused tests:

```bash
.venv/bin/python -m pytest backend/tests/test_ingest.py
.venv/bin/python -m pytest backend/tests/test_search.py
```

## Validations

Check script syntax:

```bash
bash -n up.sh
bash -n down.sh
```

Validate processed JSONL can be parsed:

```bash
.venv/bin/python - <<'PY'
import json
from pathlib import Path

path = Path("data/processed/docs.jsonl")
rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
print(f"docs={len(rows)}")
print(f"first_keys={sorted(rows[0]) if rows else []}")
PY
```

Validate vector index metadata:

```bash
.venv/bin/python - <<'PY'
import json
from pathlib import Path

meta = json.loads(Path("data/index/vector/meta.json").read_text(encoding="utf-8"))
print(meta)
PY
```

## Search Sanity Check

Run one BM25 query and one vector query against saved artifacts:

```bash
PYTHONPATH="$PWD/backend" .venv/bin/python -m app.search.sanity_check \
  --query "Alan Turing computer science" \
  --top-k 3
```

The output prints ranked titles, `doc_id`, score, and source for each index.

## Run Services Separately

Terminal 1, backend:

```bash
source .venv/bin/activate
PYTHONPATH="$PWD/backend" python -m uvicorn app.api.main:app \
  --host 0.0.0.0 \
  --port 8000
```

Terminal 2, frontend:

```bash
npm run dev --prefix frontend -- --host 0.0.0.0 --port 5173
```
