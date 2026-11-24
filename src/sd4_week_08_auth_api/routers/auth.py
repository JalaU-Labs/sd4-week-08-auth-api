from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials

from sd4_week_08_auth_api.deps import (
    bearer_scheme,
    get_current_user,
    get_session_store,
    get_user_store,
)
from sd4_week_08_auth_api.models.auth import LoginRequest, TokenResponse
from sd4_week_08_auth_api.models.user import UserCreate, UserInDB, UserPublic
from sd4_week_08_auth_api.services.security import hash_password, verify_password
from sd4_week_08_auth_api.services.session_store import SessionStore
from sd4_week_08_auth_api.services.user_store import DuplicateUserError, UserStore

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description=(
        "Create a local account with an email address, username, and password. "
        "The response contains the public user profile and never includes the password."
    ),
    response_description="The account was created; sensitive password data is omitted.",
    responses={409: {"description": "The email address or username is already registered."}},
)
async def register(
    payload: UserCreate,
    user_store: Annotated[UserStore, Depends(get_user_store)],
) -> UserPublic:
    try:
        user = user_store.create(payload, hashed_password=hash_password(payload.password))
    except DuplicateUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{exc.field} already registered",
        ) from exc
    return UserPublic.model_validate(user, from_attributes=True)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and obtain a session token",
    description=(
        "Authenticate a local account using its email address and password. The returned "
        "opaque access token is a local session token, not a Casdoor token. Send it as "
        "`Authorization: Bearer <access_token>` to protected endpoints."
    ),
    response_description="Credentials were accepted and a local Bearer token was issued.",
    responses={
        401: {"description": "The email or password is invalid, or the account is inactive."}
    },
)
async def login(
    payload: LoginRequest,
    user_store: Annotated[UserStore, Depends(get_user_store)],
    session_store: Annotated[SessionStore, Depends(get_session_store)],
) -> TokenResponse:
    user = user_store.get_by_email(payload.email)
    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = session_store.create(user.id)
    return TokenResponse(access_token=token, expires_in=session_store.ttl_seconds)


@router.get(
    "/me",
    response_model=UserPublic,
    summary="Return the authenticated user",
    description=(
        "Return the public profile associated with the current local session. Provide "
        "the access token obtained from `/auth/login` or `/auth/casdoor/callback`."
    ),
    response_description="The authenticated user's public profile.",
    responses={401: {"description": "The Bearer token is missing, invalid, expired, or inactive."}},
)
async def me(current_user: Annotated[UserInDB, Depends(get_current_user)]) -> UserPublic:
    return UserPublic.model_validate(current_user, from_attributes=True)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Invalidate the current session token",
    description=(
        "Invalidate the current local session. A successful request has no response body; "
        "the token cannot be used for subsequent authenticated requests."
    ),
    response_description="The session was invalidated.",
    responses={401: {"description": "The Authorization header is missing or invalid."}},
)
async def logout(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session_store: Annotated[SessionStore, Depends(get_session_store)],
) -> Response:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    session_store.delete(credentials.credentials)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
