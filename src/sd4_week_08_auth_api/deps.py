from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from sd4_week_08_auth_api.config import settings
from sd4_week_08_auth_api.models.user import UserInDB
from sd4_week_08_auth_api.services.session_store import SessionStore
from sd4_week_08_auth_api.services.user_store import UserStore

bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def get_user_store() -> UserStore:
    return UserStore()


@lru_cache
def get_session_store() -> SessionStore:
    return SessionStore(ttl_seconds=settings.session_ttl_seconds)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session_store: Annotated[SessionStore, Depends(get_session_store)],
    user_store: Annotated[UserStore, Depends(get_user_store)],
) -> UserInDB:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    session = session_store.get(credentials.credentials)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = user_store.get_by_id(session.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is no longer active",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
