from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from sd4_week_08_auth_api.deps import get_session_store, get_user_store
from sd4_week_08_auth_api.main import app
from sd4_week_08_auth_api.models.user import UserCreate


@pytest.fixture()
def client() -> Iterator[TestClient]:
    get_session_store.cache_clear()
    get_user_store.cache_clear()
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        get_session_store.cache_clear()
        get_user_store.cache_clear()


def test_default_stores_persist_authentication_state(client: TestClient) -> None:
    registration = client.post(
        "/auth/register",
        json={
            "email": "default-store@example.com",
            "username": "default_store",
            "password": "StrongPass123!",
        },
    )
    assert registration.status_code == 201

    login = client.post(
        "/auth/login",
        json={"email": "default-store@example.com", "password": "StrongPass123!"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    current_user = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert current_user.status_code == 200
    assert current_user.json()["email"] == "default-store@example.com"


def test_me_rejects_session_for_missing_user(client: TestClient) -> None:
    token = get_session_store().create(uuid4())

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_inactive_user_cannot_login_or_access_me(client: TestClient) -> None:
    user = get_user_store().create(
        UserCreate(
            email="inactive@example.com",
            username="inactive",
            password="StrongPass123!",
        ),
        hashed_password="fake-hash",
    )
    user.is_active = False
    token = get_session_store().create(user.id)

    login = client.post(
        "/auth/login",
        json={"email": "inactive@example.com", "password": "StrongPass123!"},
    )
    current_user = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert login.status_code == 401
    assert current_user.status_code == 401


def test_logout_without_token_returns_401(client: TestClient) -> None:
    response = client.post("/auth/logout")

    assert response.status_code == 401
