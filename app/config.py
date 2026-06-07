from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    google_api_key: str = ""
    google_image_model: str = "imagen-4.0-generate-001"
    google_edit_model: str = "gemini-2.5-flash-image"
    google_prompt_model: str = "gemini-2.5-flash"

    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_base_path: str = ""

    edit_backend: str = "google"

    comfyui_host: str = "127.0.0.1"
    comfyui_port: int = 8188

    output_dir: Path = Path("./output")
    comfyui_output_dir: Path = Path("./comfyui/output")

    @property
    def comfyui_base_url(self) -> str:
        return f"http://{self.comfyui_host}:{self.comfyui_port}"


settings = Settings()


def public_path(path: str) -> str:
    """nginx サブパス配下でも正しい公開 URL を返す（例: /gazou/comfy-output/xxx.png）。"""
    normalized = path if path.startswith("/") else f"/{path}"
    base = settings.app_base_path.rstrip("/")
    if not base:
        return normalized
    return f"{base}{normalized}"


def base_href() -> str:
    """HTML <base href> 用。末尾スラッシュ付き。"""
    base = settings.app_base_path.rstrip("/")
    return f"{base}/" if base else "/"
