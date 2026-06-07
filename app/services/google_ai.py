import uuid
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image

from app.config import settings


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
