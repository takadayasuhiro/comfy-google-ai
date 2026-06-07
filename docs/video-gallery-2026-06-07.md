# 動画生成・ギャラリー機能（2026/06/07）

Veo 動画生成とギャラリー拡張の技術メモです。

---

## 1. 動画生成アーキテクチャ

画像は ComfyUI ワークフロー経由、**動画は FastAPI が Google Veo API に直接接続**します（長時間オペレーションのため）。

```
UI（動画タブ）
  → POST /api/generate-video
  → video_jobs（バックグラウンド asyncio タスク）
    → run_prompt_pipeline(mode=video)  # 英語拡張 + スタイル suffix
    → GoogleAIService.generate_video()
      → client.aio.models.generate_videos()
      → operations ポーリング（10秒間隔）
      → files.download() → comfyui/output/veo_*.mp4
      → ffmpeg で veo_*_thumb.jpg（任意）
  ← GET /api/generate-video/{job_id}（フロント 5秒ポーリング）
```

### Veo モデル名（重要）

本プロジェクトは **Gemini Developer API（API キー）** を使用します。

| Gemini API（本リポジトリ） | Vertex AI（別途 GCP） |
|---------------------------|----------------------|
| `veo-3.1-lite-generate-preview` | `veo-3.1-lite-generate-001` |
| `veo-3.1-generate-preview` | `veo-3.1-generate-001` |
| `veo-3.1-fast-generate-preview` | — |

`-001` を Gemini API に指定すると **404** になります。

利用可能モデルの確認:

```bash
export GEMINI_API_KEY=$(grep '^GOOGLE_API_KEY=' .env | cut -d= -f2)
curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=${GEMINI_API_KEY}" | grep -i veo
```

---

## 2. UI（動画タブ）

| 項目 | 内容 |
|------|------|
| モデル | Veo 3.1 Lite / Fast / 3.1 / 2.0 |
| 尺 | 4 / 6 / 8 秒 |
| アスペクト比 | 16:9、9:16 |
| スタイル | 画像と同じプリセット（`style_presets.py`） |
| プレビュー | カスタム再生コントロール（⏪ ▶ ⏸ ⏹ ⏩ + シークバー） |
| 保存先 | `comfyui/output/veo_*.mp4` |

生成完了後、右ペインの **映像エリアをドラッグ** して左ギャラリーへ追加（画像と同様）。

---

## 3. ギャラリー

### 画像

- クリック → **モーダル**で拡大表示
- ダブルクリック → 参照画像（Image to Image）に設定
- 左端 ⠿ → ペイント等へファイルドラッグ

### 動画

- サムネイル（`veo_*_thumb.jpg` またはブラウザキャプチャ）
- クリック → モーダルで簡易再生
- ↓ → mp4 ダウンロード、📋 → サムネをクリップボード

### サムネイル解決順序

1. 保存済み `thumbUrl`（localStorage）
2. サーバー `comfy-output/veo_xxx_thumb.jpg`
3. `GET /api/video-thumbnail/{filename}`（ffmpeg 生成）
4. ブラウザで動画フレームを canvas キャプチャ

**ffmpeg 推奨**:

```bash
sudo apt install -y ffmpeg
```

---

## 4. コンテンツポリシー

Veo は Google の Responsible AI ポリシーにより、未成年・性的表現等のプロンプトを拒否します。

- エラー例: `sensitive words that violate Google's Responsible AI practices`
- 対処: 成人の描写に言い換え（例: 「女子高生」→「20代の女性」）
- 動画用プロンプト拡張（`mode: video`）で安全な英語への言い換えを試行

---

## 5. 関連ファイル

| ファイル | 役割 |
|----------|------|
| `app/services/google_ai.py` | `generate_video()`, サムネ生成 |
| `app/services/video_jobs.py` | 非同期ジョブ管理 |
| `app/services/prompt_pipeline.py` | 動画モードのスタイル適用 |
| `app/routers/ui.py` | 動画 API、サムネ API |
| `app/static/index.html` | 画像/動画タブ、モーダル、ギャラリー |

---

## 6. Phase2（未実装）

- image-to-video
- ギャラリーへの mp4 メタ（プロンプト）保存
- ComfyUI カスタムノード経由の動画生成

---

## 7. 料金

動画生成は **Veo API 従量課金**（無料枠なし）です。Google AI Pro サブスクだけでは API は無制限になりません。

| モデル例 | 目安（6秒 720p） |
|----------|------------------|
| `veo-3.1-lite-generate-preview`（デフォルト） | 約 $0.30 / 本 |
| `veo-3.1-generate-preview`（高品質） | 約 $2.40 / 本 |

詳細: [billing-and-usage-2026-06-07.md](billing-and-usage-2026-06-07.md)

---

*作成日: 2026/06/07*
