import asyncio
from typing import Literal

from google import genai

from app.config import settings

_MAX_RETRIES = 3
_RETRY_DELAY_SEC = 1.5


def _is_transient(exc: Exception) -> bool:
    msg = str(exc).upper()
    return "503" in msg or "UNAVAILABLE" in msg or "429" in msg or "RESOURCE_EXHAUSTED" in msg

_ENHANCE_GENERATE = """You are an expert image prompt engineer for Imagen and Gemini image models.
Given a short user prompt (often in Japanese), produce ONE vivid English prompt for image generation.

Rules:
- Output ONLY the final English prompt. No quotes, labels, or explanation.
- Add concrete visual details: subject, action, environment, lighting, mood, composition.
- Keep it concise but cinematic (1-3 sentences, under 120 words).
- If the input is already detailed English, refine it slightly rather than rewriting entirely.
"""

_ENHANCE_EDIT = """You are an expert at writing image EDIT instructions for Gemini image editing.
The user already has a reference image and wants to CUSTOMIZE it — NOT generate a completely new unrelated image.

Rules:
- Output ONLY the edit instruction in English. No quotes, labels, or explanation.
- MUST begin with preserving the reference subject: "Keep the same person/subject from the reference image"
- Preserve: face, gender, age, hairstyle, clothing, and overall identity of the main subject in the reference
- Apply ONLY the scene/action/background changes the user requested
- If the user mentions a number of people (e.g. "5人"), the reference subject counts as ONE of them — add others around them, do NOT replace the subject with different people
- Do NOT write a full scene description that ignores the reference image
- Keep under 100 words
"""


class PromptEnhancer:
    def __init__(self) -> None:
        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY が未設定です")
        self._client = genai.Client(api_key=settings.google_api_key)

    async def enhance(
        self,
        user_prompt: str,
        *,
        mode: Literal["generate", "edit"] = "generate",
    ) -> str:
        system = _ENHANCE_EDIT if mode == "edit" else _ENHANCE_GENERATE
        contents = f"{system}\n\nUser instruction:\n{user_prompt}"
        last_exc: Exception | None = None

        for attempt in range(_MAX_RETRIES):
            try:
                response = await self._client.aio.models.generate_content(
                    model=settings.google_prompt_model,
                    contents=contents,
                )
                text = (response.text or "").strip()
                if not text:
                    raise ValueError("プロンプト拡張結果が空です")
                return text
            except Exception as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES - 1 and _is_transient(exc):
                    await asyncio.sleep(_RETRY_DELAY_SEC * (attempt + 1))
                    continue
                raise

        if last_exc:
            raise last_exc
        raise ValueError("プロンプト拡張に失敗しました")
