"""Auth router with JWT cookie auth, refresh rotation, logout, and theft detection.

Maintains dual auth mode: accepts both cookies and Bearer headers.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from app.auth.utils import (
    create_access_token,
    create_refresh_token,
    create_reset_token,
    decode_access_token,
    decode_reset_token,
    hash_password,
    verify_password,
)
from app.auth.redis_client import (
    blacklist_refresh_token,
    clear_lockout,
    clear_user_blacklist,
    is_account_locked,
    is_token_blacklisted,
    record_failed_login,
)
from app.database import get_session
from app.middleware.rate_limit import limiter
from app.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Cookie settings
# ---------------------------------------------------------------------------
ACCESS_TOKEN_MAX_AGE = 900  # 15 minutes in seconds
REFRESH_TOKEN_TTL = 604800  # 7 days in seconds


def _set_access_token_cookie(response: Response, token: str) -> None:
    """Set the access_token as an httpOnly, secure, SameSite=Lax cookie."""
    response.set_cookie(
        key="access_token",
        value=token,
        max_age=ACCESS_TOKEN_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/api",
    )


def _clear_access_token_cookie(response: Response) -> None:
    """Clear the access_token cookie."""
    response.set_cookie(
        key="access_token",
        value="",
        max_age=0,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/api",
    )


# ---------------------------------------------------------------------------
# Auth dependencies
# ---------------------------------------------------------------------------


async def get_token(request: Request, authorization: str | None = Header(None)) -> str:
    """Extract JWT from cookie first, then fall back to Authorization header.

    Dual auth mode: cookies are preferred (modern clients), Bearer header
    is the fallback (legacy/mobile clients).
    """
    # Try cookie first
    token = request.cookies.get("access_token")
    if token:
        return token

    # Fall back to header
    if authorization and authorization.startswith("Bearer "):
        return authorization.removeprefix("Bearer ")

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )


async def get_current_user_id(token: str = Depends(get_token)) -> str:
    """Decode JWT token and return the user ID (sub claim)."""
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    return user_id


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------


def _decode_refresh_token(token: str) -> dict | None:
    """Decode and validate a refresh token. Returns payload or None."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("purpose") != "refresh":
            return None
        return payload
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(
    request: Request,
    body: RegisterRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """Register a new user and return tokens via cookie + body."""
    result = await session.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        name=body.name,
    )
    session.add(user)
    await session.flush()

    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)

    _set_access_token_cookie(response, access)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """Authenticate a user and set access_token cookie, return refresh_token.

    Implements account lockout: 5 consecutive failed attempts lock the
    account for 15 minutes (backed by Redis). On successful login the
    lockout counter is cleared.
    """
    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    # Early exit if account is locked — skip password check
    if user and await is_account_locked(user.id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account is locked due to too many failed login attempts. Try again in 15 minutes.",
        )

    if not user or not verify_password(body.password, user.password_hash):
        # Record the failed attempt (only for known users to avoid leaking info)
        if user:
            await record_failed_login(user.id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Successful login — clear lockout
    await clear_lockout(user.id)

    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)

    _set_access_token_cookie(response, access)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_session),
):
    """Send a password reset email with a short-lived token (30 min).

    Always returns 200 to avoid email enumeration — the user will
    only receive an email if the account exists and SMTP is configured.
    """
    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is not None:
        token = create_reset_token(user.email)
        reset_url = f"{settings.app_url}/reset-password?token={token}"

        from app.notifications.service import NotificationService
        service = NotificationService(None)
        await service.send_email(
            to=user.email,
            subject="Password Reset — Search Jobs",
            body=(
                f"Hi {user.name or 'there'},\n\n"
                f"You requested a password reset. Click the link below to reset your password:\n\n"
                f"{reset_url}\n\n"
                f"This link expires in 30 minutes.\n\n"
                f"If you didn't request this, ignore this email."
            ),
        )

    return {"message": "If the email exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    session: AsyncSession = Depends(get_session),
):
    """Reset the password using a reset token received by email."""
    email = decode_reset_token(body.token)
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user.password_hash = hash_password(body.password)
    await session.flush()

    return {"message": "Password reset successfully"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """Issue a new token pair with refresh token rotation.

    1. Validate the refresh token
    2. Check blacklist — if found, trigger theft detection
    3. Blacklist the old refresh token
    4. Issue a new access token (cookie) + new refresh token (body)
    """
    payload = _decode_refresh_token(body.refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload",
        )

    # Check blacklist — theft detection
    blacklisted = await is_token_blacklisted(user_id, body.refresh_token)
    if blacklisted:
        logger.warning(
            "Theft detected: blacklisted refresh token reused for user %s. "
            "Clearing all refresh tokens.",
            user_id,
        )
        await clear_user_blacklist(user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked. Please log in again.",
        )

    # Verify user still exists
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Blacklist the current refresh token
    await blacklist_refresh_token(user_id, body.refresh_token, REFRESH_TOKEN_TTL)

    # Issue new tokens
    new_access = create_access_token(user_id)
    new_refresh = create_refresh_token(user_id)

    _set_access_token_cookie(response, new_access)
    return TokenResponse(access_token=new_access, refresh_token=new_refresh)


@router.post("/logout")
async def logout(
    body: LogoutRequest,
    response: Response,
    user_id: str = Depends(get_current_user_id),
):
    """Logout by blacklisting the refresh token (if provided) and clearing the cookie."""
    # Blacklist the refresh token if one was provided
    if body.refresh_token:
        await blacklist_refresh_token(user_id, body.refresh_token, REFRESH_TOKEN_TTL)

    # Clear the cookie
    _clear_access_token_cookie(response)

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Return the currently authenticated user's info."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user
