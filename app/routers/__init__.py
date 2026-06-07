from fastapi import APIRouter

from app.routers import generate, health, ui, workflow

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(ui.router, tags=["ui"])
api_router.include_router(generate.router, prefix="/generate", tags=["generate"])
api_router.include_router(workflow.router, prefix="/workflow", tags=["workflow"])
