from uuid import uuid4

from sd4_week_08_auth_api.services.session_store import SessionStore


def test_create_session_returns_token_and_persists() -> None:
    store = SessionStore(ttl_seconds=3600)
    user_id = uuid4()
    token = store.create(user_id)
    session = store.get(token)
    assert session is not None
    assert session.user_id == user_id


def test_ttl_seconds_property_exposes_configured_value() -> None:
    store = SessionStore(ttl_seconds=1234)
    assert store.ttl_seconds == 1234


def test_get_returns_none_for_unknown_token() -> None:
    store = SessionStore(ttl_seconds=3600)
    assert store.get("unknown-token") is None


def test_delete_removes_session_and_returns_true() -> None:
    store = SessionStore(ttl_seconds=3600)
    token = store.create(uuid4())
    assert store.delete(token) is True
    assert store.get(token) is None


def test_delete_returns_false_for_unknown_token() -> None:
    store = SessionStore(ttl_seconds=3600)
    assert store.delete("unknown-token") is False


def test_get_returns_none_for_expired_session() -> None:
    store = SessionStore(ttl_seconds=-1)
    token = store.create(uuid4())
    assert store.get(token) is None
