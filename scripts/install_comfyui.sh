#!/usr/bin/env bash
# ComfyUI を CPU モード用にクローン・セットアップする
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

if [ ! -d "comfyui" ]; then
  echo "==> ComfyUI をクローン中..."
  git clone --depth 1 https://github.com/Comfy-Org/ComfyUI.git comfyui
fi

echo "==> ComfyUI 依存をインストール中（CPU 版 PyTorch）..."
pip install -r requirements-comfyui.txt

if [ -f "comfyui/requirements.txt" ]; then
  pip install -r comfyui/requirements.txt
fi

echo "==> カスタムノードをリンク中..."
mkdir -p comfyui/custom_nodes
ln -sfn "$PROJECT_ROOT/custom_nodes/google_ai_nodes" \
  comfyui/custom_nodes/google_ai_nodes

echo "==> 完了。起動: bash scripts/start_comfyui.sh"
