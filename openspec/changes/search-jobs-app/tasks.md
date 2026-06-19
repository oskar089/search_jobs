# Tasks: Search Jobs App — Python Pivot + Foundation

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~900–1,400 |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: Scaffold + Models + Migration → PR 2: Auth + Profiles → PR 3: Portals + Scrapers |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes (resolved → stacked-to-main)
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Scaffold + Python structure + SQLAlchemy models + Alembic migration + FastAPI skeleton | PR 1 | Delete Node/TS, create backend structure, all 8 models, initial migration, config, database module |
| 2 | Auth + Profiles — routers, schemas, JWT utils | PR 2 | `app/auth/`, `app/profiles/`, register/login/me endpoints, profile CRUD |
| 3 | Portal CRUD + Scraper engine | PR 3 | `app/portals/`, `app/scrapers/`, built-in configs, dry-run |

## Phase 1: Project Scaffold — Python Pivot

- [x] 1.1 Delete Node/TS files: `package.json`, `package-lock.json`, `tsconfig.json`, `turbo.json`, `eslint.config.js`, `packages/database/`, `node_modules/`
- [x] 1.2 Create Python project structure: `backend/pyproject.toml`, `backend/requirements.txt`, `.gitignore` (Python), `.env` (Python), `.env.example`
- [x] 1.3 Create FastAPI app skeleton: `backend/app/main.py`, `backend/app/config.py` (pydantic-settings), `backend/app/database.py` (async engine + session + Base)
- [x] 1.4 Create SQLAlchemy models: all 8 tables — User, Profile, Portal, StoredJob, Application, ScrapeSession, PipelineRun, Notification
- [x] 1.5 Create Alembic migration: `backend/alembic.ini`, `backend/alembic/env.py`, initial migration revision `001` — create all 8 tables with FKs and constraints
- [x] 1.6 Apply Alembic migration to Neon — run `alembic upgrade head` against live DB
- [x] 1.7 Rewrite `design.md` — Python stack, FastAPI/SQLAlchemy/Celery/Playwright architecture
- [x] 1.8 Rewrite `tasks.md` — Python tasks with updated phases

## Phase 2: Auth Module

- [x] 2.1 `backend/app/auth/utils.py` — JWT sign/verify (python-jose), password hash/verify (passlib bcrypt)
- [x] 2.2 `backend/app/auth/schemas.py` — RegisterRequest, LoginRequest, TokenResponse, UserResponse (Pydantic v2)
- [x] 2.3 `backend/app/auth/router.py` — POST /api/auth/register, POST /api/auth/login, GET /api/auth/me + JWT dependencies (`get_token_from_header`, `get_current_user_id`)
- [x] 2.4 Register auth router in `backend/app/main.py`

## Phase 3: Profile Module

- [x] 3.1 `backend/app/profiles/schemas.py` — ProfileResponse, ProfileUpdate (Pydantic v2)
- [x] 3.2 `backend/app/profiles/router.py` — GET /api/profiles, PUT /api/profiles (upsert)
- [x] 3.3 Register profiles router in `backend/app/main.py`

## Phase 4: Portal Config + Scraper (future)

- [ ] 4.1 `backend/app/portals/router.py` — CRUD for portal configs
- [ ] 4.2 `backend/app/portals/schemas.py` — PortalCreate, PortalResponse, PortalSelectors schemas
- [ ] 4.3 `backend/app/scrapers/engine.py` — Core scraping engine with Playwright
- [ ] 4.4 `backend/app/scrapers/builtin/linkedin.py` — LinkedIn selector config
- [ ] 4.5 `backend/app/scrapers/builtin/infojobs.py` — Infojobs selector config
- [ ] 4.6 `backend/app/scrapers/builtin/computrabajo.py` — Computrabajo selector config
- [ ] 4.7 `backend/app/scrapers/builtin/bumeran.py` — Bumeran selector config
- [ ] 4.8 Dry-run test mode for portal selectors

## Phase 5: Worker Pipeline (future)

- [ ] 5.1 Celery app setup in `backend/app/celery_app.py`
- [ ] 5.2 Task: scrape portal (Playwright + selectors → StoredJobs)
- [ ] 5.3 Task: match + score (profile → StoredJob → score)
- [ ] 5.4 Task: apply (Playwright form fill + cover letter)
- [ ] 5.5 Task: notify (in-app notification + email)
- [ ] 5.6 PipelineRun state machine orchestrator

## Phase 6: Frontend (future)

- [ ] 6.1 Scaffold React/Vite project in `frontend/`
- [ ] 6.2 Login/register pages
- [ ] 6.3 Dashboard with application history
- [ ] 6.4 Profile editor
- [ ] 6.5 Portal config CRUD UI
- [ ] 6.6 Notification history UI

## Phase 7: Tests (future)

- [ ] 7.1 Unit: auth utils — hash comparison, token sign/verify
- [ ] 7.2 Unit: profile — CRUD logic
- [ ] 7.3 Integration: auth routes — register, login, token expiry
- [ ] 7.4 Integration: profile routes — CRUD, validation, unauthenticated rejection
- [ ] 7.5 E2E: register → login → create/update profile → verify JWT guard
- [ ] 7.6 Integration: scraper engine against Playwright (HTML fixtures)
