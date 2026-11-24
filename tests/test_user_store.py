from uuid import uuid4

import pytest

from sd4_week_08_auth_api.models.user import UserCreate, UserInDB
from sd4_week_08_auth_api.services.user_store import DuplicateUserError, UserStore


@pytest.fixture()
def store() -> UserStore:
    return UserStore()


def _create(
    store: UserStore,
    email: str = "alice@example.com",
    username: str = "alice",
) -> UserInDB:
    return store.create(
        UserCreate(email=email, username=username, password="StrongPass123!"),
        hashed_password="fake-hash",
    )


def test_create_user_persists_and_returns_user(store: UserStore) -> None:
    user = _create(store)
    assert user.email == "alice@example.com"
    assert store.get_by_email("alice@example.com") is user
    assert store.get_by_username("alice") is user
    assert store.get_by_id(user.id) is user


def test_create_user_rejects_duplicate_email(store: UserStore) -> None:
    _create(store)
    with pytest.raises(DuplicateUserError):
        _create(store, username="alice2")


def test_create_user_rejects_duplicate_username(store: UserStore) -> None:
    _create(store)
    with pytest.raises(DuplicateUserError):
        _create(store, email="alice2@example.com")


def test_get_by_email_returns_none_when_missing(store: UserStore) -> None:
    assert store.get_by_email("missing@example.com") is None


def test_get_by_username_returns_none_when_missing(store: UserStore) -> None:
    assert store.get_by_username("missing") is None


def test_get_by_id_returns_none_when_missing(store: UserStore) -> None:
    assert store.get_by_id(uuid4()) is None
