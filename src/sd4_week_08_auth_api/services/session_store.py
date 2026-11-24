import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock
from uuid import UUID


@dataclass(frozen=True)
class Session:
    token: str
    user_id: UUID
    created_at: datetime
    expires_at: datetime


class SessionStore:
    def __init__(self, ttl_seconds: int) -> None:
        self._ttl = ttl_seconds
        self._sessions: dict[str, Session] = {}
        self._lock = Lock()

    @property
    def ttl_seconds(self) -> int:
        return self._ttl

    def create(self, user_id: UUID) -> str:
        token = secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        session = Session(
            token=token,
            user_id=user_id,
            created_at=now,
            expires_at=now + timedelta(seconds=self._ttl),
        )
        with self._lock:
            self._sessions[token] = session
        return token

    def get(self, token: str) -> Session | None:
        session = self._sessions.get(token)
        if session is None:
            return None
        if session.expires_at <= datetime.now(UTC):
            with self._lock:
                self._sessions.pop(token, None)
            return None
        return session

    def delete(self, token: str) -> bool:
        with self._lock:
            return self._sessions.pop(token, None) is not None
