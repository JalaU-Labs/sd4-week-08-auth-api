import pytest

from sd4_week_08_auth_api.services.security import hash_password, verify_password


def test_hash_password_returns_different_hashes_for_same_input() -> None:
    password = "correct-horse-battery-staple"
    hash1 = hash_password(password)
    hash2 = hash_password(password)
    assert hash1 != hash2
    assert hash1.startswith(("$2a$", "$2b$"))


def test_verify_password_accepts_correct_password() -> None:
    password = "correct-horse-battery-staple"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True


def test_verify_password_rejects_wrong_password() -> None:
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password("wrong-password", hashed) is False


def test_hash_password_rejects_empty_string() -> None:
    with pytest.raises(ValueError):
        hash_password("")


def test_verify_password_rejects_malformed_hash() -> None:
    assert verify_password("anything", "not-a-bcrypt-hash") is False


def test_verify_password_rejects_empty_inputs() -> None:
    assert verify_password("", "somehash") is False
    assert verify_password("password", "") is False
