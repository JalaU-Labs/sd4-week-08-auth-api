from fastapi import APIRouter
from pydantic import BaseModel, Field

from sd4_week_08_auth_api import __version__
from sd4_week_08_auth_api.config import settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str = Field(description="Health status.", examples=["ok"])
    version: str = Field(description="Running application version.", examples=["0.1.5"])
    environment: str = Field(
        description="Configured deployment environment.",
        examples=["production"],
    )


class ReadyResponse(BaseModel):
    status: str = Field(description="Readiness status.", examples=["ready"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check service health",
    description=(
        "Reports whether the API process is responding and includes the running "
        "application version and configured environment. This endpoint does not "
        "require authentication."
    ),
    response_description="The API is healthy and returns its version and environment.",
)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=__version__,
        environment=settings.app_env,
    )


@router.get(
    "/ready",
    response_model=ReadyResponse,
    summary="Check service readiness",
    description=(
        "Reports whether the API is ready to accept requests. This endpoint does "
        "not require authentication."
    ),
    response_description="The API is ready to accept requests.",
)
async def ready() -> ReadyResponse:
    return ReadyResponse(status="ready")
