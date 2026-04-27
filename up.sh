#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

BACKEND_PORT=8000
FRONTEND_PORT=5173
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  if [[ -n "${BACKEND_PID}" ]] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
    kill "${BACKEND_PID}" 2>/dev/null || true
  fi

  if [[ -n "${FRONTEND_PID}" ]] && kill -0 "${FRONTEND_PID}" 2>/dev/null; then
    kill "${FRONTEND_PID}" 2>/dev/null || true
  fi

  wait "${BACKEND_PID}" 2>/dev/null || true
  wait "${FRONTEND_PID}" 2>/dev/null || true
}

trap cleanup SIGINT SIGTERM EXIT

if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if ! find data/raw -type f ! -name ".gitkeep" -print -quit | grep -q .; then
  python - <<'PY'
from pathlib import Path
from datasets import load_dataset

raw_dir = Path("data/raw")
raw_dir.mkdir(parents=True, exist_ok=True)

dataset = load_dataset("wikipedia", "20220301.simple", split="train[:300]")
for idx, row in enumerate(dataset):
    title = row.get("title") or f"document_{idx:03d}"
    text = row.get("text") or ""
    safe_title = "".join(ch if ch.isalnum() else "_" for ch in title).strip("_")
    filename = f"{idx:03d}_{safe_title[:80] or 'document'}.txt"
    (raw_dir / filename).write_text(text, encoding="utf-8")
PY
fi

if [[ ! -f "data/index/bm25/bm25.json" || ! -f "data/index/vector/vector.meta.json" ]]; then
  PYTHONPATH="$ROOT_DIR/backend" python -m app.ingest
  PYTHONPATH="$ROOT_DIR/backend" python -m app.index
fi

if [[ ! -d "frontend/node_modules" ]]; then
  npm install --prefix frontend
fi

PYTHONPATH="$ROOT_DIR/backend" python -m uvicorn app.api.main:app --host 0.0.0.0 --port "$BACKEND_PORT" &
BACKEND_PID=$!

npm run dev --prefix frontend -- --host 0.0.0.0 --port "$FRONTEND_PORT" &
FRONTEND_PID=$!

printf 'Backend: http://localhost:%s\n' "$BACKEND_PORT"
printf 'Frontend: http://localhost:%s\n' "$FRONTEND_PORT"

wait "$BACKEND_PID" "$FRONTEND_PID"
