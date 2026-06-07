#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

HOST="${APP_HOST:-0.0.0.0}"
PORT="${APP_PORT:-8000}"
BASE_PATH="${APP_BASE_PATH:-}"

ROOT_PATH_ARGS=()
if [ -n "$BASE_PATH" ]; then
  ROOT_PATH_ARGS=(--root-path "$BASE_PATH")
fi

if [ -n "$BASE_PATH" ]; then
  echo "==> FastAPI 起動（内部 :${PORT}、公開 http://localhost${BASE_PATH}/）"
else
  echo "==> FastAPI 起動: http://${HOST}:${PORT}"
fi
uvicorn app.main:app --host "$HOST" --port "$PORT" "${ROOT_PATH_ARGS[@]}" --reload
