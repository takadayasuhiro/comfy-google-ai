from dataclasses import dataclass
from typing import Literal

from app.services.prompt_enhancer import PromptEnhancer
from app.services.style_presets import apply_style


@dataclass
class PromptPipelineResult:
    original_prompt: str
    enhanced_prompt: str
    styled_prompt: str
    auto_enhance: bool
    style: str


async def run_prompt_pipeline(
    user_prompt: str,
    *,
    auto_enhance: bool = True,
    style: str = "none",
    mode: Literal["generate", "edit", "video"] = "generate",
    cached_enhanced: str | None = None,
) -> PromptPipelineResult:
    user_prompt = user_prompt.strip()
    if cached_enhanced and cached_enhanced.strip():
        enhanced = cached_enhanced.strip()
    elif auto_enhance:
        enhancer = PromptEnhancer()
        enhance_mode = "edit" if mode == "edit" else "video" if mode == "video" else "generate"
        enhanced = await enhancer.enhance(user_prompt, mode=enhance_mode)
    else:
        enhanced = user_prompt

    styled = apply_style(enhanced, style) if mode in ("generate", "video") else enhanced
    return PromptPipelineResult(
        original_prompt=user_prompt,
        enhanced_prompt=enhanced,
        styled_prompt=styled,
        auto_enhance=auto_enhance,
        style=style,
    )
