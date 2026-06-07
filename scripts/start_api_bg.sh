#!/usr/bin/env bash
# FastAPI をバックグラウンドで起動（ターミナルを閉じても維持）
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
LOG="${API_LOG:-/tmp/comfy-google-api.log}"

ROOT_PATH_ARGS=()
if [ -n "$BASE_PATH" ]; then
  ROOT_PATH_ARGS=(--root-path "$BASE_PATH")
fi

if pgrep -f "uvicorn app.main:app" >/dev/null 2>&1; then
  echo "==> 既に uvicorn が起動中です"
  pgrep -af "uvicorn app.main:app" || true
  exit 0
fi

source venv/bin/activate
nohup uvicorn app.main:app --host "$HOST" --port "$PORT" "${ROOT_PATH_ARGS[@]}" >"$LOG" 2>&1 &
if [ -n "$BASE_PATH" ]; then
  echo "==> FastAPI 起動（内部 :${PORT}、公開 http://localhost${BASE_PATH}/）"
else
  echo "==> FastAPI 起動: http://${HOST}:${PORT}/ui"
fi
echo "==> ログ: $LOG"
