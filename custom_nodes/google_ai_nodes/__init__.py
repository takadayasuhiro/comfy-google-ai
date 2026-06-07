import json
import os
import urllib.error
import urllib.request

import numpy as np
import torch
from PIL import Image


class GoogleAIImageGenerate:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "forceInput": True}),
                "provider": (["imagen", "gemini"],),
                "model": ("STRING", {"default": "imagen-4.0-generate-001"}),
                "aspect_ratio": (["1:1", "3:4", "4:3", "9:16", "16:9"],),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "generate"
    CATEGORY = "google_ai"
    DESCRIPTION = "Google AI image generation via FastAPI bridge"

    def generate(self, prompt, provider, model, aspect_ratio):
        bridge_url = os.environ.get("GOOGLE_AI_BRIDGE_URL", "http://127.0.0.1:8000")
        payload = json.dumps(
            {
                "prompt": prompt,
                "provider": provider,
                "model": model,
                "aspect_ratio": aspect_ratio,
                "number_of_images": 1,
                "save_to_comfy": True,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{bridge_url}/generate/image",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        image_path = result["images"][0]
        if image_path.startswith("./"):
            image_path = image_path[2:]

        project_root = os.environ.get("GOOGLE_AI_PROJECT_ROOT")
        if not project_root:
            cwd = os.getcwd()
            project_root = os.path.dirname(cwd) if os.path.basename(cwd) == "comfyui" else cwd
        full_path = os.path.join(project_root, image_path)
        if not os.path.isfile(full_path):
            full_path = os.path.join(project_root, "comfyui", "output", os.path.basename(image_path))

        pil_image = Image.open(full_path).convert("RGB")
        tensor = torch.from_numpy(np.array(pil_image).astype("float32") / 255.0)
        tensor = tensor.unsqueeze(0)
        return (tensor,)


class GoogleAIImageEdit:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "reference_filename": ("STRING", {"default": "google_ai_00001_.png"}),
                "prompt": ("STRING", {"multiline": True, "forceInput": True}),
                "model": ("STRING", {"default": "gemini-2.5-flash-image"}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "edit"
    CATEGORY = "google_ai"
    DESCRIPTION = "参照画像を元に Google AI (Gemini) でカスタマイズ"

    def edit(self, reference_filename, prompt, model):
        bridge_url = os.environ.get("GOOGLE_AI_BRIDGE_URL", "http://127.0.0.1:8000")
        payload = json.dumps(
            {
                "prompt": prompt,
                "reference_image": reference_filename,
                "model": model,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{bridge_url}/generate/edit",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        image_info = result["images"][0]
        filename = image_info.get("filename") or image_info.get("url", "").split("/")[-1]

        project_root = os.environ.get("GOOGLE_AI_PROJECT_ROOT")
        if not project_root:
            cwd = os.getcwd()
            project_root = os.path.dirname(cwd) if os.path.basename(cwd) == "comfyui" else cwd
        full_path = os.path.join(project_root, "comfyui", "output", filename)
        if not os.path.isfile(full_path):
            full_path = os.path.join(project_root, "output", filename)

        pil_image = Image.open(full_path).convert("RGB")
        tensor = torch.from_numpy(np.array(pil_image).astype("float32") / 255.0)
        tensor = tensor.unsqueeze(0)
        return (tensor,)


STYLE_OPTIONS = [
    "none", "watercolor", "cyberpunk", "anime",
    "photorealistic", "oil_painting", "pixel_art", "minimal",
]
STYLE_SUFFIXES = {
    "none": "",
    "watercolor": ", watercolor painting style, soft brush strokes, paper texture, artistic",
    "cyberpunk": ", cyberpunk style, neon lights, futuristic city, high contrast, cinematic",
    "anime": ", anime illustration style, vibrant colors, clean linework, studio quality",
    "photorealistic": ", photorealistic, ultra detailed, professional photography, natural lighting",
    "oil_painting": ", oil painting style, rich textures, classical fine art, museum quality",
    "pixel_art": ", pixel art style, retro 16-bit game aesthetic, crisp pixels",
    "minimal": ", minimalist style, clean composition, simple shapes, negative space",
}


class GoogleAIPromptEnhance:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "user_prompt": ("STRING", {"multiline": True, "default": "夕焼けの柴犬"}),
                "auto_enhance": ("BOOLEAN", {"default": True}),
                "mode": (["generate", "edit"],),
            }
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "enhance"
    CATEGORY = "google_ai"
    DESCRIPTION = "Gemini で日本語プロンプトを英語に拡張"

    def enhance(self, user_prompt, auto_enhance, mode):
        if not auto_enhance:
            return (user_prompt,)
        bridge_url = os.environ.get("GOOGLE_AI_BRIDGE_URL", "http://127.0.0.1:8000")
        payload = json.dumps({"prompt": user_prompt, "mode": mode}).encode("utf-8")
        req = urllib.request.Request(
            f"{bridge_url}/api/enhance-prompt",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            return (result["enhanced_prompt"],)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"プロンプト拡張 API エラー ({exc.code}): {body}"
            ) from exc


class GoogleAIStyleApply:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"forceInput": True}),
                "style": (STYLE_OPTIONS,),
            }
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "apply"
    CATEGORY = "google_ai"
    DESCRIPTION = "スタイルプリセットをプロンプトに付与"

    def apply(self, prompt, style):
        suffix = STYLE_SUFFIXES.get(style, "")
        if not suffix:
            return (prompt,)
        return (f"{prompt.strip()}{suffix}",)


NODE_CLASS_MAPPINGS = {
    "GoogleAIPromptEnhance": GoogleAIPromptEnhance,
    "GoogleAIStyleApply": GoogleAIStyleApply,
    "GoogleAIImageGenerate": GoogleAIImageGenerate,
    "GoogleAIImageEdit": GoogleAIImageEdit,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GoogleAIPromptEnhance": "Google AI Prompt Enhance",
    "GoogleAIStyleApply": "Google AI Style Apply",
    "GoogleAIImageGenerate": "Google AI Image Generate",
    "GoogleAIImageEdit": "Google AI Image Edit",
}
