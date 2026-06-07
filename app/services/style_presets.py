STYLE_PRESETS: dict[str, dict[str, str]] = {
    "none": {
        "label": "なし（指定しない）",
        "suffix": "",
    },
    "watercolor": {
        "label": "水彩画風",
        "suffix": ", watercolor painting style, soft brush strokes, paper texture, artistic",
    },
    "cyberpunk": {
        "label": "サイバーパンク風",
        "suffix": ", cyberpunk style, neon lights, futuristic city, high contrast, cinematic",
    },
    "anime": {
        "label": "アニメ風",
        "suffix": ", anime illustration style, vibrant colors, clean linework, studio quality",
    },
    "photorealistic": {
        "label": "フォトリアル",
        "suffix": ", photorealistic, ultra detailed, professional photography, natural lighting",
    },
    "oil_painting": {
        "label": "油絵風",
        "suffix": ", oil painting style, rich textures, classical fine art, museum quality",
    },
    "pixel_art": {
        "label": "ピクセルアート",
        "suffix": ", pixel art style, retro 16-bit game aesthetic, crisp pixels",
    },
    "minimal": {
        "label": "ミニマル",
        "suffix": ", minimalist style, clean composition, simple shapes, negative space",
    },
}


def apply_style(prompt: str, style: str) -> str:
    preset = STYLE_PRESETS.get(style, STYLE_PRESETS["none"])
    suffix = preset["suffix"]
    if not suffix:
        return prompt.strip()
    return f"{prompt.strip()}{suffix}"


def list_styles() -> list[dict[str, str]]:
    return [
        {"id": k, "label": v["label"], "suffix": v["suffix"]}
        for k, v in STYLE_PRESETS.items()
    ]
