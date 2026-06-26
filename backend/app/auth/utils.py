import logging
import uuid

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def create_access_token(subject: str) -> str:
    """Create a JWT access token for the given user ID."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expires_in_minutes)
    to_encode = {"sub": subject, "exp": expire, "iat": datetime.now(timezone.utc)}
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    """Create a JWT refresh token (7 day expiry) for the given user ID.

    Includes a unique ``jti`` (JWT ID) claim to guarantee distinct tokens
    even when multiple tokens are issued within the same second.
    """
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expiry_days)
    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "purpose": "refresh",
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    """Decode and validate a JWT token. Returns payload dict or None on failure."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None


def create_reset_token(email: str) -> str:
    """Create a short-lived JWT for password reset (30 min)."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    to_encode = {"sub": email, "exp": expire, "iat": datetime.now(timezone.utc), "purpose": "reset"}
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_reset_token(token: str) -> str | None:
    """Decode a reset token and return the email if valid. Returns None on failure."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("purpose") != "reset":
            return None
        return payload.get("sub")
    except JWTError:
        return None
