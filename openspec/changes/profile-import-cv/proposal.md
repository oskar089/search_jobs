# Proposal: Profile Import & CV Management

## Intent

Users spend too long filling profile fields manually. We need to let them import from LinkedIn / Infojobs and upload a CV PDF — parse both sources, show an editable preview, and merge into their existing profile without data loss.

## Scope

### In Scope
- LinkedIn profile import via third-party API (ProxyCurl / Scrapin.io)
- Infojobs public profile scraping via Playwright
- CV PDF upload, parsing (OpenAI), and persistent storage + download
- Editable preview of imported/parsed data before saving
- Merge strategy: imported data combines with existing — overwrites nothing
- New profile fields: headline, summary, skills (with level), education, work_experience, linkedin_url, infojobs_url, cv_file_url

### Out of Scope
- LinkedIn OAuth login flow (API-key based, not OAuth)
- Infojobs authenticated scraping (public pages only)
- Multiple CVs per profile
- Cover letter generation from CV (existing feature, not changing)
- AI-powered profile enrichment beyond CV parsing

## Capabilities

### New Capabilities
- `profile-import`: Import profile data from LinkedIn URL (third-party API) and Infojobs URL (scraping) into an editable preview before saving
- `cv-management`: Upload, parse (OpenAI), store (file server), and download CV PDFs linked to a profile

### Modified Capabilities
- `profile-management`: Add fields (headline, summary, skills, education, work_experience, linkedin_url, infojobs_url, cv_file_url) and import-preview endpoint

## Approach

1. **Profile model**: Add new columns via Alembic migration + SQLAlchemy model changes
2. **Import endpoints**: `POST /api/profile/import/linkedin`, `POST /api/profile/import/infojobs`, `POST /api/profile/import/preview-save` — each returns parsed data for preview, final save merges with existing
3. **CV endpoints**: `POST /api/profile/cv/upload`, `GET /api/profile/cv/download/{id}`, `DELETE /api/profile/cv/{id}` — parse via OpenAI file processing, store PDF on local filesystem or S3-compatible
4. **Scraper abstraction**: New `ProfileScraper` base class in `scrapers/`; `InfojobsProfileScraper` subclass
5. **Third-party integration**: `LinkedInImporter` service that calls ProxyCurl/Scrapin.io API
6. **Frontend**: New "Importar perfil" and "Subir CV" sections on Profile page; editable preview modal; all UI in Spanish

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/app/models/profile.py` | Modified | New columns + relationships |
| `backend/app/schemas/profile.py` | Modified | New Pydantic schemas for import/cv |
| `backend/app/routers/profile.py` | Modified | +5 new endpoints |
| `backend/app/scrapers/engine.py` | Modified | Base ScraperEngine already exists |
| `backend/app/scrapers/profile_scraper.py` | New | Profile scraping abstraction |
| `backend/app/services/linkedin_importer.py` | New | Third-party API integration |
| `backend/app/services/cv_parser.py` | New | OpenAI-based CV parsing |
| `backend/app/services/file_storage.py` | New | CV file storage + serving |
| `frontend/src/pages/Profile.tsx` | Modified | Import + CV UI sections |
| `frontend/src/lib/profiles.ts` | Modified | New API client methods |
| `frontend/src/types/index.ts` | Modified | New types for import data |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| LinkedIn API changes / deprecation | Medium | Wrap in adapter, abstract behind `LinkedInImporter` interface; monitor API status |
| Infojobs scraping breaks on layout changes | Medium | Version selectors, test against snapshot; alert on failure |
| CV parsing quality varies wildly | Medium | Show editable preview; let user correct before save |
| Large CV PDF uploads fail | Low | File size limits + upload progress indicator |

## Rollback Plan

- **DB**: Create migration as additive only (no destructive column drops). Rollback via `alembic downgrade -1`.
- **Endpoints**: New endpoints don't break existing. Remove import endpoints and file storage route; clients lose feature but keep working.
- **Frontend**: Feature-flag import/CV sections. Toggle off via env var if issues arise.

## Dependencies

- ProxyCurl or Scrapin.io API key in `.env` (third-party)
- File storage path config in `.env` (default: local `uploads/cv/`)
- OpenAI API key already configured; verify GPT-4o vision access for PDF parsing

## Success Criteria

- [ ] Import LinkedIn profile → see preview with headline, summary, skills, experience — merge without data loss
- [ ] Import Infojobs public profile → see same preview with available fields
- [ ] Upload CV PDF → parsed fields show in preview; original PDF downloadable
- [ ] All test suites pass (`pytest -v --tb=short --cov=app --cov-report=term-missing`)
- [ ] Lint + type check pass (`ruff check app && mypy app`)
