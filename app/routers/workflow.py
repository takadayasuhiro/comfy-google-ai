import httpx
from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models.schemas import WorkflowSubmitRequest, WorkflowSubmitResponse
from app.services.comfy_client import ComfyUIClient

router = APIRouter()


@router.post("/submit", response_model=WorkflowSubmitResponse)
async def submit_workflow(request: WorkflowSubmitRequest) -> WorkflowSubmitResponse:
    """ComfyUI にワークフローを投入する（画像生成ノードはカスタムノード経由で Google AI を呼ぶ想定）。"""
    client = ComfyUIClient()

    if not await client.health():
        raise HTTPException(
            status_code=503,
            detail=(
                f"ComfyUI に接続できません ({settings.comfyui_base_url})。"
                " scripts/start_comfyui.sh で CPU モード起動してください。"
            ),
        )

    try:
        prompt_id = await client.queue_prompt(
            workflow=request.workflow,
            client_id=request.client_id,
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=exc.response.text,
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return WorkflowSubmitResponse(
        prompt_id=prompt_id,
        comfyui_url=settings.comfyui_base_url,
        message="ワークフローを ComfyUI キューに投入しました",
    )


@router.get("/history/{prompt_id}")
async def get_workflow_history(prompt_id: str) -> dict:
    client = ComfyUIClient()
    try:
        return await client.get_history(prompt_id)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
