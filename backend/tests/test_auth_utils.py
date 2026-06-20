"""Unit tests for ``app.auth.utils``.

Tests password hashing/verification and JWT token sign/decode operations
against the existing production code (no database needed).
"""

from datetime import datetime, timedelta, timezone

from jose import jwt

from app.auth.utils import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.config import settings

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


def test_hash_password_returns_bcrypt_hash():
    """Hashing any password returns a bcrypt hash string."""
    hashed = hash_password("my-secret")
    assert isinstance(hashed, str)
    assert hashed.startswith("$2")  # $2a$, $2b$, or $2y$


def test_hash_password_salting_produces_different_hashes():
    """Hashing the same password twice yields different hashes (automatic salt)."""
    pwd = "same-password"
    hash1 = hash_password(pwd)
    hash2 = hash_password(pwd)
    assert hash1 != hash2


def test_verify_password_correct():
    """A valid plain-text password verifies against its stored hash."""
    hashed = hash_password("correct-password")
    assert verify_password("correct-password", hashed) is True


def test_verify_password_incorrect():
    """Wrong password does NOT verify against a hash."""
    hashed = hash_password("real-password")
    assert verify_password("wrong", hashed) is False


def test_verify_password_cross_hash():
    """Each hash is bound to its own password — no cross-verification."""
    hash_a = hash_password("password-a")
    hash_b = hash_password("password-b")
    assert verify_password("password-a", hash_b) is False
    assert verify_password("password-b", hash_a) is False


# ---------------------------------------------------------------------------
# JWT creation
# ---------------------------------------------------------------------------


def test_create_access_token_returns_jwt_string():
    """``create_access_token`` returns a three-part JWT with dots."""
    token = create_access_token("user-123")
    assert isinstance(token, str)
    assert token.count(".") == 2


def test_create_access_token_contains_sub_claim():
    """The token's ``sub`` claim matches the given subject."""
    user_id = "user-abc-999"
    token = create_access_token(user_id)
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
    assert payload["sub"] == user_id


def test_create_access_token_includes_timestamps():
    """A valid token has ``exp`` and ``iat`` claims."""
    token = create_access_token("u1")
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
    assert "exp" in payload
    assert "iat" in payload


def test_create_access_token_respects_expiry_setting():
    """The token expiry should be approximately ``jwt_expires_in_minutes`` away."""
    now = datetime.now(timezone.utc)
    token = create_access_token("u1")
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
    exp_dt = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    diff = (exp_dt - now).total_seconds()
    expected = settings.jwt_expires_in_minutes * 60
    # Allow 10 seconds of clock drift
    assert expected - 10 <= diff <= expected + 10


# ---------------------------------------------------------------------------
# JWT decoding
# ---------------------------------------------------------------------------


def test_decode_access_token_valid():
    """A valid token decodes to a dict with the correct subject."""
    user_id = "user-test-42"
    token = create_access_token(user_id)
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == user_id


def test_decode_access_token_invalid_returns_none():
    """Garbage / malformed tokens return ``None``."""
    assert decode_access_token("not-a-jwt") is None
    assert decode_access_token("") is None


def test_decode_access_token_expired_returns_none():
    """An intentionally expired token returns ``None``."""
    expired_payload = {
        "sub": "user-expired",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
    }
    expired_token = jwt.encode(
        expired_payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    assert decode_access_token(expired_token) is None


def test_decode_access_token_wrong_secret_returns_none():
    """A token signed with a different secret returns ``None``."""
    token = jwt.encode(
        {"sub": "u1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "wrong-secret",
        algorithm=settings.jwt_algorithm,
    )
    assert decode_access_token(token) is None
