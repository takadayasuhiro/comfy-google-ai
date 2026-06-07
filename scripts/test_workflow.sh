#!/usr/bin/env bash
# サンプルワークフローを FastAPI 経由で ComfyUI に投入する
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

API_URL="${GOOGLE_AI_BRIDGE_URL:-http://127.0.0.1:8000}"

PAYLOAD=$(python3 -c "
import json, pathlib
wf = json.loads(pathlib.Path('$PROJECT_ROOT/workflows/text_to_image_api.json').read_text())
print(json.dumps({'workflow': wf}))
")

echo "==> ワークフロー投入: $API_URL/workflow/submit"
RESPONSE=$(curl -s -X POST "$API_URL/workflow/submit" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

echo "$RESPONSE" | python3 -m json.tool
PROMPT_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['prompt_id'])")

echo "==> 完了待ち (prompt_id: $PROMPT_ID) ..."
for _ in $(seq 1 60); do
  HISTORY=$(curl -s "$API_URL/workflow/history/$PROMPT_ID")
  if echo "$HISTORY" | python3 -c "
import sys, json
data = json.load(sys.stdin)
entry = data.get('$PROMPT_ID', {})
status = entry.get('status', {})
if status.get('completed'):
    outputs = entry.get('outputs', {})
    for node_out in outputs.values():
        for img in node_out.get('images', []):
            print(img['filename'])
    sys.exit(0)
if status.get('status_str') == 'error':
    msgs = status.get('messages', [])
    print('ERROR:', msgs, file=sys.stderr)
    sys.exit(2)
sys.exit(1)
" 2>/dev/null; then
    echo "==> ワークフロー完了"
    exit 0
  fi
  sleep 3
done

echo "==> タイムアウト。履歴を確認: $API_URL/workflow/history/$PROMPT_ID"
exit 1
