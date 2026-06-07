#!/usr/bin/env bash
# 初回 GitHub 公開用（WSL Ubuntu で実行）
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

if git diff --cached --name-only 2>/dev/null | grep -qx '.env'; then
  echo "ERROR: .env がステージされています。コミットを中止します。"
  exit 1
fi

git check-ignore -q .env || { echo "WARN: .env が .gitignore にありません"; exit 1; }

git add -A
git status --short

if ! git diff --cached --quiet 2>/dev/null; then
  git commit -m "$(cat <<'EOF'
Add company deployment guide and /gazou subpath support.

Document WSL/nginx/FastAPI architecture for office rollout, nginx templates,
APP_BASE_PATH routing, and Phase2 FLUX img2img plan.
EOF
)"
fi

git branch -M main 2>/dev/null || true

if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  if git remote get-url origin >/dev/null 2>&1; then
    git push -u origin main
  else
    gh repo create comfy-google-ai --public --source=. --remote=origin --push
  fi
  echo "==> GitHub URL:"
  gh repo view --json url -q .url
else
  echo "==> gh 未認証のため手動でリモートを追加してください:"
  echo "    git remote add origin git@github.com:<USER>/comfy-google-ai.git"
  echo "    git push -u origin main"
fi
