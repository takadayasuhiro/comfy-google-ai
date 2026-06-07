from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.config import public_path, settings
from app.models.schemas import (
    EditImageRequest,
    GenerateImageRequest,
    GenerateImageResponse,
    GeneratedImageInfo,
)
from app.services.google_ai import GoogleAIService


def _safe_filename(filename: str) -> str:
    return Path(filename).name


router = APIRouter()


@router.post("/image", response_model=GenerateImageResponse)
async def generate_image(request: GenerateImageRequest) -> GenerateImageResponse:
    try:
        service = GoogleAIService()
        save_dir = (
            settings.comfyui_output_dir if request.save_to_comfy else settings.output_dir
        )
        paths = await service.generate(
            prompt=request.prompt,
            model=request.model,
            provider=request.provider,
            number_of_images=request.number_of_images,
            aspect_ratio=request.aspect_ratio,
            output_dir=save_dir,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Google AI API エラー: {exc}") from exc

    if not paths:
        raise HTTPException(status_code=502, detail="画像が生成されませんでした")

    base = settings.comfyui_output_dir.parent if request.save_to_comfy else settings.output_dir.parent
    return GenerateImageResponse(
        model=request.model or settings.google_image_model,
        provider=request.provider,
        images=[str(p.relative_to(base)) for p in paths],
        prompt=request.prompt,
    )


@router.post("/edit")
async def edit_image(request: EditImageRequest) -> dict:
    """参照画像 + プロンプトでカスタマイズ（ComfyUI カスタムノードからも呼ばれる）。"""
    safe_name = _safe_filename(request.reference_image)
    image_path = settings.comfyui_output_dir / safe_name
    if not image_path.is_file():
        raise HTTPException(status_code=404, detail=f"参照画像が見つかりません: {safe_name}")

    try:
        service = GoogleAIService()
        paths = await service.edit_image(
            prompt=request.prompt,
            image_path=image_path,
            model=request.model,
            output_dir=settings.comfyui_output_dir,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Google AI API エラー: {exc}") from exc

    if not paths:
        raise HTTPException(status_code=502, detail="編集画像が生成されませんでした")

    return {
        "model": request.model or settings.google_edit_model,
        "provider": "gemini-edit",
        "prompt": request.prompt,
        "reference_image": safe_name,
        "images": [
            GeneratedImageInfo(
                filename=p.name,
                url=public_path(f"/comfy-output/{p.name}"),
            ).model_dump()
            for p in paths
        ],
    }
