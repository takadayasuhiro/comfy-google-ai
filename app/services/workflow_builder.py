from typing import Any

from app.config import settings

WORKFLOW_NODE_LABELS = {
    "GoogleAIPromptEnhance": "AIプロンプター",
    "GoogleAIStyleApply": "スタイル適用",
    "GoogleAIImageGenerate": "画像生成",
    "GoogleAIImageEdit": "画像カスタマイズ",
    "SaveImage": "保存",
}


def build_google_ai_workflow(
    prompt: str,
    *,
    provider: str = "imagen",
    model: str | None = None,
    aspect_ratio: str = "1:1",
    filename_prefix: str = "google_ai",
    user_prompt: str | None = None,
    auto_enhance: bool = True,
    style: str = "none",
    preprocessed: bool = False,
) -> dict[str, Any]:
    """マルチノードワークフロー: プロンプト拡張 → スタイル → 画像生成 → 保存。"""
    # preprocessed=True: FastAPI 側で拡張済み。ノードは HTTP 再呼び出しせずパススルー。
    final_prompt = prompt
    return {
        "1": {
            "class_type": "GoogleAIPromptEnhance",
            "inputs": {
                "user_prompt": final_prompt,
                "auto_enhance": False if preprocessed else auto_enhance,
                "mode": "generate",
            },
        },
        "2": {
            "class_type": "GoogleAIStyleApply",
            "inputs": {
                "prompt": ["1", 0],
                "style": "none" if preprocessed else style,
            },
        },
        "3": {
            "class_type": "GoogleAIImageGenerate",
            "inputs": {
                "prompt": ["2", 0],
                "provider": provider,
                "model": model or settings.google_image_model,
                "aspect_ratio": aspect_ratio,
            },
        },
        "4": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": filename_prefix,
                "images": ["3", 0],
            },
        },
    }


def build_google_ai_edit_workflow(
    prompt: str,
    reference_filename: str,
    *,
    model: str | None = None,
    filename_prefix: str = "google_ai_edit",
    user_prompt: str | None = None,
    auto_enhance: bool = True,
    preprocessed: bool = False,
) -> dict[str, Any]:
    """マルチノードワークフロー: プロンプト拡張 → 画像カスタマイズ → 保存。"""
    final_prompt = prompt
    return {
        "1": {
            "class_type": "GoogleAIPromptEnhance",
            "inputs": {
                "user_prompt": final_prompt,
                "auto_enhance": False if preprocessed else auto_enhance,
                "mode": "edit",
            },
        },
        "2": {
            "class_type": "GoogleAIImageEdit",
            "inputs": {
                "reference_filename": reference_filename,
                "prompt": ["1", 0],
                "model": model or settings.google_edit_model,
            },
        },
        "3": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": filename_prefix,
                "images": ["2", 0],
            },
        },
    }


def workflow_node_chain(workflow: dict[str, Any]) -> list[str]:
    """ワークフロー内のノード表示名リストを返す。"""
    chain: list[str] = []
    for node in workflow.values():
        class_type = node.get("class_type", "")
        chain.append(WORKFLOW_NODE_LABELS.get(class_type, class_type))
    return chain
