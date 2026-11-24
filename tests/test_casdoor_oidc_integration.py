import logging
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from authlib.jose import JsonWebKey, jwt
from authlib.jose.errors import JoseError
from fastapi.testclient import TestClient

from sd4_week_08_auth_api.config import settings
from sd4_week_08_auth_api.deps import (
    get_oauth_state_store,
    get_session_store,
    get_user_store,
)
from sd4_week_08_auth_api.main import app
from sd4_week_08_auth_api.services import casdoor_oidc
from sd4_week_08_auth_api.services.casdoor_oidc import OAuthStateStore
from sd4_week_08_auth_api.services.session_store import SessionStore
from sd4_week_08_auth_api.services.user_store import UserStore

ISSUER = "https://identity.example.test/casdoor"
CLIENT_ID = "sd4-week-08-auth-api-client"
CLIENT_SECRET = "test-client-secret"
REDIRECT_URI = "https://api.example.test/auth/casdoor/callback"


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    user_store = UserStore()
    session_store = SessionStore(ttl_seconds=3600)
    state_store = OAuthStateStore()
    monkeypatch.setattr(settings, "casdoor_client_id", CLIENT_ID)
    monkeypatch.setattr(settings, "casdoor_client_secret", CLIENT_SECRET)
    monkeypatch.setattr(settings, "casdoor_issuer", ISSUER)
    monkeypatch.setattr(settings, "casdoor_internal_issuer", "")
    monkeypatch.setattr(settings, "casdoor_redirect_uri", REDIRECT_URI)
    app.dependency_overrides[get_user_store] = lambda: user_store
    app.dependency_overrides[get_session_store] = lambda: session_store
    app.dependency_overrides[get_oauth_state_store] = lambda: state_store
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_full_casdoor_oidc_flow_with_signed_id_token(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_key = JsonWebKey.generate_key("RSA", 2048, is_private=True)
    key_id = "integration-test-key"
    private_jwk = private_key.as_dict(is_private=True)
    private_jwk["kid"] = key_id
    public_jwk = private_key.as_dict(is_private=False)
    public_jwk["kid"] = key_id
    now = datetime.now(UTC)
    id_token = jwt.encode(
        {"alg": "RS256", "kid": key_id},
        {
            "iss": ISSUER,
            "aud": CLIENT_ID,
            "sub": "casdoor-subject-123",
            "email": "integration-user@example.com",
            "preferred_username": "integration_user",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
        },
        private_jwk,
    ).decode()
    requests: list[httpx.Request] = []
    issuer_path = urlsplit(ISSUER).path

    def handle_request(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == f"{issuer_path}/api/login/oauth/access_token":
            return httpx.Response(200, json={"id_token": id_token})
        if request.url.path == f"{issuer_path}/.well-known/jwks":
            return httpx.Response(200, json={"keys": [public_jwk]})
        return httpx.Response(404)

    monkeypatch.setattr(
        casdoor_oidc,
        "_new_http_client",
        lambda: httpx.Client(transport=httpx.MockTransport(handle_request)),
    )
    login_response = client.get("/auth/casdoor/login", follow_redirects=False)
    state = parse_qs(urlsplit(login_response.headers["location"]).query)["state"][0]

    callback_response = client.get(
        "/auth/casdoor/callback",
        params={"code": "authorization-code", "state": state},
    )

    assert callback_response.status_code == 200
    access_token = callback_response.json()["access_token"]
    profile_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert profile_response.status_code == 200
    assert profile_response.json()["email"] == "integration-user@example.com"
    assert profile_response.json()["username"] == "integration_user"

    assert [request.url.path for request in requests] == [
        f"{issuer_path}/api/login/oauth/access_token",
        f"{issuer_path}/.well-known/jwks",
    ]
    token_request = parse_qs(requests[0].content.decode())
    assert token_request["grant_type"] == ["authorization_code"]
    assert token_request["code"] == ["authorization-code"]
    assert token_request["client_id"] == [CLIENT_ID]
    assert token_request["client_secret"] == [CLIENT_SECRET]
    assert token_request["redirect_uri"] == [REDIRECT_URI]


def test_exchange_code_logs_http_failure_without_credentials(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    authorization_code = "authorization-code-canary"

    def handle_request(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            request=request,
            text=f"Rejected {authorization_code} and {CLIENT_SECRET}",
        )

    monkeypatch.setattr(
        casdoor_oidc,
        "_new_http_client",
        lambda: httpx.Client(transport=httpx.MockTransport(handle_request)),
    )
    caplog.set_level(logging.ERROR, logger=casdoor_oidc.__name__)

    with pytest.raises(casdoor_oidc.OIDCAuthenticationError):
        casdoor_oidc.exchange_code(authorization_code)

    assert "HTTPStatusError" in caplog.text
    assert "401" in caplog.text
    assert authorization_code not in caplog.text
    assert CLIENT_SECRET not in caplog.text


def test_extract_user_info_logs_jose_failure_without_id_token(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    id_token = "id-token-canary"

    def handle_request(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, request=request, json={"keys": []})

    def fail_decode(*args: object, **kwargs: object) -> None:
        raise JoseError(f"Invalid ID token: {id_token}")

    monkeypatch.setattr(
        casdoor_oidc,
        "_new_http_client",
        lambda: httpx.Client(transport=httpx.MockTransport(handle_request)),
    )
    monkeypatch.setattr(casdoor_oidc.JsonWebKey, "import_key_set", lambda jwks: {})
    monkeypatch.setattr(casdoor_oidc.jwt, "decode", fail_decode)
    caplog.set_level(logging.ERROR, logger=casdoor_oidc.__name__)

    with pytest.raises(casdoor_oidc.OIDCAuthenticationError):
        casdoor_oidc.extract_user_info(id_token)

    assert "JoseError" in caplog.text
    assert "Invalid ID token" in caplog.text
    assert id_token not in caplog.text


def test_internal_issuer_routes_token_and_jwks_requests_to_casdoor(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ValidClaims(dict[str, str]):
        def validate(self) -> None:
            return None

    requests: list[httpx.Request] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/api/login/oauth/access_token":
            return httpx.Response(200, request=request, json={"id_token": "test-id-token"})
        if request.url.path == "/casdoor/.well-known/jwks":
            return httpx.Response(200, request=request, json={"keys": []})
        return httpx.Response(404, request=request)

    monkeypatch.setattr(
        settings,
        "casdoor_internal_issuer",
        "http://127.0.0.1:8000/casdoor",
    )
    monkeypatch.setattr(
        casdoor_oidc,
        "_new_http_client",
        lambda: httpx.Client(transport=httpx.MockTransport(handle_request)),
    )
    monkeypatch.setattr(casdoor_oidc.JsonWebKey, "import_key_set", lambda jwks: {})
    monkeypatch.setattr(
        casdoor_oidc.jwt,
        "decode",
        lambda *args, **kwargs: ValidClaims(
            sub="casdoor-subject-123",
            email="internal-user@example.com",
        ),
    )

    token_data = casdoor_oidc.exchange_code("authorization-code")
    user_info = casdoor_oidc.extract_user_info(token_data["id_token"])

    assert user_info.email == "internal-user@example.com"
    assert user_info.preferred_username == "internal-user"
    assert [str(request.url) for request in requests] == [
        "http://127.0.0.1:8000/api/login/oauth/access_token",
        "http://127.0.0.1:8000/casdoor/.well-known/jwks",
    ]
