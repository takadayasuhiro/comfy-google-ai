import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from app.config import base_href, public_path, settings
from app.models.schemas import (
    EnhancePromptRequest,
    EnhancePromptResponse,
    GeneratedImageInfo,
    UiGenerateRequest,
    UiGenerateResponse,
)
from app.services.comfy_runner import (
    ComfyWorkflowError,
    ComfyWorkflowTimeout,
    run_google_ai_edit_workflow,
    run_google_ai_workflow,
)
from app.services.prompt_enhancer import PromptEnhancer
from app.services.style_presets import list_styles
from app.services.workflow_builder import build_google_ai_workflow

router = APIRouter()
_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
_ALLOWED_UPLOAD = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


@router.get("/ui", response_class=HTMLResponse)
async def ui_page() -> HTMLResponse:
    html = (_STATIC_DIR / "index.html").read_text(encoding="utf-8")
    html = html.replace("{{BASE}}", base_href())
    return HTMLResponse(html)


@router.get("/api/styles")
async def get_styles() -> list[dict[str, str]]:
    return list_styles()


@router.post("/api/enhance-prompt", response_model=EnhancePromptResponse)
async def enhance_prompt(request: EnhancePromptRequest) -> EnhancePromptResponse:
    try:
        enhancer = PromptEnhancer()
        enhanced = await enhancer.enhance(request.prompt, mode=request.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        msg = str(exc)
        if "503" in msg or "UNAVAILABLE" in msg:
            raise HTTPException(
                status_code=503,
                detail="Gemini が混雑中です。しばらく待ってから再度お試しください。",
            ) from exc
        raise HTTPException(status_code=502, detail=f"プロンプト拡張エラー: {exc}") from exc

    return EnhancePromptResponse(
        original_prompt=request.prompt,
        enhanced_prompt=enhanced,
    )


@router.post("/api/upload-image")
async def upload_image(file: UploadFile = File(...)) -> dict:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_UPLOAD:
        raise HTTPException(status_code=400, detail="対応形式: PNG, JPG, WEBP, GIF")

    settings.comfyui_output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"upload_{uuid.uuid4().hex[:12]}{suffix}"
    dest = settings.comfyui_output_dir / filename

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="ファイルサイズは 10MB 以下にしてください")
    dest.write_bytes(content)

    return {
        "filename": filename,
        "url": public_path(f"/comfy-output/{filename}"),
    }


@router.post("/api/generate-via-comfy", response_model=UiGenerateResponse)
async def generate_via_comfy(request: UiGenerateRequest) -> UiGenerateResponse:
    """プロンプト → ComfyUI ワークフロー → Google AI API → 画像 URL を返す。"""
    is_edit = bool(request.reference_image)
    try:
        if is_edit:
            result = await run_google_ai_edit_workflow(
                request.prompt,
                request.reference_image,  # type: ignore[arg-type]
                model=request.model,
                auto_enhance=request.auto_enhance,
            )
        else:
            result = await run_google_ai_workflow(
                request.prompt,
                provider=request.provider,
                model=request.model,
                aspect_ratio=request.aspect_ratio,
                auto_enhance=request.auto_enhance,
                style=request.style,
                enhanced_prompt=request.enhanced_prompt,
            )
    except ComfyWorkflowTimeout as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except ComfyWorkflowError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"生成エラー: {exc}") from exc

    images = [
        GeneratedImageInfo(
            filename=img["filename"],
            url=public_path(f"/comfy-output/{img['filename']}"),
        )
        for img in result["images"]
    ]

    return UiGenerateResponse(
        prompt_id=result["prompt_id"],
        prompt=result["prompt"],
        provider=result["provider"],
        model=result["model"],
        images=images,
        mode="edit" if is_edit else "generate",
        reference_image=result.get("reference_image"),
        original_prompt=result.get("original_prompt"),
        enhanced_prompt=result.get("enhanced_prompt"),
        style=request.style if not is_edit else None,
        workflow_nodes=result.get("workflow_nodes", []),
    )


@router.get("/api/workflow-template")
async def workflow_template(
    prompt: str = "a serene landscape at sunset",
    provider: str = "imagen",
    aspect_ratio: str = "1:1",
    style: str = "none",
) -> dict:
    return build_google_ai_workflow(
        prompt,
        provider=provider,
        aspect_ratio=aspect_ratio,
        user_prompt=prompt,
        style=style,
    )


@router.get("/comfy-output/{filename}")
async def serve_comfy_output(filename: str) -> FileResponse:
    path = settings.comfyui_output_dir / Path(filename).name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="画像が見つかりません")
    return FileResponse(path)
