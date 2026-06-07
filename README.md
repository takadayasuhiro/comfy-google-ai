# comfy-google-ai

ComfyUI + Google AI API を仲介する画像生成 Web アプリです。

- 日本語プロンプト → AI 英語拡張 → Imagen / Gemini で新規生成
- Image to Image カスタマイズ（Gemini 編集 API）
- ギャラリー、スタイル選択、ドラッグ＆ドロップ UI

## クイックスタート（自宅・開発）

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # GOOGLE_API_KEY を設定
bash scripts/install_comfyui.sh
bash scripts/start_api_bg.sh
bash scripts/start_comfyui.sh
```

ブラウザ: http://localhost:8000/ui

## 会社サーバー向け

[docs/company-implementation-2026-06-07.md](docs/company-implementation-2026-06-07.md) を参照してください。

- アクセス URL: **http://localhost/gazou**
- 環境変数テンプレ: `.env.company.example`
- nginx 設定: `deploy/nginx/`

## 構成

| コンポーネント | 説明 |
|----------------|------|
| FastAPI (`app/`) | Web API + UI（venv） |
| ComfyUI (`comfyui/`) | ワークフローエンジン（別途 clone） |
| nginx | 会社向け URL パス分離（OS パッケージ、venv 外） |

## ライセンス

各依存プロジェクトのライセンスに従います。
