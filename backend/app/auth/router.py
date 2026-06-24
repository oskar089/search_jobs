from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from app.auth.utils import (
    create_access_token,
    create_reset_token,
    decode_access_token,
    decode_reset_token,
    hash_password,
    verify_password,
)
from app.database import get_session
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


async def get_token_from_header(authorization: str = Header(...)) -> str:
    """Extract Bearer token from the Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )
    return authorization.removeprefix("Bearer ")


async def get_current_user_id(token: str = Depends(get_token_from_header)) -> str:
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


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, session: AsyncSession = Depends(get_session)):
    """Register a new user and return a JWT token."""
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

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)):
    """Authenticate a user and return a JWT token."""
    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_session),
):
    """Send a password reset email with a short-lived token (30 min).

    Always returns 200 to avoid email enumeration — the user will
    only receive an email if the account exists and SMTP is configured.
    """
    # Check if user exists
    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is not None:
        # Generate reset token
        token = create_reset_token(user.email)
        reset_url = f"{settings.app_url}/reset-password?token={token}"

        # Send email
        from app.notifications.service import NotificationService
        service = NotificationService(None)  # We only need send_email
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

    return {
        "message": "If the email exists, a reset link has been sent.",
    }


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
    user_id: str = Depends(get_current_user_id),
):
    """Issue a new JWT token for the currently authenticated user.

    The client can call this before the current token expires to keep
    the session alive without requiring the user to log in again.
    """
    token = create_access_token(user_id)
    return TokenResponse(access_token=token)


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
