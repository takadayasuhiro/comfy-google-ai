# comfy-google-ai

ComfyUI + Google AI API を仲介する画像・動画生成 Web アプリです。

- **画像**: 日本語プロンプト → AI 英語拡張 → Imagen / Gemini で新規生成
- **動画**: Veo API でテキストから mp4 生成（ComfyUI 経由なし・ジョブポーリング）
- **カスタマイズ**: Image to Image（Gemini 編集 API）
- **UI**: ギャラリー、スタイル選択、モーダルプレビュー、ドラッグ＆ドロップ

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

動画サムネイル生成（推奨）:

```bash
sudo apt install -y ffmpeg
```

ブラウザ: http://localhost:8000/ui

## 主な機能（2026/06/07 時点）

| 機能 | 説明 |
|------|------|
| 画像タブ | Imagen / Gemini、スタイル、アスペクト比、ComfyUI ワークフロー経由 |
| 動画タブ | Veo 3.1 Lite / Fast / 3.1 / 2.0、尺 4〜8秒、16:9 / 9:16 |
| スタイル | 水彩・サイバーパンク・アニメ等（画像・動画共通） |
| ギャラリー | localStorage、並び替え、クリックでモーダル再生、サムネ自動補完 |
| 会社向け | nginx サブパス `/gazou` 対応 |

詳細: [docs/video-gallery-2026-06-07.md](docs/video-gallery-2026-06-07.md)

## API 料金・利用枠（必読）

本アプリは **AI Studio API キー（従量課金）** を使用します。**Google AI Pro のサブスク契約だけでは API 利用は無制限になりません。**

| 目安（Paid Tier） | 単価 |
|-------------------|------|
| Imagen 4 Standard | 約 $0.04 / 枚 |
| Veo 3.1 Lite 6秒 720p | 約 $0.30 / 本 |

$10 GCP クレジット（Pro 特典）のみの場合: 動画 **約30本/月** または 画像 **約250枚/月** が目安です。

詳細: [docs/billing-and-usage-2026-06-07.md](docs/billing-and-usage-2026-06-07.md)

## 環境変数（抜粋）

| 変数 | デフォルト | 説明 |
|------|------------|------|
| `GOOGLE_API_KEY` | — | 必須。[AI Studio](https://aistudio.google.com/apikey)（**従量課金・Spend Cap 推奨**） |
| `GOOGLE_VIDEO_MODEL` | `veo-3.1-lite-generate-preview` | **Gemini API は `-preview` サフィックス** |
| `APP_BASE_PATH` | 空 | 会社: `/gazou` |

テンプレ: `.env.example`（自宅）、`.env.company.example`（会社）

## 会社サーバー向け

[docs/company-implementation-2026-06-07.md](docs/company-implementation-2026-06-07.md) を参照してください。

- アクセス URL: **http://localhost/gazou**
- 環境変数テンプレ: `.env.company.example`
- nginx 設定: `deploy/nginx/`

## 構成

| コンポーネント | 説明 |
|----------------|------|
| FastAPI (`app/`) | Web API + UI（venv） |
| ComfyUI (`comfyui/`) | 画像ワークフローエンジン（動画は FastAPI 直結） |
| nginx | 会社向け URL パス分離（OS パッケージ、venv 外） |
| ffmpeg | 動画サムネイル生成（OS パッケージ、任意だが推奨） |

### API エンドポイント（動画）

| メソッド | パス | 説明 |
|----------|------|------|
| POST | `/api/generate-video` | Veo ジョブ開始 |
| GET | `/api/generate-video/{job_id}` | ステータス取得 |
| GET | `/api/video-thumbnail/{filename}` | サムネ jpg 生成・取得 |

## ライセンス

各依存プロジェクトのライセンスに従います。
