from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from sd4_week_08_auth_api import __version__
from sd4_week_08_auth_api.routers import auth, auth_casdoor, health


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield


app = FastAPI(
    title="SD4 Week 08 Auth API",
    version=__version__,
    description=(
        "## Overview\n\n"
        "A public authentication API for local user registration, login, profile and "
        "session management, with Casdoor OIDC single sign-on and just-in-time user "
        "provisioning. User and session data are stored in memory.\n\n"
        "## Obtain an access token\n\n"
        "- Use `POST /auth/login` with a registered email and password, or\n"
        "- Open `GET /auth/casdoor/login` to sign in through Casdoor.\n\n"
        "Both flows issue a local Bearer token for protected API operations.\n\n"
        "## Authorize requests in Swagger UI\n\n"
        "Click **Authorize** and paste the access token. The security scheme adds "
        "the `Bearer` prefix; do not include it in the value. Then try `GET /auth/me`.\n\n"
        "See the [full project documentation](https://github.com/JalaU-Labs/"
        "sd4-week-08-auth-api#readme)."
    ),
    openapi_tags=[
        {"name": "health", "description": "Liveness and readiness probes."},
        {"name": "auth", "description": "Local user registration and session management."},
        {"name": "Casdoor SSO", "description": "Single sign-on using Casdoor OIDC."},
    ],
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={"name": "Diego Alejandro Botina"},
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(auth_casdoor.router)
