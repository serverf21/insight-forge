#!/usr/bin/env bash
set -euo pipefail

kill_port() {
  local port="$1"
  local pids=""

  if command -v lsof >/dev/null 2>&1; then
    pids="$(lsof -ti tcp:"${port}" 2>/dev/null || true)"
  elif command -v fuser >/dev/null 2>&1; then
    pids="$(fuser "${port}"/tcp 2>/dev/null || true)"
  fi

  if [[ -n "$pids" ]]; then
    kill $pids 2>/dev/null || true
    printf 'Killed processes on port %s: %s\n' "$port" "$pids"
  else
    printf 'No process found on port %s\n' "$port"
  fi
}

kill_port 8000
kill_port 5173
