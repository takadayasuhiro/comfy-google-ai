from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import public_path, settings
from app.routers import api_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    settings.comfyui_output_dir.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Comfy Google AI Bridge",
    description="ComfyUI ワークフローと Google AI API（Imagen/Gemini）を仲介する Web アプリ",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(api_router)
app.mount("/output", StaticFiles(directory=str(settings.output_dir)), name="output")


@app.get("/")
async def root():
    return RedirectResponse(url=public_path("/ui"))
