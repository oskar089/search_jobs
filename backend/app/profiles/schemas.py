from datetime import datetime

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Import / CV item schemas
# ---------------------------------------------------------------------------


class SkillItem(BaseModel):
    name: str
    level: str = "intermediate"  # beginner | intermediate | advanced | expert


class EducationItem(BaseModel):
    institution: str
    degree: str
    field: str | None = None
    start_date: str
    end_date: str | None = None
    description: str | None = None


class ExperienceItem(BaseModel):
    company: str
    role: str
    start_date: str = ""
    end_date: str | None = None
    description: str | None = None
    location: str | None = None
    current: bool = False


class ImportedProfile(BaseModel):
    """Full structured profile from an external source (LinkedIn / Infojobs / CV)."""

    headline: str | None = None
    summary: str | None = None
    skills: list[SkillItem] = []
    education: list[EducationItem] = []
    work_experience: list[ExperienceItem] = []
    linkedin_url: str | None = None
    infojobs_url: str | None = None


class CVParseResult(BaseModel):
    """Result of parsing a CV upload."""

    id: str
    file_name: str
    file_size: int
    parsed_data: ImportedProfile


class ImportUrlRequest(BaseModel):
    """Request body containing a URL to import."""

    url: str


class MergeRequest(BaseModel):
    """Request body for the preview-save merge endpoint."""

    preview_data: ImportedProfile
    strategy: str = "fill-empty"


class CVResponse(BaseModel):
    """Metadata response for a stored CurriculumVitae."""

    id: str
    user_id: str
    filename: str
    file_size: int
    uploaded_at: datetime | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Profile response / update schemas (extended with import fields)
# ---------------------------------------------------------------------------


class ProfileResponse(BaseModel):
    id: str
    user_id: str
    target_roles: list[str] = []
    tech_stack: list[str] = []
    experience_level: str
    min_salary: int | None = None
    max_salary: int | None = None
    locations: list[str] = []
    remote_only: bool = False
    languages: list[str] = []
    is_active: bool = True

    # Profile import / CV fields
    headline: str | None = None
    summary: str | None = None
    skills: list[SkillItem] = []
    education: list[EducationItem] = []
    work_experience: list[ExperienceItem] = []
    linkedin_url: str | None = None
    infojobs_url: str | None = None
    cv_file_url: str | None = None

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    target_roles: list[str] | None = None
    tech_stack: list[str] | None = None
    experience_level: str | None = None
    min_salary: int | None = None
    max_salary: int | None = None
    locations: list[str] | None = None
    remote_only: bool | None = None
    languages: list[str] | None = None
    is_active: bool | None = None

    # Profile import / CV fields
    headline: str | None = None
    summary: str | None = None
    skills: list[SkillItem] | None = None
    education: list[EducationItem] | None = None
    work_experience: list[ExperienceItem] | None = None
    linkedin_url: str | None = None
    infojobs_url: str | None = None
    cv_file_url: str | None = None
