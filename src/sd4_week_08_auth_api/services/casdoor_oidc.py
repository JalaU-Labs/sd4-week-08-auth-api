import secrets
import time
from dataclasses import dataclass
from threading import Lock
from typing import Any
from urllib.parse import urlencode, urlsplit

import httpx
from authlib.jose import JsonWebKey, jwt  # type: ignore[import-untyped]
from authlib.jose.errors import JoseError  # type: ignore[import-untyped]

from sd4_week_08_auth_api.config import settings

STATE_TTL_SECONDS = 300
HTTP_TIMEOUT_SECONDS = 10.0


class OIDCError(Exception):
    pass


class OIDCConfigurationError(OIDCError):
    pass


class OIDCAuthenticationError(OIDCError):
    pass


class OIDCProviderError(OIDCError):
    pass


@dataclass(frozen=True)
class CasdoorUserInfo:
    sub: str
    email: str
    preferred_username: str


class OAuthStateStore:
    def __init__(self, ttl_seconds: int = STATE_TTL_SECONDS) -> None:
        self._ttl_seconds = ttl_seconds
        self._states: dict[str, float] = {}
        self._lock = Lock()

    def create(self) -> str:
        state = secrets.token_urlsafe(32)
        now = time.monotonic()
        with self._lock:
            self._remove_expired(now)
            self._states[state] = now + self._ttl_seconds
        return state

    def consume(self, state: str) -> bool:
        now = time.monotonic()
        with self._lock:
            expires_at = self._states.pop(state, None)
            self._remove_expired(now)
        return expires_at is not None and expires_at > now

    def clear(self) -> None:
        with self._lock:
            self._states.clear()

    def _remove_expired(self, now: float) -> None:
        expired = [state for state, expiry in self._states.items() if expiry <= now]
        for state in expired:
            del self._states[state]


def _validate_configuration() -> tuple[str, str, str, str]:
    issuer = settings.casdoor_issuer.rstrip("/")
    client_id = settings.casdoor_client_id
    client_secret = settings.casdoor_client_secret
    redirect_uri = settings.casdoor_redirect_uri
    if not all((issuer, client_id, client_secret, redirect_uri)):
        raise OIDCConfigurationError("Casdoor OIDC is not configured")

    issuer_url = urlsplit(issuer)
    if issuer_url.scheme != "https" and not (
        issuer_url.scheme == "http" and issuer_url.hostname in {"localhost", "127.0.0.1"}
    ):
        raise OIDCConfigurationError("Casdoor issuer must use HTTPS")

    return issuer, client_id, client_secret, redirect_uri


def get_authorization_url(state: str) -> str:
    issuer, client_id, _, redirect_uri = _validate_configuration()
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid profile email",
            "state": state,
        }
    )
    return f"{issuer}/login/oauth/authorize?{query}"


def _new_http_client() -> httpx.Client:
    return httpx.Client(timeout=HTTP_TIMEOUT_SECONDS)


def exchange_code(code: str) -> dict[str, Any]:
    issuer, client_id, client_secret, redirect_uri = _validate_configuration()
    try:
        with _new_http_client() as client:
            response = client.post(
                f"{issuer}/api/login/oauth/access_token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                },
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code < 500:
            raise OIDCAuthenticationError("Casdoor rejected the authorization code") from exc
        raise OIDCProviderError("Casdoor token endpoint is unavailable") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise OIDCProviderError("Casdoor token endpoint is unavailable") from exc

    if not isinstance(payload, dict) or payload.get("error"):
        raise OIDCAuthenticationError("Casdoor rejected the authorization code")
    if not isinstance(payload.get("id_token"), str):
        raise OIDCAuthenticationError("Casdoor response did not contain an ID token")
    return payload


def extract_user_info(id_token: str) -> CasdoorUserInfo:
    issuer, client_id, _, _ = _validate_configuration()
    try:
        with _new_http_client() as client:
            response = client.get(f"{issuer}/.well-known/jwks")
            response.raise_for_status()
            jwks = response.json()
        if not isinstance(jwks, dict) or not isinstance(jwks.get("keys"), list):
            raise OIDCAuthenticationError("Casdoor returned an invalid signing key set")

        key_set = JsonWebKey.import_key_set(jwks)
        claims = jwt.decode(
            id_token,
            key_set,
            claims_options={
                "iss": {"essential": True, "value": issuer},
                "aud": {"essential": True, "value": client_id},
                "sub": {"essential": True},
                "email": {"essential": True},
                "preferred_username": {"essential": True},
            },
        )
        claims.validate()
    except OIDCError:
        raise
    except httpx.HTTPError as exc:
        raise OIDCProviderError("Casdoor signing keys are unavailable") from exc
    except (JoseError, ValueError, TypeError) as exc:
        raise OIDCAuthenticationError("Casdoor ID token is invalid") from exc

    subject = claims.get("sub")
    email = claims.get("email")
    username = claims.get("preferred_username")
    if not all(isinstance(value, str) and value for value in (subject, email, username)):
        raise OIDCAuthenticationError("Casdoor ID token is missing required user claims")

    return CasdoorUserInfo(sub=subject, email=email, preferred_username=username)
