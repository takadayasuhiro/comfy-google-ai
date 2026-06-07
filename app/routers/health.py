from fastapi import APIRouter

from app.config import settings
from app.services.comfy_client import ComfyUIClient

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    comfy = ComfyUIClient()
    comfyui_ok = await comfy.health()

    return {
        "status": "ok",
        "google_api_key_set": bool(settings.google_api_key),
        "comfyui_reachable": comfyui_ok,
        "comfyui_url": settings.comfyui_base_url,
    }
