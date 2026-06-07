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

API_PORT="${APP_PORT:-8000}"
COMFY_PORT="${COMFYUI_PORT:-8188}"
BASE_PATH="${APP_BASE_PATH:-}"
HEALTH_PATH="/health"
PUBLIC_URL="http://127.0.0.1:${API_PORT}${HEALTH_PATH}"
if [ -n "$BASE_PATH" ]; then
  HEALTH_PATH="${BASE_PATH%/}/health"
  PUBLIC_URL="http://127.0.0.1${HEALTH_PATH} (nginx 経由: http://localhost${BASE_PATH%/}/)"
fi

echo "=== プロセス ==="
pgrep -af "uvicorn app.main:app" || echo "(FastAPI 未起動)"
pgrep -af "python main.py" || echo "(ComfyUI 未起動)"

echo ""
echo "=== ポート ==="
ss -tlnp 2>/dev/null | grep -E ":${API_PORT}|:${COMFY_PORT}" || true

echo ""
echo "=== 疎通 ==="
echo "公開 URL 目安: ${PUBLIC_URL}"
curl -sf "http://127.0.0.1:${API_PORT}/health" && echo " (直接 :${API_PORT})" || echo "FastAPI :${API_PORT} 接続不可"
if [ -n "$BASE_PATH" ]; then
  curl -sf "http://127.0.0.1${HEALTH_PATH}" >/dev/null 2>&1 \
    && echo "nginx 経由 ${HEALTH_PATH} OK" \
    || echo "nginx 経由 ${HEALTH_PATH} 未設定または未起動"
fi
curl -sf "http://127.0.0.1:${COMFY_PORT}/system_stats" >/dev/null \
  && echo "ComfyUI :${COMFY_PORT} OK" \
  || echo "ComfyUI :${COMFY_PORT} 接続不可"
