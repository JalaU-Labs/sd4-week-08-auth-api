import logging
import re
import secrets
from hashlib import sha256
from typing import Annotated
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError

from sd4_week_08_auth_api.deps import (
    get_oauth_state_store,
    get_session_store,
    get_user_store,
)
from sd4_week_08_auth_api.models.auth import TokenResponse
from sd4_week_08_auth_api.models.user import UserCreate, UserInDB
from sd4_week_08_auth_api.services import casdoor_oidc
from sd4_week_08_auth_api.services.casdoor_oidc import (
    CasdoorUserInfo,
    OAuthStateStore,
)
from sd4_week_08_auth_api.services.security import hash_password
from sd4_week_08_auth_api.services.session_store import SessionStore
from sd4_week_08_auth_api.services.user_store import DuplicateUserError, UserStore

router = APIRouter(prefix="/auth/casdoor", tags=["Casdoor SSO"])
logger = logging.getLogger(__name__)


@router.get(
    "/login",
    status_code=status.HTTP_302_FOUND,
    summary="Start Casdoor single sign-on",
    description=(
        "Begin the OIDC Authorization Code flow. The API creates a one-time state value "
        "and redirects the browser to the configured Casdoor issuer. Start SSO here rather "
        "than opening Casdoor's `/casdoor/login` page directly."
    ),
    response_description="Redirects the browser to Casdoor's authorization page.",
    responses={503: {"description": "Casdoor OIDC client settings are incomplete or invalid."}},
)
def login(
    state_store: Annotated[OAuthStateStore, Depends(get_oauth_state_store)],
) -> RedirectResponse:
    state = state_store.create()
    try:
        authorization_url = casdoor_oidc.get_authorization_url(state)
    except casdoor_oidc.OIDCConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return RedirectResponse(authorization_url, status_code=status.HTTP_302_FOUND)


@router.get(
    "/callback",
    response_model=TokenResponse,
    summary="Complete Casdoor single sign-on",
    description=(
        "Validate the one-time OAuth state, exchange the authorization code with Casdoor, "
        "verify the ID token, provision the user if needed, and issue a local Bearer token. "
        "Casdoor returns the browser to this endpoint."
    ),
    response_description="Casdoor authentication succeeded and a local Bearer token was issued.",
    responses={
        401: {
            "description": (
                "Authorization was denied, state is invalid, or Casdoor authentication failed."
            )
        },
        409: {"description": "The Casdoor user could not be provisioned."},
        502: {"description": "Casdoor's token or signing-key endpoint is unavailable."},
        503: {"description": "Casdoor OIDC client settings are incomplete or invalid."},
    },
)
def callback(
    state_store: Annotated[OAuthStateStore, Depends(get_oauth_state_store)],
    user_store: Annotated[UserStore, Depends(get_user_store)],
    session_store: Annotated[SessionStore, Depends(get_session_store)],
    code: Annotated[
        str | None,
        Query(description="Authorization code supplied by Casdoor after sign-in."),
    ] = None,
    state: Annotated[
        str | None,
        Query(description="One-time state value created by the API when SSO began."),
    ] = None,
    error: Annotated[
        str | None,
        Query(description="OAuth error returned by Casdoor if authorization was denied."),
    ] = None,
) -> TokenResponse:
    if state is not None:
        state = unquote(state)
    if error is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Casdoor authorization was denied",
        )
    if not code or not state or not state_store.consume(state):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Casdoor state",
        )

    try:
        token_data = casdoor_oidc.exchange_code(code)
        id_token = token_data.get("id_token")
        if not isinstance(id_token, str):
            raise casdoor_oidc.OIDCAuthenticationError(
                "Casdoor response did not contain an ID token"
            )
        user_info = casdoor_oidc.extract_user_info(id_token)
    except casdoor_oidc.OIDCAuthenticationError as exc:
        logger.error("Casdoor OIDC authentication failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Casdoor authentication failed",
        ) from exc
    except casdoor_oidc.OIDCConfigurationError as exc:
        logger.error("Casdoor OIDC configuration error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Casdoor OIDC is not configured",
        ) from exc
    except casdoor_oidc.OIDCProviderError as exc:
        logger.error("Casdoor OIDC provider error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Casdoor authentication service is unavailable",
        ) from exc

    try:
        user = _get_or_provision_user(user_info, user_store)
    except HTTPException as exc:
        logger.error(
            "Casdoor user provisioning failed (HTTP %s): %s",
            exc.status_code,
            exc.detail,
        )
        raise
    token = session_store.create(user.id)
    return TokenResponse(access_token=token, expires_in=session_store.ttl_seconds)


def _get_or_provision_user(user_info: CasdoorUserInfo, user_store: UserStore) -> UserInDB:
    existing_user = user_store.get_by_email(user_info.email)
    if existing_user is not None:
        if not existing_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User is inactive",
            )
        return existing_user

    username = _available_username(user_info, user_store)
    try:
        payload = UserCreate(
            email=user_info.email,
            username=username,
            password=secrets.token_urlsafe(32),
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Casdoor returned invalid user claims",
        ) from exc

    try:
        return user_store.create(payload, hashed_password=hash_password(payload.password))
    except DuplicateUserError as exc:
        existing_user = user_store.get_by_email(payload.email)
        if existing_user is not None and existing_user.is_active:
            return existing_user
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to provision Casdoor user",
        ) from exc


def _available_username(user_info: CasdoorUserInfo, user_store: UserStore) -> str:
    username = re.sub(r"[^a-zA-Z0-9_]", "_", user_info.preferred_username)[:32]
    if len(username) < 3:
        username = f"sso_{sha256(user_info.sub.encode()).hexdigest()[:8]}"

    existing_user = user_store.get_by_username(username)
    if existing_user is None or existing_user.email == user_info.email:
        return username

    suffix = sha256(user_info.sub.encode()).hexdigest()[:8]
    return f"{username[:23]}_{suffix}"
