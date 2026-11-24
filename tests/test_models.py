import pytest
from pydantic import ValidationError

from sd4_week_08_auth_api.models.user import UserCreate, UserPublic


def test_user_create_accepts_valid_input() -> None:
    payload = UserCreate(
        email="alice@example.com",
        username="alice",
        password="StrongPass123!",
    )
    assert payload.email == "alice@example.com"


def test_user_create_rejects_invalid_email() -> None:
    with pytest.raises(ValidationError):
        UserCreate(email="not-an-email", username="alice", password="StrongPass123!")


def test_user_create_rejects_short_password() -> None:
    with pytest.raises(ValidationError):
        UserCreate(email="alice@example.com", username="alice", password="short")


def test_user_create_rejects_short_username() -> None:
    with pytest.raises(ValidationError):
        UserCreate(email="alice@example.com", username="a", password="StrongPass123!")


def test_user_create_rejects_username_with_invalid_chars() -> None:
    with pytest.raises(ValidationError):
        UserCreate(email="alice@example.com", username="alice!", password="StrongPass123!")


def test_user_public_never_exposes_password() -> None:
    fields = UserPublic.model_fields
    assert "password" not in fields
    assert "hashed_password" not in fields
