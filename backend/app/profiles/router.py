from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.router import get_current_user_id
from app.database import get_session
from app.models import Profile
from app.profiles.schemas import ProfileResponse, ProfileUpdate

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("", response_model=ProfileResponse)
async def get_profile(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Get the current user's profile."""
    result = await session.execute(select(Profile).where(Profile.user_id == user_id))
    profile = result.scalar_one_or_none()

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Create one via PUT.",
        )

    return profile


@router.put("", response_model=ProfileResponse)
async def upsert_profile(
    body: ProfileUpdate,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Create or update the current user's profile."""
    result = await session.execute(select(Profile).where(Profile.user_id == user_id))
    profile = result.scalar_one_or_none()

    update_data = body.model_dump(exclude_unset=True)

    if profile is None:
        # Create new profile — require at least experience_level
        if "experience_level" not in update_data:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="experience_level is required when creating a profile",
            )
        profile = Profile(user_id=user_id, **update_data)
        session.add(profile)
    else:
        # Update existing profile
        for field, value in update_data.items():
            setattr(profile, field, value)

    await session.flush()
    return profile
