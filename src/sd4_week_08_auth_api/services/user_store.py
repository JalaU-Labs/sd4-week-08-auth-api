from datetime import UTC, datetime
from threading import Lock
from uuid import UUID, uuid4

from sd4_week_08_auth_api.models.user import UserCreate, UserInDB


class DuplicateUserError(Exception):
    def __init__(self, field: str, value: str) -> None:
        super().__init__(f"User with {field}={value!r} already exists")
        self.field = field
        self.value = value


class UserStore:
    def __init__(self) -> None:
        self._users: dict[UUID, UserInDB] = {}
        self._by_email: dict[str, UUID] = {}
        self._by_username: dict[str, UUID] = {}
        self._lock = Lock()

    def create(self, payload: UserCreate, hashed_password: str) -> UserInDB:
        with self._lock:
            if payload.email in self._by_email:
                raise DuplicateUserError("email", payload.email)
            if payload.username in self._by_username:
                raise DuplicateUserError("username", payload.username)
            user = UserInDB(
                id=uuid4(),
                email=payload.email,
                username=payload.username,
                hashed_password=hashed_password,
                is_active=True,
                created_at=datetime.now(UTC),
            )
            self._users[user.id] = user
            self._by_email[user.email] = user.id
            self._by_username[user.username] = user.id
            return user

    def get_by_email(self, email: str) -> UserInDB | None:
        user_id = self._by_email.get(email)
        return self._users.get(user_id) if user_id else None

    def get_by_username(self, username: str) -> UserInDB | None:
        user_id = self._by_username.get(username)
        return self._users.get(user_id) if user_id else None

    def get_by_id(self, user_id: UUID) -> UserInDB | None:
        return self._users.get(user_id)
