from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from sd4_week_08_auth_api.deps import get_session_store, get_user_store
from sd4_week_08_auth_api.main import app
from sd4_week_08_auth_api.services.session_store import SessionStore
from sd4_week_08_auth_api.services.user_store import UserStore


@pytest.fixture()
def client() -> Iterator[TestClient]:
    user_store = UserStore()
    session_store = SessionStore(ttl_seconds=3600)
    app.dependency_overrides[get_user_store] = lambda: user_store
    app.dependency_overrides[get_session_store] = lambda: session_store
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _register(
    client: TestClient,
    email: str = "alice@example.com",
    username: str = "alice",
) -> None:
    response = client.post(
        "/auth/register",
        json={"email": email, "username": username, "password": "StrongPass123!"},
    )
    assert response.status_code == 201, response.text


def test_register_returns_public_user_without_password(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={"email": "alice@example.com", "username": "alice", "password": "StrongPass123!"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert body["username"] == "alice"
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    _register(client)
    response = client.post(
        "/auth/register",
        json={"email": "alice@example.com", "username": "alice2", "password": "StrongPass123!"},
    )
    assert response.status_code == 409


def test_register_rejects_duplicate_username(client: TestClient) -> None:
    _register(client)
    response = client.post(
        "/auth/register",
        json={"email": "alice2@example.com", "username": "alice", "password": "StrongPass123!"},
    )
    assert response.status_code == 409


def test_register_rejects_invalid_payload(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={"email": "not-an-email", "username": "alice", "password": "StrongPass123!"},
    )
    assert response.status_code == 422


def test_login_with_valid_credentials_returns_token(client: TestClient) -> None:
    _register(client)
    response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "StrongPass123!"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] > 0


def test_login_with_wrong_password_returns_401(client: TestClient) -> None:
    _register(client)
    response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "WrongPassword1!"},
    )
    assert response.status_code == 401


def test_login_with_unknown_email_returns_401(client: TestClient) -> None:
    response = client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "StrongPass123!"},
    )
    assert response.status_code == 401


def test_me_without_token_returns_401(client: TestClient) -> None:
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_returns_user_with_valid_token(client: TestClient) -> None:
    _register(client)
    login = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "StrongPass123!"},
    )
    token = login.json()["access_token"]
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"


def test_me_rejects_invalid_token(client: TestClient) -> None:
    response = client.get("/auth/me", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401


def test_logout_invalidates_token(client: TestClient) -> None:
    _register(client)
    login = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "StrongPass123!"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/auth/me", headers=headers).status_code == 200
    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_openapi_schema_includes_auth_endpoints() -> None:
    client = TestClient(app)
    schema = client.get("/openapi.json").json()
    for path in ("/auth/register", "/auth/login", "/auth/me", "/auth/logout"):
        assert path in schema["paths"], f"Missing {path} in OpenAPI schema"
