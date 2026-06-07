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

cd "$PROJECT_ROOT/comfyui"

export GOOGLE_AI_BRIDGE_URL="${GOOGLE_AI_BRIDGE_URL:-http://127.0.0.1:8000}"
export GOOGLE_AI_PROJECT_ROOT="${GOOGLE_AI_PROJECT_ROOT:-$PROJECT_ROOT}"

HOST="${COMFYUI_HOST:-127.0.0.1}"
PORT="${COMFYUI_PORT:-8188}"

echo "==> ComfyUI 起動（CPU モード）: http://${HOST}:${PORT}"
python main.py --cpu --listen "$HOST" --port "$PORT"
