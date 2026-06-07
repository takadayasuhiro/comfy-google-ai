from typing import Any, Literal

from pydantic import BaseModel, Field


class GenerateImageRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="画像生成プロンプト")
    model: str | None = Field(None, description="使用モデル（省略時は設定のデフォルト）")
    provider: Literal["imagen", "gemini"] = Field(
        "imagen",
        description="imagen=Imagen API, gemini=Gemini 画像出力モード",
    )
    number_of_images: int = Field(1, ge=1, le=4)
    aspect_ratio: str = Field("1:1", description="1:1, 3:4, 4:3, 9:16, 16:9")
    save_to_comfy: bool = Field(False, description="comfyui/output に保存（ComfyUI ノード用）")


class GenerateImageResponse(BaseModel):
    model: str
    provider: str
    images: list[str] = Field(description="保存された画像ファイルの相対パス")
    prompt: str


class WorkflowSubmitRequest(BaseModel):
    workflow: dict[str, Any] = Field(..., description="ComfyUI ワークフロー JSON")
    client_id: str | None = Field(None, description="WebSocket クライアント ID（任意）")


class WorkflowSubmitResponse(BaseModel):
    prompt_id: str
    comfyui_url: str
    message: str


class EnhancePromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    mode: Literal["generate", "edit"] = "generate"


class EnhancePromptResponse(BaseModel):
    original_prompt: str
    enhanced_prompt: str


class UiGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="ざっくりとした画像生成プロンプト")
    provider: Literal["imagen", "gemini"] = "imagen"
    model: str | None = None
    aspect_ratio: str = Field("1:1", description="1:1, 3:4, 4:3, 9:16, 16:9")
    reference_image: str | None = Field(
        None,
        description="カスタマイズ元画像のファイル名（comfyui/output 内）",
    )
    auto_enhance: bool = Field(True, description="Gemini でプロンプトを英語に拡張")
    style: str = Field("none", description="スタイルプリセット ID")
    enhanced_prompt: str | None = Field(
        None,
        description="プレビュー済みの拡張プロンプト（あれば再拡張をスキップ）",
    )


class EditImageRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    reference_image: str = Field(..., description="参照画像ファイル名")
    model: str | None = None


class GeneratedImageInfo(BaseModel):
    filename: str
    url: str


class UiGenerateResponse(BaseModel):
    prompt_id: str
    prompt: str
    provider: str
    model: str
    images: list[GeneratedImageInfo]
    mode: Literal["generate", "edit"] = "generate"
    reference_image: str | None = None
    original_prompt: str | None = None
    enhanced_prompt: str | None = None
    style: str | None = None
    workflow_nodes: list[str] = Field(default_factory=list)
