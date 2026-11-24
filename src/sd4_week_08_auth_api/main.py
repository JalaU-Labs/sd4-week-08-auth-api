from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from sd4_week_08_auth_api import __version__
from sd4_week_08_auth_api.routers import health


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield


app = FastAPI(
    title="SD4 Week 08 Auth API",
    version=__version__,
    description=(
        "Public authentication API for Week 08 Lab of Software Development 4 "
        "at Jala University. Provides user registration, login and profile "
        "endpoints with in-memory session storage and Casdoor IAM integration."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={"name": "Diego Alejandro Botina"},
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
    lifespan=lifespan,
)

app.include_router(health.router)
