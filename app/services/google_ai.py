import asyncio
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image

from app.config import settings

_VIDEO_POLL_INTERVAL_SEC = 10.0


def _format_veo_error(error: object) -> str:
    """Veo API エラーをユーザー向け日本語メッセージに変換する。"""
    text = str(error)
    if isinstance(error, dict):
        text = str(error.get("message") or error)
    lower = text.lower()
    if "sensitive words" in lower or "responsible ai" in lower:
        return (
            "プロンプトが Google のコンテンツポリシーに抵触しました。"
            "未成年・性的表現・暴力などを避け、別の表現に言い換えてください。"
            "（例: 「女子高生」→「20代の女性」「大学生」など成人の描写）"
        )
    if "429" in text or "resource_exhausted" in lower or "quota" in lower:
        return "Veo の利用上限に達しました。しばらく待ってから再度お試しください。"
    if "503" in text or "unavailable" in lower:
        return "Veo API が混雑中です。しばらく待ってから再度お試しください。"
    return f"Veo 生成エラー: {text}"


@dataclass
class SavedVideo:
    video_path: Path
    thumb_path: Path | None = None


class GoogleAIService:
    """Google AI（Imagen / Gemini）による画像生成サービス。"""

    def __init__(self) -> None:
        if not settings.google_api_key:
            raise ValueError(
                "GOOGLE_API_KEY が未設定です。.env に API キーを設定してください。"
            )
        self._client = genai.Client(api_key=settings.google_api_key)

    async def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        provider: str = "imagen",
        number_of_images: int = 1,
        aspect_ratio: str = "1:1",
        output_dir: Path | None = None,
    ) -> list[Path]:
        model = model or settings.google_image_model
        save_dir = output_dir or settings.output_dir
        save_dir.mkdir(parents=True, exist_ok=True)

        if provider == "gemini":
            return await self._generate_with_gemini(
                prompt=prompt,
                model=model,
                aspect_ratio=aspect_ratio,
                save_dir=save_dir,
            )

        return await self._generate_with_imagen(
            prompt=prompt,
            model=model,
            number_of_images=number_of_images,
            aspect_ratio=aspect_ratio,
            save_dir=save_dir,
        )

    async def _generate_with_imagen(
        self,
        *,
        prompt: str,
        model: str,
        number_of_images: int,
        aspect_ratio: str,
        save_dir: Path,
    ) -> list[Path]:
        response = await self._client.aio.models.generate_images(
            model=model,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=number_of_images,
                aspect_ratio=aspect_ratio,
                output_mime_type="image/png",
            ),
        )

        saved: list[Path] = []
        for generated in response.generated_images:
            filename = f"imagen_{uuid.uuid4().hex[:12]}.png"
            path = save_dir / filename
            generated.image.save(path)
            saved.append(path)
        return saved

    async def _generate_with_gemini(
        self,
        *,
        prompt: str,
        model: str,
        aspect_ratio: str,
        save_dir: Path,
    ) -> list[Path]:
        response = await self._client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
            ),
        )

        saved: list[Path] = []
        for part in response.parts:
            if part.inline_data is None:
                continue
            image = part.as_image()
            filename = f"gemini_{uuid.uuid4().hex[:12]}.png"
            path = save_dir / filename
            image.save(path)
            saved.append(path)
        return saved

    async def edit_image(
        self,
        prompt: str,
        image_path: Path,
        *,
        model: str | None = None,
        output_dir: Path | None = None,
    ) -> list[Path]:
        """参照画像 + テキスト指示で画像をカスタマイズ（Gemini）。"""
        model = model or settings.google_edit_model
        save_dir = output_dir or settings.comfyui_output_dir
        save_dir.mkdir(parents=True, exist_ok=True)

        source = Image.open(image_path)
        edit_instruction = (
            "Edit this reference image. "
            "CRITICAL: Keep the same main subject — preserve their face, gender, age, "
            "hairstyle, clothing, and identity. Do NOT replace them with different people.\n\n"
            f"Apply only these changes:\n{prompt}"
        )
        response = await self._client.aio.models.generate_content(
            model=model,
            contents=[source, edit_instruction],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        saved: list[Path] = []
        for part in response.parts:
            if part.inline_data is None:
                continue
            image = part.as_image()
            filename = f"gemini_edit_{uuid.uuid4().hex[:12]}.png"
            path = save_dir / filename
            image.save(path)
            saved.append(path)
        return saved

    async def generate_video(
        self,
        prompt: str,
        *,
        model: str | None = None,
        duration_seconds: int = 6,
        aspect_ratio: str = "16:9",
        output_dir: Path | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> SavedVideo:
        """Veo API でテキストから動画を生成し mp4 として保存する。"""
        model = model or settings.google_video_model
        save_dir = output_dir or settings.comfyui_output_dir
        save_dir.mkdir(parents=True, exist_ok=True)

        if on_progress:
            on_progress("Veo API にリクエスト送信中…")

        try:
            operation = await self._client.aio.models.generate_videos(
                model=model,
                source=types.GenerateVideosSource(prompt=prompt),
                config=types.GenerateVideosConfig(
                    number_of_videos=1,
                    duration_seconds=duration_seconds,
                    aspect_ratio=aspect_ratio,
                ),
            )
        except Exception as exc:
            raise RuntimeError(_format_veo_error(exc)) from exc

        poll_count = 0
        while not operation.done:
            poll_count += 1
            if on_progress:
                on_progress(f"Veo で生成中…（{poll_count * int(_VIDEO_POLL_INTERVAL_SEC)}秒経過）")
            await asyncio.sleep(_VIDEO_POLL_INTERVAL_SEC)
            operation = await self._client.aio.operations.get(operation=operation)

        if operation.error:
            raise RuntimeError(_format_veo_error(operation.error))

        result = operation.result
        if not result or not result.generated_videos:
            raise RuntimeError("Veo から動画が返されませんでした")

        video = result.generated_videos[0].video
        if video is None:
            raise RuntimeError("生成動画オブジェクトが空です")

        if on_progress:
            on_progress("動画をダウンロード中…")

        # aio.files.download は sync 版と違い video.video_bytes を設定しないため、
        # 返却バイトを直接保存する。
        video_bytes = await self._client.aio.files.download(file=video)
        if not video_bytes:
            raise RuntimeError("動画のダウンロードに失敗しました")

        filename = f"veo_{uuid.uuid4().hex[:12]}.mp4"
        path = save_dir / filename
        path.write_bytes(video_bytes)

        if on_progress:
            on_progress("サムネイルを作成中…")
        thumb_path = await self._create_video_thumbnail(path)
        return SavedVideo(video_path=path, thumb_path=thumb_path)

    async def _create_video_thumbnail(self, video_path: Path) -> Path | None:
        return await create_video_thumbnail_file(video_path)


async def create_video_thumbnail_file(video_path: Path) -> Path | None:
    """ffmpeg があれば動画の先頭付近からサムネイル jpg を生成する。"""
    thumb_path = video_path.with_name(f"{video_path.stem}_thumb.jpg")
    if thumb_path.is_file() and thumb_path.stat().st_size > 0:
        return thumb_path

    for seek in ("0.1", "0.5", "1.0"):
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-y",
                "-ss",
                seek,
                "-i",
                str(video_path),
                "-vframes",
                "1",
                "-q:v",
                "3",
                str(thumb_path),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            if proc.returncode == 0 and thumb_path.is_file() and thumb_path.stat().st_size > 0:
                return thumb_path
        except (FileNotFoundError, OSError):
            break
    return None
