from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.router import get_current_user_id
from app.database import get_session
from app.models import Notification, Profile

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationResponse(BaseModel):
    id: str
    application_id: str | None = None
    type: str
    channel: str
    title: str
    body: str
    is_read: bool
    sent_at: datetime
    read_at: datetime | None = None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """List the current user's notifications, newest first."""
    result = await session.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.sent_at.desc()),
    )
    return result.scalars().all()


@router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Mark a notification as read."""
    result = await session.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        ),
    )
    notif = result.scalar_one_or_none()
    if notif is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    notif.is_read = True
    notif.read_at = datetime.now(timezone.utc)
    await session.flush()
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Notification Preferences
# ---------------------------------------------------------------------------

DEFAULT_PREFERENCES: dict = {
    "in_app": True,
    "email": False,
    "on_submit": True,
    "on_fail": True,
    "on_match": True,
}


class NotificationPreferencesResponse(BaseModel):
    in_app: bool = True
    email: bool = False
    on_submit: bool = True
    on_fail: bool = True
    on_match: bool = True


class NotificationPreferencesUpdate(BaseModel):
    in_app: bool | None = None
    email: bool | None = None
    on_submit: bool | None = None
    on_fail: bool | None = None
    on_match: bool | None = None


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Return the current user's notification preferences from their profile."""
    result = await session.execute(
        select(Profile).where(Profile.user_id == user_id),
    )
    profile = result.scalar_one_or_none()
    if profile is None or profile.notification_preferences is None:
        return NotificationPreferencesResponse(**DEFAULT_PREFERENCES)
    return NotificationPreferencesResponse(**profile.notification_preferences)


@router.put("/preferences", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    data: NotificationPreferencesUpdate,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Update the current user's notification preferences."""
    result = await session.execute(
        select(Profile).where(Profile.user_id == user_id),
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    current = profile.notification_preferences or {}
    merged = {**DEFAULT_PREFERENCES, **current}

    for field in ("in_app", "email", "on_submit", "on_fail", "on_match"):
        value = getattr(data, field, None)
        if value is not None:
            merged[field] = value

    profile.notification_preferences = merged
    await session.flush()
    return NotificationPreferencesResponse(**merged)
