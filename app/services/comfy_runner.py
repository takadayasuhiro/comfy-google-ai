import asyncio
import time
from pathlib import Path
from typing import Any

import httpx

from app.config import settings
from app.services.comfy_client import ComfyUIClient
from app.services.prompt_pipeline import run_prompt_pipeline
from app.services.workflow_builder import (
    build_google_ai_edit_workflow,
    build_google_ai_workflow,
    workflow_node_chain,
)


class ComfyWorkflowError(Exception):
    pass


class ComfyWorkflowTimeout(ComfyWorkflowError):
    pass


def _extract_output_images(history_entry: dict[str, Any]) -> list[dict[str, str]]:
    images: list[dict[str, str]] = []
    for node_output in history_entry.get("outputs", {}).values():
        for image in node_output.get("images", []):
            images.append(
                {
                    "filename": image["filename"],
                    "subfolder": image.get("subfolder", ""),
                    "type": image.get("type", "output"),
                }
            )
    return images


async def run_google_ai_workflow(
    prompt: str,
    *,
    provider: str = "imagen",
    model: str | None = None,
    aspect_ratio: str = "1:1",
    auto_enhance: bool = True,
    style: str = "none",
    enhanced_prompt: str | None = None,
    timeout: float = 180.0,
    poll_interval: float = 2.0,
) -> dict[str, Any]:
    """ワークフローを組み立てて ComfyUI に投入し、完了まで待って結果を返す。"""
    client = ComfyUIClient()

    if not await client.health():
        raise ComfyWorkflowError(
            f"ComfyUI に接続できません ({settings.comfyui_base_url})"
        )

    pipeline = await run_prompt_pipeline(
        prompt,
        auto_enhance=auto_enhance,
        style=style,
        cached_enhanced=enhanced_prompt,
    )
    workflow = build_google_ai_workflow(
        pipeline.styled_prompt,
        provider=provider,
        model=model,
        aspect_ratio=aspect_ratio,
        user_prompt=pipeline.original_prompt,
        auto_enhance=auto_enhance,
        style=style,
        preprocessed=True,
    )

    try:
        prompt_id = await client.queue_prompt(workflow)
    except httpx.HTTPStatusError as exc:
        raise ComfyWorkflowError(exc.response.text) from exc
    except httpx.HTTPError as exc:
        raise ComfyWorkflowError(str(exc)) from exc

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        history = await client.get_history(prompt_id)
        entry = history.get(prompt_id)
        if not entry:
            await asyncio.sleep(poll_interval)
            continue

        status = entry.get("status", {})
        if status.get("completed"):
            images = _extract_output_images(entry)
            if not images:
                raise ComfyWorkflowError("ワークフローは完了しましたが画像がありません")
            return {
                "prompt_id": prompt_id,
                "images": images,
                "prompt": pipeline.styled_prompt,
                "provider": provider,
                "model": model or settings.google_image_model,
                "original_prompt": pipeline.original_prompt,
                "enhanced_prompt": pipeline.enhanced_prompt,
                "style": pipeline.style,
                "workflow_nodes": workflow_node_chain(workflow),
            }

        messages = status.get("messages", [])
        for msg in messages:
            if isinstance(msg, (list, tuple)) and len(msg) >= 2 and msg[0] == "execution_error":
                raise ComfyWorkflowError(str(msg[1]))

        if status.get("status_str") == "error":
            raise ComfyWorkflowError(f"ComfyUI 実行エラー: {messages}")

        await asyncio.sleep(poll_interval)

    raise ComfyWorkflowTimeout(
        f"タイムアウト ({timeout}s)。prompt_id={prompt_id}"
    )


def _resolve_output_filename(filename: str) -> str:
    return Path(filename).name


async def _edit_image_direct(
    prompt: str,
    safe_name: str,
    image_path: Path,
    *,
    model: str,
    prompt_id: str,
) -> dict[str, Any]:
    """ComfyUI ワークフローで画像が取れない場合のフォールバック。"""
    from app.services.google_ai import GoogleAIService

    service = GoogleAIService()
    paths = await service.edit_image(
        prompt=prompt,
        image_path=image_path,
        model=model,
        output_dir=settings.comfyui_output_dir,
    )
    if not paths:
        raise ComfyWorkflowError("編集画像が生成されませんでした")
    return {
        "prompt_id": prompt_id,
        "images": [
            {"filename": p.name, "subfolder": "", "type": "output"} for p in paths
        ],
        "prompt": prompt,
        "provider": "gemini-edit",
        "model": model,
        "reference_image": safe_name,
    }


async def run_google_ai_edit_workflow(
    prompt: str,
    reference_image: str,
    *,
    model: str | None = None,
    auto_enhance: bool = True,
    timeout: float = 180.0,
    poll_interval: float = 2.0,
) -> dict[str, Any]:
    """参照画像を元にカスタマイズする（ComfyUI ワークフロー経由）。"""
    import uuid

    safe_name = _resolve_output_filename(reference_image)
    image_path = settings.comfyui_output_dir / safe_name
    if not image_path.is_file():
        raise ComfyWorkflowError(f"参照画像が見つかりません: {safe_name}")

    client = ComfyUIClient()
    if not await client.health():
        raise ComfyWorkflowError(
            f"ComfyUI に接続できません ({settings.comfyui_base_url})"
        )

    pipeline = await run_prompt_pipeline(
        prompt, auto_enhance=auto_enhance, style="none", mode="edit"
    )
    workflow = build_google_ai_edit_workflow(
        pipeline.enhanced_prompt,
        safe_name,
        model=model,
        filename_prefix=f"google_ai_edit_{uuid.uuid4().hex[:8]}",
        user_prompt=pipeline.original_prompt,
        auto_enhance=auto_enhance,
        preprocessed=True,
    )

    try:
        prompt_id = await client.queue_prompt(workflow)
    except httpx.HTTPStatusError as exc:
        raise ComfyWorkflowError(exc.response.text) from exc
    except httpx.HTTPError as exc:
        raise ComfyWorkflowError(str(exc)) from exc

    edit_model = model or settings.google_edit_model
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        history = await client.get_history(prompt_id)
        entry = history.get(prompt_id)
        if not entry:
            await asyncio.sleep(poll_interval)
            continue

        status = entry.get("status", {})
        if status.get("completed"):
            images = _extract_output_images(entry)
            if images:
                return {
                    "prompt_id": prompt_id,
                    "images": images,
                    "prompt": pipeline.enhanced_prompt,
                    "provider": "gemini-edit",
                    "model": edit_model,
                    "reference_image": safe_name,
                    "original_prompt": pipeline.original_prompt,
                    "enhanced_prompt": pipeline.enhanced_prompt,
                    "workflow_nodes": workflow_node_chain(workflow),
                }
            direct = await _edit_image_direct(
                pipeline.enhanced_prompt,
                safe_name,
                image_path,
                model=edit_model,
                prompt_id=prompt_id,
            )
            direct.update(
                {
                    "original_prompt": pipeline.original_prompt,
                    "enhanced_prompt": pipeline.enhanced_prompt,
                    "workflow_nodes": workflow_node_chain(workflow),
                }
            )
            return direct

        messages = status.get("messages", [])
        for msg in messages:
            if isinstance(msg, (list, tuple)) and len(msg) >= 2 and msg[0] == "execution_error":
                raise ComfyWorkflowError(str(msg[1]))

        if status.get("status_str") == "error":
            raise ComfyWorkflowError(f"ComfyUI 実行エラー: {messages}")

        await asyncio.sleep(poll_interval)

    raise ComfyWorkflowTimeout(
        f"タイムアウト ({timeout}s)。prompt_id={prompt_id}"
    )
