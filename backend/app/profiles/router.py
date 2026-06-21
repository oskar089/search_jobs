from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.router import get_current_user_id
from app.config import settings
from app.database import get_session
from app.models import CurriculumVitae, Profile
from app.profiles.cv_parser import CVParser
from app.profiles.file_storage import FileStorageService
from app.profiles.linkedin_importer import LinkedInImporter
from app.profiles.merge_service import MergeService
from app.profiles.schemas import (
    CVParseResult,
    ImportUrlRequest,
    ImportedProfile,
    MergeRequest,
    ProfileResponse,
    ProfileUpdate,
)

router = APIRouter(prefix="/profiles", tags=["profiles"])

_MAX_CV_SIZE = 10 * 1024 * 1024  # 10 MB


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
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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


# ---------------------------------------------------------------------------
# Import endpoints  (Tasks 3.2, 3.4)
# ---------------------------------------------------------------------------


@router.post("/import/linkedin", response_model=ImportedProfile)
async def import_linkedin(
    body: ImportUrlRequest,
    user_id: str = Depends(get_current_user_id),  # noqa: ARG001
):
    """Import profile data from a LinkedIn URL via third-party API.

    Returns parsed fields for the user to review before saving.
    """
    importer = LinkedInImporter(
        api_key=settings.linkedin_api_key,
        api_url=settings.linkedin_api_url,
    )
    try:
        return await importer.import_profile(body.url)
    except ValueError as e:
        msg = str(e)
        if msg.startswith("Invalid LinkedIn URL"):
            raise HTTPException(status_code=422, detail=msg)
        if "timed out" in msg or "rate limit" in msg:
            raise HTTPException(status_code=504, detail=msg)
        raise HTTPException(status_code=502, detail=msg)


@router.post("/import/infojobs", response_model=ImportedProfile)
async def import_infojobs(
    body: ImportUrlRequest,
    user_id: str = Depends(get_current_user_id),  # noqa: ARG001
):
    """Import profile data from an Infojobs public profile URL via scraping.

    Returns parsed fields for the user to review before saving.
    """
    if "infojobs" not in body.url:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid Infojobs URL: '{body.url}'. URL must contain 'infojobs'.",
        )

    from app.scrapers.profile_scraper import InfojobsProfileScraper

    scraper = InfojobsProfileScraper()
    try:
        return await scraper.parse_profile(body.url)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to scrape Infojobs profile: {e}",
        )


@router.post("/import/preview-save", response_model=ProfileResponse)
async def preview_save(
    body: MergeRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Merge imported preview data into the user's profile and save.

    Uses the fill-empty merge strategy: existing populated fields are never
    overwritten; new list items are appended.
    """
    result = await session.execute(select(Profile).where(Profile.user_id == user_id))
    profile = result.scalar_one_or_none()

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Profile not found. Create one via PUT first.",
        )

    existing = {
        "headline": profile.headline,
        "summary": profile.summary,
        "skills": profile.skills or [],
        "education": profile.education or [],
        "work_experience": profile.work_experience or [],
        "linkedin_url": profile.linkedin_url,
        "infojobs_url": profile.infojobs_url,
        "cv_file_url": profile.cv_file_url,
    }

    merged = MergeService.merge(existing, body.preview_data)
    for field, value in merged.items():
        setattr(profile, field, value)

    await session.flush()
    return profile


# ---------------------------------------------------------------------------
# CV endpoints  (Task 3.6)
# ---------------------------------------------------------------------------


@router.post("/cv/upload", response_model=CVParseResult)
async def upload_cv(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Upload a CV PDF, parse its content, and persist the file.

    Validates that the file is a PDF and does not exceed 10 MB.
    Parses the content via OpenAI and returns extracted fields for preview.
    """
    # --- Validate PDF content type ---
    content_type = (file.content_type or "").lower()
    filename = (file.filename or "").lower()
    if content_type != "application/pdf" and not filename.endswith(".pdf"):
        raise HTTPException(
            status_code=422,
            detail="Only PDF files are accepted.",
        )

    # --- Validate file size ---
    content = await file.read()
    if len(content) > _MAX_CV_SIZE:
        raise HTTPException(
            status_code=422,
            detail=f"File too large. Maximum size is {_MAX_CV_SIZE // (1024 * 1024)} MB.",
        )
    await file.seek(0)

    # --- Persist file ---
    storage = FileStorageService(upload_dir=settings.upload_dir)
    cv_meta = await storage.save(file, user_id)

    # --- Parse CV via OpenAI ---
    file_path = str(Path(settings.upload_dir) / f"{cv_meta.id}.pdf")
    parser = CVParser()
    try:
        parse_result = await parser.parse_cv(file_path)
    except Exception:
        # File saved but parsing failed — return metadata without parsed data
        parse_result = CVParseResult(
            id=cv_meta.id,
            file_name=cv_meta.filename,
            file_size=cv_meta.file_size,
            parsed_data=ImportedProfile(),
        )

    # --- Create DB record ---
    cv_record = CurriculumVitae(
        id=cv_meta.id,
        user_id=user_id,
        filename=cv_meta.filename,
        file_path=file_path,
        file_size=cv_meta.file_size,
        parsed_data=(
            parse_result.parsed_data.model_dump()
            if parse_result.parsed_data
            else None
        ),
    )
    session.add(cv_record)

    # --- Update profile's cv_file_url ---
    profile_result = await session.execute(
        select(Profile).where(Profile.user_id == user_id),
    )
    profile = profile_result.scalar_one_or_none()
    if profile is not None:
        profile.cv_file_url = file_path

    await session.flush()

    return CVParseResult(
        id=cv_meta.id,
        file_name=cv_meta.filename,
        file_size=cv_meta.file_size,
        parsed_data=parse_result.parsed_data or ImportedProfile(),
    )


@router.get("/cv/download/{cv_id}")
async def download_cv(
    cv_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Download a stored CV PDF file."""
    result = await session.execute(
        select(CurriculumVitae).where(
            CurriculumVitae.id == cv_id,
            CurriculumVitae.user_id == user_id,
        ),
    )
    cv_record = result.scalar_one_or_none()
    if cv_record is None:
        raise HTTPException(status_code=404, detail="CV not found.")

    storage = FileStorageService(upload_dir=settings.upload_dir)
    try:
        return storage.serve(cv_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="CV file not found on disk.")


@router.delete("/cv/{cv_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cv(
    cv_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Delete a stored CV PDF file and its database record."""
    result = await session.execute(
        select(CurriculumVitae).where(
            CurriculumVitae.id == cv_id,
            CurriculumVitae.user_id == user_id,
        ),
    )
    cv_record = result.scalar_one_or_none()
    if cv_record is None:
        raise HTTPException(status_code=404, detail="CV not found.")

    storage = FileStorageService(upload_dir=settings.upload_dir)
    try:
        storage.delete(cv_id)
    except FileNotFoundError:
        pass  # File already gone — still remove the record

    await session.delete(cv_record)

    # Clear cv_file_url on profile if it points to this CV
    profile_result = await session.execute(
        select(Profile).where(Profile.user_id == user_id),
    )
    profile = profile_result.scalar_one_or_none()
    if profile is not None and profile.cv_file_url and cv_id in profile.cv_file_url:
        profile.cv_file_url = None

    await session.flush()
