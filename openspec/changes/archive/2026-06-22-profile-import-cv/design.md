# Design: Profile Import & CV Management

## Technical Approach

Five self-contained additions to the existing `app/profiles/` domain: model columns, import services (LinkedIn API, Infojobs scraping), CV upload/parse, file storage, and frontend sections. Models add JSON columns for structured data (skills, education, experience) to avoid separate tables. Services mirror the flat-package pattern used by `cover_letter/` and `matching/`.

## Architecture Decisions

| Decision | Option | Rationale |
|----------|--------|-----------|
| **Skills/education/experience storage** | `JSON` columns vs separate tables | **JSON columns**. Lists are always loaded with profile (no pagination needed); keeps schema additive; SQLAlchemy `JSON` type works on both PostgreSQL and SQLite (native JSON support). Normalize later if querying becomes necessary. |
| **CV file model** | `CurriculumVitae` table vs flat field on Profile | **Separate table**. Endpoints use `{id}` (not profile ID) for download/delete. Enables future multi-CV. Profile gets a `cv_id` FK pointing to the active CV. |
| **Import service location** | `app/services/` vs `app/profiles/` | **`app/profiles/`**. Follows existing flat-domain pattern (`cover_letter/generator.py`, `matching/engine.py`). No separate services package needed. |
| **LinkedIn API adapter** | ProxyCurl / Scrapin.io behind `LinkedInImporter` class | **Interface pattern**. Wraps HTTP calls; swap provider by changing env var `LINKEDIN_API_KEY` + `LINKEDIN_API_URL`. No OAuth — API-key based per scope. |
| **Infojobs scraping** | New `ProfileScraper` base + `InfojobsProfileScraper` subclass | Reuses existing `ScraperEngine` for browser automation. `ProfileScraper` in `app/scrapers/profile_scraper.py` with structured `ProfileSelectors` dataclass. |
| **Merge strategy** | Imported data fills empty fields only | Simple fields set only when `None`. List fields append items not already present (by name/institution key). User edits preview in modal before save. |
| **File storage** | Local filesystem initially | Configurable via `UPLOAD_DIR` in `.env`. S3-compatible adapter later behind a `FileStorage` abstract class. |

## Data Flow

```
LinkedIn Import:
  Client ──POST /profiles/import/linkedin {url}──→ LinkedInImporter
    → HTTP GET {LINKEDIN_API_URL}?url={url}
    ← Mapped ImportedProfile schema
  Client ──POST /profiles/import/preview-save──→ MergeService
    → Compare with existing Profile
    → Fill empty fields, append new list items
    ← ProfileResponse

Infojobs Import:
  Client ──POST /profiles/import/infojobs {url}──→ InfojobsProfileScraper
    → ScraperEngine (Playwright) → navigate public profile
    → Extract fields via CSS selectors
    ← ImportedProfile schema

CV Upload:
  Client ──POST /profiles/cv/upload (multipart)──→ FileStorageService.save()
    → File saved to uploads/cv/{uuid}.pdf
    → CurriculumVitae row created
    → CVParser (pdfplumber → text → OpenAI) → structured data
    ← CVParseResult + file metadata
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/models/profile.py` | Modify | Add headline, summary, skills, education, work_experience, linkedin_url, infojobs_url (JSON/MutableDict for lists) |
| `backend/app/models/curriculum_vitae.py` | Create | CV model: id, profile_id FK, file_path, file_name, file_size, parsed_data (JSON), timestamps |
| `backend/app/profiles/schemas.py` | Modify | Add ProfileImport, ImportedProfile, CVUploadResponse, MergePreview schemas |
| `backend/app/profiles/router.py` | Modify | Add 5 new endpoints under existing `/profiles` prefix |
| `backend/app/profiles/linkedin_importer.py` | Create | `LinkedInImporter` class — HTTP client wrapping ProxyCurl/Scrapin.io |
| `backend/app/profiles/cv_parser.py` | Create | `CVParser` — pdfplumber text extraction + OpenAI structured parse |
| `backend/app/profiles/file_storage.py` | Create | `FileStorageService` — local save, serve, delete |
| `backend/app/scrapers/profile_scraper.py` | Create | `ProfileScraper` ABC + `InfojobsProfileScraper` |
| `backend/app/config.py` | Modify | Add `LINKEDIN_API_KEY`, `LINKEDIN_API_URL`, `UPLOAD_DIR` settings |
| `backend/alembic/versions/002_profile_import.py` | Create | Migration: ADD columns + curriculum_vitae table |
| `frontend/src/types/index.ts` | Modify | Add `ImportedProfile`, `CVParseResult` types |
| `frontend/src/lib/profiles.ts` | Modify | Add `importLinkedin`, `importInfojobs`, `previewSave`, `uploadCv`, `downloadCv`, `deleteCv` API methods |
| `frontend/src/pages/Profile.tsx` | Modify | Add "Importar perfil" section (URL input + preview Modal) and "Subir CV" section (file upload + preview Modal) |

## Interfaces / Contracts

```python
# Import preview schema (backend/app/profiles/schemas.py)
class ImportedProfile(BaseModel):
    headline: str | None = None
    summary: str | None = None
    skills: list[SkillItem] = []
    education: list[EducationItem] = []
    work_experience: list[ExperienceItem] = []
    linkedin_url: str | None = None
    infojobs_url: str | None = None

class SkillItem(BaseModel):
    name: str
    level: str = "intermediate"  # beginner|intermediate|advanced|expert

class EducationItem(BaseModel):
    institution: str
    degree: str
    field: str | None = None
    start_year: int | None = None
    end_year: int | None = None

class ExperienceItem(BaseModel):
    company: str
    title: str
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None
    current: bool = False

# CV result
class CVParseResult(BaseModel):
    id: str
    file_name: str
    file_size: int
    parsed: ImportedProfile

# Merge
class MergeRequest(BaseModel):
    imported: ImportedProfile
```

New API endpoints:
- `POST /profiles/import/linkedin` — body: `{"url": str}` → `ImportedProfile`
- `POST /profiles/import/infojobs` — body: `{"url": str}` → `ImportedProfile`
- `POST /profiles/import/preview-save` — body: `MergeRequest` → `ProfileResponse`
- `POST /profiles/cv/upload` — multipart: `file: UploadFile` → `CVParseResult`
- `GET /profiles/cv/download/{id}` → `FileResponse` (application/pdf)
- `DELETE /profiles/cv/{id}` → `204`

## Testing Strategy

| Layer | What | How |
|-------|------|-----|
| Unit | `LinkedInImporter.map_response()` | Mock HTTP client, assert field mapping |
| Unit | `CVParser.extract_text()` | Test with sample PDF fixtures |
| Unit | `MergeService.merge()` | Profile with existing data + imported → assert no overwrite |
| Unit | `InfojobsProfileScraper.parse()` | Mock ScraperEngine, return fake DOM |
| Unit | `FileStorageService` | Temp directory, test write/read/delete |
| Integration | Import endpoints | httpx AsyncClient + SQLite test DB, mock external HTTP |
| Integration | CV upload+download | Upload real tiny PDF, download, delete — full cycle |
| E2E | Frontend import flow | Playwright: fill URL, click import, see preview modal |

## Migration / Rollout

Additive migration only. `alembic upgrade head` adds JSON columns (nullable, no defaults needed) and `curriculum_vitae` table. Rollback via `alembic downgrade -1` — data loss limited to un-saved imports.

New endpoints and frontend sections are safe to deploy alongside existing profile code. No DB locks or backfill required.
