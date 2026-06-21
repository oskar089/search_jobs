# Tasks: Profile Import & CV Management

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1,300 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (foundation) → PR 2 (services) → PR 3 (routes) → PR 4 (frontend) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | DB models + migration + schemas + config + merge service | PR 1 | Base = feature branch `profile-import-cv`. Tests included. |
| 2 | Backend services (file_storage, linkedin_importer, infojobs_scraper, cv_parser) + unit tests | PR 2 | Base = PR 1 branch. Depends on schemas from PR 1. |
| 3 | Backend routes (import + CV endpoints) + integration tests | PR 3 | Base = PR 2 branch. Depends on services from PR 2. |
| 4 | Frontend (types, API client, UI sections, preview modals) + E2E tests | PR 4 | Base = PR 3 branch. Depends on routes from PR 3. |

## Phase 1: Foundation — Models, Migration, Schemas, Config

- [x] 1.1 Add JSON + string columns to `Profile` model (headline, summary, skills, education, work_experience, linkedin_url, infojobs_url, cv_file_url)
- [x] 1.2 Create `CurriculumVitae` model in `backend/app/models/curriculum_vitae.py` with id, user_id FK, filename, file_path, file_size, parsed_data JSON, uploaded_at
- [x] 1.3 Register `CurriculumVitae` in `backend/app/models/__init__.py`
- [x] 1.4 Add Pydantic schemas to `backend/app/profiles/schemas.py`: SkillItem, EducationItem, ExperienceItem, ImportedProfile, CVParseResult, MergeRequest, CVResponse
- [x] 1.5 Add new fields to existing ProfileResponse / ProfileUpdate schemas
- [x] 1.6 Create Alembic migration for Profile column additions + CurriculumVitae table
- [x] 1.7 Add `LINKEDIN_API_KEY`, `LINKEDIN_API_URL`, `UPLOAD_DIR` to `backend/app/config.py`
- [x] 1.8 **RED**: Write merge strategy unit test (fill-empty, append-new, no-overwrite)
- [x] 1.9 **GREEN**: Implement `MergeService.merge()` in `backend/app/profiles/merge_service.py`

## Phase 2: Backend Services — Importers, Parsers, Storage

- [x] 2.1 **RED**: Unit test for `FileStorageService.save()`, `serve()`, `delete()` with temp dir
- [x] 2.2 **GREEN**: Create `FileStorageService` in `backend/app/profiles/file_storage.py`
- [x] 2.3 **RED**: Unit test for `LinkedInImporter.map_response()` with mock HTTP client
- [x] 2.4 **GREEN**: Create `LinkedInImporter` in `backend/app/profiles/linkedin_importer.py`
- [x] 2.5 **RED**: Unit test for `InfojobsProfileScraper.parse()` with mock ScraperEngine DOM
- [x] 2.6 **GREEN**: Create `ProfileScraper` ABC in `backend/app/scrapers/profile_scraper.py` + `InfojobsProfileScraper` subclass
- [x] 2.7 **RED**: Unit test for `CVParser.extract_text()` with sample PDF fixture
- [x] 2.8 **GREEN**: Create `CVParser` in `backend/app/profiles/cv_parser.py` (pdfplumber + OpenAI)

## Phase 3: Backend Routes — Import + CV Endpoints

- [x] 3.1 **RED**: Integration test for `POST /profiles/import/linkedin` and `/import/infojobs` with mock external HTTP
- [x] 3.2 **GREEN**: Add `POST /profiles/import/linkedin` and `POST /profiles/import/infojobs` to router.py (body: `{url}`, return `ImportedProfile`)
- [x] 3.3 **RED**: Integration test for `POST /profiles/import/preview-save` (merge, verify no overwrite)
- [x] 3.4 **GREEN**: Add `POST /profiles/import/preview-save` to router.py (body: MergeRequest, return ProfileResponse)
- [x] 3.5 **RED**: Integration test for CV upload/download/delete cycle (real tiny PDF)
- [x] 3.6 **GREEN**: Add `POST /profiles/cv/upload`, `GET /profiles/cv/download/{id}`, `DELETE /profiles/cv/{id}` to router.py

## Phase 4: Frontend — Spanish UI + Integration

- [x] 4.1 Add `ImportedProfile`, `CVParseResult`, `SkillItem`, `EducationItem`, `ExperienceItem` types to `frontend/src/types/index.ts`
- [x] 4.2 Add `importLinkedin`, `importInfojobs`, `previewSave`, `uploadCv`, `downloadCv`, `deleteCv` methods to `frontend/src/lib/profiles.ts`
- [x] 4.3 Add "Importar perfil" section to Profile.tsx: provider selector (LinkedIn/Infojobs), URL input, import trigger, editable preview modal with all fields
- [x] 4.4 Add "Subir CV" section to Profile.tsx: file upload with progress indicator, parsed preview modal, download/delete actions
- [x] 4.5 Wire preview-save flow: user edits preview → click "Guardar" → merge with existing profile → update UI
- [x] 4.6 **E2E**: Playwright test for import flow — fill URL, click import, see preview modal

## Verification Checklist

- [ ] `pytest -v --tb=short` passes (unit + integration)
- [ ] `ruff check app && mypy app` passes
- [ ] `pytest --cov=app --cov-report=term-missing` ≥ 80%
- [ ] LinkedIn import → editable preview → merge without data loss
- [ ] CV upload (PDF) → parsed preview → download original → delete
- [ ] Invalid URL / non-PDF / missing CV → proper error responses
