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


@router.get("/login", summary="Start Casdoor single sign-on")
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
)
def callback(
    state_store: Annotated[OAuthStateStore, Depends(get_oauth_state_store)],
    user_store: Annotated[UserStore, Depends(get_user_store)],
    session_store: Annotated[SessionStore, Depends(get_session_store)],
    code: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    error: Annotated[str | None, Query()] = None,
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Casdoor authentication failed",
        ) from exc
    except casdoor_oidc.OIDCConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Casdoor OIDC is not configured",
        ) from exc
    except casdoor_oidc.OIDCProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Casdoor authentication service is unavailable",
        ) from exc

    user = _get_or_provision_user(user_info, user_store)
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
