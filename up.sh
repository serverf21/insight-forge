#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

fail() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

require_command() {
  local command_name="$1"
  local install_hint="$2"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    fail "$command_name is required. $install_hint"
  fi
}

version_at_least() {
  local actual="$1"
  local required="$2"
  python3 - "$actual" "$required" <<'PY'
import sys

actual = tuple(int(part) for part in sys.argv[1].split(".")[:3])
required = tuple(int(part) for part in sys.argv[2].split(".")[:3])
if actual < required:
    sys.exit(1)
PY
}

preflight() {
  require_command python3 "Install Python 3.11 or newer, then retry: bash up.sh"
  require_command node "Install Node.js 18 or newer, then retry: bash up.sh"
  require_command npm "Install npm with Node.js, then retry: bash up.sh"

  local python_version
  python_version="$(python3 -c 'import platform; print(platform.python_version())')"
  if ! version_at_least "$python_version" "3.11.0"; then
    fail "python3 must be >= 3.11; found $python_version. Install Python 3.11+ and ensure python3 points to it."
  fi

  local node_version
  node_version="$(node -p 'process.versions.node')"
  if ! version_at_least "$node_version" "18.0.0"; then
    fail "node must be >= 18; found $node_version. Install Node.js 18+ and retry."
  fi
}

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

preflight

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

if [[ ! -f "data/processed/docs.jsonl" ]]; then
  PYTHONPATH="$ROOT_DIR/backend" python -m app.ingest --input data/raw --out data/processed
fi

if [[ ! -f "data/index/bm25/index.pkl" || ! -f "data/index/bm25/docmap.json" || ! -f "data/index/vector/index.faiss" || ! -f "data/index/vector/meta.json" || ! -f "data/index/vector/docmap.json" ]]; then
  PYTHONPATH="$ROOT_DIR/backend" python -m app.index --input data/processed/docs.jsonl
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
