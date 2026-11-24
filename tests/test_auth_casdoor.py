from collections.abc import Iterator
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from sd4_week_08_auth_api.config import settings
from sd4_week_08_auth_api.deps import (
    get_oauth_state_store,
    get_session_store,
    get_user_store,
)
from sd4_week_08_auth_api.main import app
from sd4_week_08_auth_api.services import casdoor_oidc
from sd4_week_08_auth_api.services.casdoor_oidc import CasdoorUserInfo, OAuthStateStore
from sd4_week_08_auth_api.services.session_store import SessionStore
from sd4_week_08_auth_api.services.user_store import UserStore

ISSUER = "https://identity.example.test/casdoor"
CLIENT_ID = "sd4-week-08-auth-api-client"
REDIRECT_URI = "https://api.example.test/auth/casdoor/callback"


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    user_store = UserStore()
    session_store = SessionStore(ttl_seconds=3600)
    state_store = OAuthStateStore()
    monkeypatch.setattr(settings, "casdoor_client_id", CLIENT_ID)
    monkeypatch.setattr(settings, "casdoor_client_secret", "test-client-secret")
    monkeypatch.setattr(settings, "casdoor_issuer", ISSUER)
    monkeypatch.setattr(settings, "casdoor_redirect_uri", REDIRECT_URI)
    app.dependency_overrides[get_user_store] = lambda: user_store
    app.dependency_overrides[get_session_store] = lambda: session_store
    app.dependency_overrides[get_oauth_state_store] = lambda: state_store
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_login_redirects_to_casdoor_with_state(client: TestClient) -> None:
    response = client.get("/auth/casdoor/login", follow_redirects=False)

    assert response.status_code == 302
    location = urlsplit(response.headers["location"])
    query = parse_qs(location.query)
    assert f"{location.scheme}://{location.netloc}{location.path}" == (
        f"{ISSUER}/login/oauth/authorize"
    )
    assert query["client_id"] == [CLIENT_ID]
    assert query["redirect_uri"] == [REDIRECT_URI]
    assert query["response_type"] == ["code"]
    assert query["scope"] == ["openid profile email"]
    assert query["state"]


def test_callback_provisions_user_and_issues_local_bearer_token(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(casdoor_oidc, "exchange_code", lambda code: {"id_token": "mock-id-token"})
    monkeypatch.setattr(
        casdoor_oidc,
        "extract_user_info",
        lambda token: CasdoorUserInfo(
            sub="casdoor-user-123",
            email="sso-user@example.com",
            preferred_username="sso_user",
        ),
    )
    login = client.get("/auth/casdoor/login", follow_redirects=False)
    state = parse_qs(urlsplit(login.headers["location"]).query)["state"][0]

    response = client.get(
        "/auth/casdoor/callback",
        params={"code": "valid-code", "state": state},
    )

    assert response.status_code == 200
    token = response.json()["access_token"]
    assert response.json()["token_type"] == "bearer"
    assert response.json()["expires_in"] == 3600
    current_user = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert current_user.status_code == 200
    assert current_user.json()["email"] == "sso-user@example.com"
    assert current_user.json()["username"] == "sso_user"


def test_callback_rejects_invalid_state(client: TestClient) -> None:
    response = client.get(
        "/auth/casdoor/callback",
        params={"code": "valid-code", "state": "not-issued-by-this-api"},
    )

    assert response.status_code == 401


def test_callback_rejects_casdoor_error(client: TestClient) -> None:
    response = client.get(
        "/auth/casdoor/callback",
        params={"error": "access_denied", "state": "unused-state"},
    )

    assert response.status_code == 401


def test_callback_state_can_only_be_used_once(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(casdoor_oidc, "exchange_code", lambda code: {"id_token": "mock-id-token"})
    monkeypatch.setattr(
        casdoor_oidc,
        "extract_user_info",
        lambda token: CasdoorUserInfo(
            sub="casdoor-user-123",
            email="sso-user@example.com",
            preferred_username="sso_user",
        ),
    )
    login = client.get("/auth/casdoor/login", follow_redirects=False)
    state = parse_qs(urlsplit(login.headers["location"]).query)["state"][0]
    callback = {"code": "valid-code", "state": state}

    assert client.get("/auth/casdoor/callback", params=callback).status_code == 200
    assert client.get("/auth/casdoor/callback", params=callback).status_code == 401
