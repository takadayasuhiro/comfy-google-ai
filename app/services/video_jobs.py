import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Literal

from app.config import public_path, settings
from app.services.google_ai import GoogleAIService
from app.services.prompt_pipeline import run_prompt_pipeline

JobStatus = Literal["queued", "running", "completed", "failed"]

_jobs: dict[str, "VideoJob"] = {}


@dataclass
class VideoJob:
    job_id: str
    status: JobStatus = "queued"
    message: str = "キューに追加されました"
    model: str = ""
    prompt: str = ""
    original_prompt: str | None = None
    enhanced_prompt: str | None = None
    filename: str | None = None
    url: str | None = None
    thumb_filename: str | None = None
    thumb_url: str | None = None
    style: str | None = None
    error: str | None = None
    _task: asyncio.Task | None = field(default=None, repr=False)


def get_job(job_id: str) -> VideoJob | None:
    return _jobs.get(job_id)


async def start_video_job(
    *,
    prompt: str,
    model: str | None = None,
    duration_seconds: int = 6,
    aspect_ratio: str = "16:9",
    auto_enhance: bool = True,
    style: str = "none",
    enhanced_prompt: str | None = None,
) -> VideoJob:
    job_id = uuid.uuid4().hex
    resolved_model = model or settings.google_video_model
    job = VideoJob(
        job_id=job_id,
        model=resolved_model,
        original_prompt=prompt,
    )
    _jobs[job_id] = job
    job._task = asyncio.create_task(
        _run_job(
            job,
            prompt=prompt,
            model=resolved_model,
            duration_seconds=duration_seconds,
            aspect_ratio=aspect_ratio,
            auto_enhance=auto_enhance,
            style=style,
            enhanced_prompt=enhanced_prompt,
        )
    )
    return job


async def _run_job(
    job: VideoJob,
    *,
    prompt: str,
    model: str,
    duration_seconds: int,
    aspect_ratio: str,
    auto_enhance: bool,
    style: str,
    enhanced_prompt: str | None,
) -> None:
    job.status = "running"
    job.style = style
    try:
        job.message = "プロンプトを準備中…"
        pipeline = await run_prompt_pipeline(
            prompt,
            auto_enhance=auto_enhance,
            style=style,
            mode="video",
            cached_enhanced=enhanced_prompt,
        )
        job.enhanced_prompt = pipeline.enhanced_prompt
        final_prompt = pipeline.styled_prompt
        job.prompt = final_prompt
        job.message = "Veo API に接続中…"

        service = GoogleAIService()

        def on_progress(msg: str) -> None:
            job.message = msg

        saved = await service.generate_video(
            final_prompt,
            model=model,
            duration_seconds=duration_seconds,
            aspect_ratio=aspect_ratio,
            on_progress=on_progress,
        )
        job.filename = saved.video_path.name
        job.url = public_path(f"/comfy-output/{saved.video_path.name}")
        if saved.thumb_path:
            job.thumb_filename = saved.thumb_path.name
            job.thumb_url = public_path(f"/comfy-output/{saved.thumb_path.name}")
        job.status = "completed"
        job.message = "動画生成が完了しました"
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        job.message = str(exc)
