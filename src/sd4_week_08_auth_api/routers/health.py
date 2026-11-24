from fastapi import APIRouter
from pydantic import BaseModel

from sd4_week_08_auth_api import __version__
from sd4_week_08_auth_api.config import settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str


class ReadyResponse(BaseModel):
    status: str


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=__version__,
        environment=settings.app_env,
    )


@router.get("/ready", response_model=ReadyResponse, summary="Readiness probe")
async def ready() -> ReadyResponse:
    return ReadyResponse(status="ready")
