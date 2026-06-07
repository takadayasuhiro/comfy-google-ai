# 会社向け実装ガイド（2026/06/07）

ComfyUI + Google AI 画像生成システムを会社 AI サーバー（WSL2）へ展開するための手順書です。  
GitHub からクローンして再デプロイし、社員は **`http://localhost/gazou`** で利用します。

---

## 1. 概要

### 目的

- 日本語プロンプトから高品質な画像を生成（新規生成は Google Imagen / Gemini API）
- ComfyUI をワークフローエンジンとして利用（ノード連携の可視化・拡張性）
- カスタマイズ（Image to Image）は Phase2 で **FLUX.1 Schnell img2img（ローカル GPU）** を追加予定
- 他 AI システム（エージェント LLM、ベクトル DB）と **ポート 80 を共有**し、URL パスで分離

### 自宅 vs 会社

| 項目 | 自宅 | 会社 |
|------|------|------|
| GPU | 不可（CPU モード） | RTX 5080（VRAM 16GB） |
| RAM | — | 64GB |
| UI アクセス | `http://localhost:8000/ui` | **`http://localhost/gazou`** |
| 新規生成 | Google API | Google API |
| カスタマイズ | Google Gemini 編集 API | Phase1: Google / **Phase2: FLUX Schnell** |
| ComfyUI | `--cpu` | Phase1: `--cpu` / Phase2: **GPU** |

---

## 2. システム構成（プロセス・依存関係）

本システムは **3 つの独立プロセス** と **1 つの OS サービス** で動作します。  
**nginx は Python venv に含まれません。**

| 役割 | 実体 | インストール方法 | ポート |
|------|------|------------------|--------|
| Web アプリ（API + UI） | FastAPI + uvicorn | `venv` + `requirements.txt` | 8000（内部） |
| ワークフローエンジン | ComfyUI | `comfyui/` + `requirements-comfyui.txt` | 8188（内部のみ） |
| 画像生成 API | Google Imagen / Gemini | SDK 経由（クラウド） | — |
| リバースプロキシ | **nginx** | **OS**: `sudo apt install nginx` | 80（社員向け入口） |

### リポジトリに含まれるもの / 含まれないもの

| 含まれる | 含まれない（別途セットアップ） |
|----------|-------------------------------|
| FastAPI アプリ (`app/`) | ComfyUI 本体（`install_comfyui.sh` で clone） |
| カスタムノード (`custom_nodes/`) | nginx 本体（`apt install`） |
| nginx **設定テンプレ** (`deploy/nginx/`) | FLUX モデルファイル（Phase2） |
| 起動スクリプト (`scripts/`) | `.env`（API キー、git 除外） |

### リクエストの流れ

**会社（nginx あり）:**

```
ブラウザ http://localhost/gazou
  → nginx（:80、systemd / OS サービス）
    → uvicorn / FastAPI（:8000、venv 内）
      → ComfyUI（:8188、別 Python プロセス）
        → カスタムノード → FastAPI → Google AI API
```

**自宅（nginx なし）:**

```
ブラウザ http://localhost:8000/ui
  → uvicorn / FastAPI（:8000）
    → ComfyUI（:8188）
      → Google AI API
```

`APP_BASE_PATH` を空にすれば自宅はポート直アクセスのまま動作します。nginx は会社向けのオプションです。

### Python 依存（venv）

`requirements.txt` の主なパッケージ:

- `fastapi`, `uvicorn` — Web サーバー（アプリ本体）
- `google-genai` — Google AI API
- `httpx` — ComfyUI との通信
- `Pillow` — 画像処理

`requirements-comfyui.txt` は ComfyUI 用（venv または同一 venv に追加インストール）。

### 環境変数の要点

| 変数 | 自宅 | 会社 |
|------|------|------|
| `APP_BASE_PATH` | 空 | `/gazou` |
| `APP_PORT` | `8000` | `8000`（nginx が転送） |
| `EDIT_BACKEND` | `google` | Phase1: `google` / Phase2: `flux_local` |
| `GOOGLE_API_KEY` | 必須 | 必須 |

テンプレ: [`.env.example`](../.env.example)（自宅）、[`.env.company.example`](../.env.company.example)（会社）

---

## 3. 現状機能まとめ（リポジトリ現行版）

### UI 機能

- **左ペイン**: ギャラリー（3列、ドラッグ並び替え、localStorage 保存、ペイント等へ File ドラッグ）
- **中央**: プロンプト入力、AIプロンプター、スタイル / API / アスペクト比、生成ボタン
- **右ペイン**: 生成結果（スクロール不要の横並びレイアウト）
- **Image to Image**: ギャラリーまたは生成結果から参照画像をドラッグ
- **AI拡張プレビュー**: 生成ボタン下に英語プロンプト表示（スタイル変更はクライアント側 suffix 適用）

### バックエンド構成

```
ブラウザ (localhost/gazou)
  → nginx :80（URL パス分離）
    → FastAPI :8000
      → ComfyUI :8188（内部のみ、社員非公開）
        → custom_nodes/google_ai_nodes/
          → FastAPI /generate/image, /generate/edit, /api/enhance-prompt
            → Google AI API
```

### ワークフロー

| モード | ノード連鎖 |
|--------|------------|
| 新規生成 | AIプロンプター → スタイル適用 → 画像生成 → 保存 |
| カスタマイズ | AIプロンプター → 画像カスタマイズ → 保存 |

### 設計上の注意（既知）

- **カスタマイズ時**はスタイル / API / アスペクト比を非表示（人物維持優先、API の性質上）
- **ギャラリー**には現状 `filename` と `url` のみ保存（英語プロンプトメタは未保存、Phase2 以降で拡張可）
- **プロンプト拡張**は Gemini API 使用。混雑時 503 が出ることがある（リトライ実装済み）

### 実装上の修正履歴（2026/06/07 時点）

| 問題 | 対応 |
|------|------|
| スタイル変更後の再生成エラー | `enhanced_prompt` キャッシュ再利用、拡張 API リクエストの重複防止 |
| 英語プレビュー位置 | 生成ボタンの下に移動 |
| 生成結果が画面最下部 | 右ペインに配置（横並びレイアウト） |
| ギャラリーからのドラッグ不可 | 並び替え用データと画像データの両方がある場合もドロップ受付 |
| `/gazou` サブパス | `APP_BASE_PATH`、`public_path()`、`<base href>`、uvicorn `--root-path` |

---

## 4. 会社ハードウェア前提

| リソース | 仕様 |
|----------|------|
| GPU | NVIDIA RTX 5080（VRAM 16GB） |
| RAM | 64GB |
| OS | Windows + WSL2（Ubuntu） |
| 共有 | ベクトル DB、機密データ用 AI エージェント LLM |

### VRAM 競合について

- **ベクトル DB**（Chroma / Qdrant 等）は基本 CPU + RAM。VRAM を使うのは埋め込みモデルを GPU で回す場合のみ
- **エージェント LLM** が VRAM の主な常駐消費源
- **FLUX img2img** は推論時のみ 6〜10GB 程度のピーク（Schnell + GGUF Q4 想定）
- **新規生成（Google API）** は VRAM を使わない

**結論**: 全部を常時 VRAM に載せるのではなく、**オンデマンドロード + GPU ジョブ直列キュー** で共存可能。

---

## 5. リソース共有方針（Phase2 向け）

1. **新規生成は常に Google API** — VRAM を占有しない
2. **FLUX はカスタマイズ要求時のみロード** — 完了後 ComfyUI モデルキャッシュを解放
3. **GPU ジョブは直列化** — エージェント LLM と FLUX の同時実行を避ける
4. **エージェント LLM は業務優先** — 画像カスタマイズは空き時またはキュー待ち
5. **埋め込みモデルは CPU 実行も検討** — VRAM をエージェント用に確保

---

## 6. Phase1: デプロイ手順（GitHub から）

### 6.1 クローンと Python 環境

```bash
cd ~
git clone <your-github-repo-url> comfy-google-ai
cd comfy-google-ai

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 6.2 環境変数

```bash
cp .env.company.example .env
# GOOGLE_API_KEY を編集
nano .env
```

必須項目:

- `GOOGLE_API_KEY` — [Google AI Studio](https://aistudio.google.com/apikey) で取得
- `APP_BASE_PATH=/gazou` — 会社では必ず設定

### 6.3 ComfyUI セットアップ

```bash
bash scripts/install_comfyui.sh
```

### 6.4 サービス起動（管理者）

```bash
# ターミナル1: FastAPI
bash scripts/start_api_bg.sh

# ターミナル2: ComfyUI（Phase1 は CPU モード）
bash scripts/start_comfyui.sh

# nginx（初回のみ setup、以降は systemctl）
sudo cp deploy/nginx/ai-services.conf /etc/nginx/sites-available/ai-services
sudo ln -sf /etc/nginx/sites-available/ai-services /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 6.5 動作確認

```bash
bash scripts/status.sh
curl -sf http://127.0.0.1/gazou/health
```

ブラウザ（Windows）: **http://localhost/gazou**

---

## 7. Phase1: nginx URL 分離

> **補足**: nginx は venv ではなく **Ubuntu（WSL）のシステムパッケージ** です。  
> リポジトリにあるのは `deploy/nginx/*.conf` の設定テンプレートのみです。

### 考え方

ポート 80 を複数 AI サービスで共有し、**URL パス**で振り分けます。

| URL パス | 転送先 | 用途 |
|----------|--------|------|
| `/gazou/` | `127.0.0.1:8000` | 画像生成 UI（本システム） |
| `/agent/` | `127.0.0.1:9000`（例） | 機密エージェント LLM |
| `/` | 404 または社内ポータル | トップ |

設定テンプレート: [`deploy/nginx/ai-services.conf`](../deploy/nginx/ai-services.conf)

### WSL2 で nginx を入れる

```bash
sudo apt update
sudo apt install -y nginx
sudo systemctl enable nginx
```

### Windows ブラウザからのアクセス

WSL2 は `localhost` ポートフォワーディングが有効なため、Windows の Chrome/Edge から  
`http://localhost/gazou` で WSL 内 nginx に到達できます。

### 社員向け（このセクションだけ共有可）

> 画像生成ツールを開く: ブラウザで **http://localhost/gazou**  
> プロンプトを日本語で入力し「画像を生成する」をクリックしてください。

ポート番号（8000、8188）は **社員向け資料に記載しない** でください。

---

## 8. Phase2: FLUX.1 Schnell img2img 実装計画

### 目的

Google Gemini 編集 API は人物同一性の維持が不安定なため、**カスタマイズ時のみ**ローカル FLUX img2img に切り替え、参照画像の一部変更を安定させる。

### 必要コンポーネント

| 項目 | 内容 |
|------|------|
| モデル | FLUX.1 Schnell GGUF Q4/Q5 |
| カスタムノード | [ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF) |
| PyTorch | CUDA 版（`requirements-comfyui-gpu.txt` を新設予定） |
| VAE / CLIP | FLUX 用を `comfyui/models/` に配置 |

### ワークフロー（img2img）

```
LoadImage（参照画像）
  → VAEEncode
  → KSampler（denoise 0.35〜0.55）
  → VAEDecode
  → SaveImage
```

### コード変更予定

| ファイル | 変更 |
|----------|------|
| `app/config.py` | `EDIT_BACKEND=google\|flux_local` |
| `app/services/workflow_builder.py` | `build_flux_img2img_workflow()` 追加 |
| `app/services/comfy_runner.py` | カスタマイズ時バックエンド分岐 |
| `scripts/start_comfyui_gpu.sh` | `--cpu` なしで GPU 起動 |
| `app/static/index.html` | カスタマイズエンジン表示（任意） |

### 環境変数（Phase2）

```env
EDIT_BACKEND=flux_local
COMFYUI_GPU=1
FLUX_MODEL=flux1-schnell-Q4_K_S.gguf
FLUX_DENOISE=0.45
```

### ギャラリーメタデータ拡張（任意）

生成時の英語プロンプトをギャラリーに保存し、カスタマイズ時に `reference_context` として API に渡すと、人物・シーンの維持精度が上がる見込み。

```json
{
  "filename": "google_ai_xxx.png",
  "url": "/gazou/comfy-output/google_ai_xxx.png",
  "originalPrompt": "かわいい女子高生",
  "generationPrompt": "A charming Japanese high school girl...",
  "style": "anime"
}
```

### フォールバック

- GPU ビジー時: キュー待ち表示、または `EDIT_BACKEND=google` にフォールバック
- 自宅環境: `EDIT_BACKEND=google` のまま（変更不要）

---

## 9. 起動・停止・確認

### 起動（管理者）

```bash
cd ~/comfy-google-ai
bash scripts/start_api_bg.sh
bash scripts/start_comfyui.sh        # Phase1
# bash scripts/start_comfyui_gpu.sh  # Phase2
sudo systemctl start nginx
```

### 停止

```bash
pkill -f "uvicorn app.main:app"
pkill -f "python main.py"
```

### 状態確認

```bash
bash scripts/status.sh
```

### ログ

| サービス | ログ |
|----------|------|
| FastAPI | `/tmp/comfy-google-api.log` |
| ComfyUI | 起動ターミナル出力 |
| nginx | `/var/log/nginx/error.log` |

---

## 10. トラブルシュート

| 症状 | 対処 |
|------|------|
| `localhost/gazou` に繋がらない | `sudo systemctl status nginx`、`bash scripts/status.sh` |
| 画像が表示されない | 生成 URL が `/gazou/comfy-output/...` か確認。`APP_BASE_PATH` と nginx の整合 |
| 502 Bad Gateway | ComfyUI 未起動。`bash scripts/start_comfyui.sh` |
| プロンプト拡張 503 | Gemini 混雑。しばらく待つか生成ボタンを直接試す |
| API キーエラー | `.env` の `GOOGLE_API_KEY` を確認 |

---

## 11. セキュリティ

- `.env` と API キーを Git にコミットしない
- ComfyUI（8188）は `127.0.0.1` のみで待ち受け、nginx から公開しない
- 社外ネットワークへの公開が必要な場合は別途認証（Basic 認証、VPN 等）を検討
- 機密エージェント用データと生成画像の保存ディレクトリを分離することを推奨

---

## 付録: ディレクトリ構成

```
comfy-google-ai/
├── app/                    # FastAPI アプリ
│   ├── main.py
│   ├── config.py
│   ├── routers/
│   ├── services/
│   └── static/index.html   # Web UI
├── custom_nodes/           # ComfyUI カスタムノード
├── comfyui/                # ComfyUI 本体（git clone）
├── deploy/nginx/           # nginx 設定テンプレ
├── docs/                   # 本ドキュメント
├── scripts/                # 起動・インストールスクリプト
├── .env.company.example    # 会社向け env テンプレ
└── requirements.txt
```

---

*作成日: 2026/06/07*
