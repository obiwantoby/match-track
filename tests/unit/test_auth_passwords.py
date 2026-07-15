"""Password hashing must work without passlib (bcrypt 5+ compatible)."""

import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "match_track_auth_unit")

from backend.auth import get_password_hash, verify_password  # noqa: E402


def test_hash_and_verify_roundtrip():
    hashed = get_password_hash("admin123")
    assert hashed.startswith("$2")
    assert verify_password("admin123", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_empty_password_rejected_on_verify():
    hashed = get_password_hash("something")
    assert verify_password("", hashed) is False
    assert verify_password("something", "") is False


def test_password_over_72_bytes_raises():
    long_pw = "x" * 80
    try:
        get_password_hash(long_pw)
        raised = False
    except ValueError:
        raised = True
    assert raised is True
