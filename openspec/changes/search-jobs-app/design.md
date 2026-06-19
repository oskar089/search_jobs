# Design: Search Jobs App — Python Stack

## Technical Approach

Python backend (FastAPI) with a decoupled React/Vite frontend. SQLAlchemy async + Alembic for database persistence over existing Neon PostgreSQL. Celery + Redis orchestrates the background worker pipeline (scrape → match → apply → notify). Playwright (Python binding) handles both scraping and auto-application browser automation. Pydantic v2 for request/response validation. JWT auth via python-jose + passlib (bcrypt). httpx for outbound HTTP. LLM API (OpenAI/Claude) generates cover letters per posting language.

## Architecture Decisions

### Web framework

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Django + DRF | Heavy, opinionated, unnecessary for mostly-async API | ❌ |
| FastAPI | Native async, Pydantic v2 built-in, auto OpenAPI docs, modern async SQLAlchemy | ✅ |

### Database layer

| Option | Tradeoff | Decision |
|--------|----------|----------|
| SQLAlchemy sync + psycopg2 | Simpler but blocks on I/O; can't use `async for` in routes | ❌ |
| SQLAlchemy async + asyncpg | Native async, matches FastAPI event loop, Alembic supports async migrations | ✅ |

### Auth strategy

| Option | Tradeoff | Decision |
|--------|----------|----------|
| FastAPI OAuth2 with JWT Bearer | Built-in `OAuth2PasswordBearer`, works with OpenAPI docs UI | ✅ |
| Session-based (starlette sessions) | Stateful, requires Redis or DB store, more infra | ❌ |

### Worker orchestration

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Celery + Redis | Mature, reliable, beat scheduler, retries, task monitoring (Flower) | ✅ |
| DB polling loop | Simpler (no Redis), but no built-in retry, scheduling, or monitoring | ❌ |
| Arq | Lighter than Celery, Redis-based, native async | Consider for future — less ecosystem |

### Scraping architecture

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Hardcoded scrapers | Not pluggable; users can't add custom portals | ❌ |
| DB-stored selectors | PortalConfig table stores CSS/XPath JSON; built-in = seeded rows; user portals via UI | ✅ |

### Anti-detection approach

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Random click sequences | More human-like but fragile to layout changes | ❌ |
| Wait + retry with human delays | Good balance of reliability and simplicity | ✅ |

### Async client for outbound HTTP

| Option | Tradeoff | Decision |
|--------|----------|----------|
| httpx | Native async, matches FastAPI event loop, client/server both async | ✅ |
| requests | Sync-only, blocks event loop, needs thread pool wrapper | ❌ |

### CLI / dev tooling

| Option | Tradeoff | Decision |
|--------|----------|----------|
| pip + requirements.txt | Universal, CI-friendly, no extra tooling | ✅ (primary) |
| Poetry | Lockfile, dependency resolution, but extra tool to install | Optional — `pyproject.toml` supports both |

### Testing

| Option | Tradeoff | Decision |
|--------|----------|----------|
| pytest + pytest-asyncio | Standard for FastAPI projects, async test support, fixture system | ✅ |
| unittest | No async support, more boilerplate | ❌ |

## Data Flow

```
                          ┌──────────────────┐
                          │   User Dashboard  │
                          │   (React/Vite)    │
                          └────────┬─────────┘
                                   │ REST (/api/*)
                                   ▼
┌──────────────────────────────────────────────────────┐
│                  FastAPI Backend                       │
│  /api/auth/*  /api/portals/*  /api/profiles/*          │
│  /api/applications/*  /api/notifications/*             │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│              SQLAlchemy (async) + PostgreSQL            │
│  Users, Profiles, Portals, StoredJobs, Applications,   │
│  PipelineRuns, Notifications, ScrapeSessions           │
└────────────────────────┬───────────────────────────────┘
                         │ Celery task
                         ▼
┌──────────────────────────────────────────────────────┐
│           Celery Worker (Redis broker)                 │
│  ┌────────┐  ┌────────────┐  ┌────────┐  ┌────────┐  │
│  │Scrape  │→ │Match+Score │→ │Apply   │→ │Notify  │  │
│  │Playwr. │  │(≥threshold)│  │Playwr. │  │Email+  │  │
│  │+BS4    │  │            │  │+LLM CL │  │In-App  │  │
│  └────────┘  └────────────┘  └────────┘  └────────┘  │
└──────────────────────────────────────────────────────┘
```

**Scrape → Match pipeline detail:**

```
Celery beat triggers PipelineRun → status='pending'
  → Task 1 (scrape): Load PortalConfig selectors from DB
    → Playwright opens portal URL, extracts job cards
    → Parse each card using selectors, save StoredJobs
  → Task 2 (match): Load User Profile, score each StoredJob
    → If score ≥ threshold → create Application (pending)
  → Task 3 (apply): Playwright navigates to apply page
    → Generate cover letter via LLM API (formal, matches posting language)
    → Fill form, submit, update Application status
  → Task 4 (notify): Create Notification (in-app row + email send)
  → Mark PipelineRun status = 'completed'
```

## File Changes — Python project structure (all files are new)

### Backend (`backend/`)

| File | Action | Description |
|------|--------|-------------|
| `backend/pyproject.toml` | Create | Project metadata, dependencies, tool config |
| `backend/requirements.txt` | Create | Pinned deps for pip install |
| `backend/alembic.ini` | Create | Alembic configuration (async) |
| `backend/alembic/env.py` | Create | Async Alembic environment |
| `backend/alembic/versions/20260619_184500_init_all_tables.py` | Create | Initial migration — all 8 tables |
| `backend/app/__init__.py` | Create | Package marker |
| `backend/app/main.py` | Create | FastAPI app factory, CORS, router registration |
| `backend/app/config.py` | Create | pydantic-settings Settings class |
| `backend/app/database.py` | Create | Async engine, session factory, Base, get_session dependency |
| `backend/app/models/__init__.py` | Create | Re-export all models |
| `backend/app/models/user.py` | Create | User model (id, email, password_hash, name, timestamps) |
| `backend/app/models/profile.py` | Create | Profile model (tech_stack, target_roles, locations, etc.) |
| `backend/app/models/portal.py` | Create | Portal model (selectors JSON, scrub config) |
| `backend/app/models/job.py` | Create | StoredJob model (scraped postings) |
| `backend/app/models/application.py` | Create | Application model (status, match_score, cover_letter) |
| `backend/app/models/scrape_session.py` | Create | ScrapeSession model (per-portal scrape runs) |
| `backend/app/models/pipeline_run.py` | Create | PipelineRun model (orchestration state) |
| `backend/app/models/notification.py` | Create | Notification model (in-app + email) |
| `backend/app/auth/__init__.py` | Create | Package marker |
| `backend/app/auth/router.py` | Create | POST /register, POST /login, GET /me + JWT dependencies |
| `backend/app/auth/schemas.py` | Create | Pydantic schemas: RegisterRequest, LoginRequest, TokenResponse, UserResponse |
| `backend/app/auth/utils.py` | Create | JWT sign/verify (python-jose), password hashing (passlib bcrypt) |
| `backend/app/profiles/__init__.py` | Create | Package marker |
| `backend/app/profiles/router.py` | Create | GET/PUT /profiles — CRUD for user profile |
| `backend/app/profiles/schemas.py` | Create | Pydantic schemas: ProfileResponse, ProfileUpdate |
| `backend/app/portals/` | Create | Portal config CRUD routes (future) |
| `backend/app/scrapers/` | Create | Scraper engine + built-in configs (future) |
| `backend/app/matching/` | Create | Match scoring engine (future) |
| `backend/app/cover_letter/` | Create | LLM cover letter generation (future) |
| `backend/app/applicator/` | Create | Auto-application browser automation (future) |
| `backend/app/notifications/` | Create | Email + in-app notification dispatch (future) |

### Frontend (`frontend/`)

| File | Action | Description |
|------|--------|-------------|
| `frontend/` | Create (empty) | React/Vite project — will be scaffolded in a later phase |

### Root

| File | Action | Description |
|------|--------|-------------|
| `.gitignore` | Updated | Python ignores (__pycache__, .venv, *.pyc) + existing Node ignores |
| `.env` | Updated | Python-style env vars (asyncpg URL, pydantic-settings compat) |
| `.env.example` | Updated | Template env vars for Python stack |

## Database Schema (SQLAlchemy)

All 8 tables match the existing Neon database schema (originally created via Prisma).

### user

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default uuid4 |
| email | VARCHAR(255) | UNIQUE, NOT NULL, indexed |
| password_hash | VARCHAR(255) | NOT NULL |
| name | VARCHAR(255) | nullable |
| created_at | TIMESTAMPTZ | NOT NULL, default now() |
| updated_at | TIMESTAMPTZ | NOT NULL, default now(), on update now() |

### profile

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default uuid4 |
| user_id | UUID | UNIQUE, NOT NULL, FK → user(id) ON DELETE CASCADE |
| target_roles | TEXT[] | NOT NULL, default [] |
| tech_stack | TEXT[] | NOT NULL, default [] |
| experience_level | VARCHAR(50) | NOT NULL |
| min_salary | INTEGER | nullable |
| max_salary | INTEGER | nullable |
| locations | TEXT[] | NOT NULL, default [] |
| remote_only | BOOLEAN | NOT NULL, default false |
| languages | TEXT[] | NOT NULL, default [] |
| is_active | BOOLEAN | NOT NULL, default true |
| created_at | TIMESTAMPTZ | NOT NULL, default now() |
| updated_at | TIMESTAMPTZ | NOT NULL, default now(), on update now() |

### portal

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default uuid4 |
| user_id | UUID | nullable, FK → user(id) ON DELETE SET NULL |
| name | VARCHAR(255) | NOT NULL |
| base_url | VARCHAR(500) | NOT NULL |
| job_listing_url | VARCHAR(500) | NOT NULL |
| selectors | JSONB | NOT NULL |
| is_builtin | BOOLEAN | NOT NULL, default false |
| is_enabled | BOOLEAN | NOT NULL, default true |
| is_verified | BOOLEAN | NOT NULL, default false |
| scrape_interval_min | INTEGER | NOT NULL, default 60 |
| created_at | TIMESTAMPTZ | NOT NULL, default now() |
| updated_at | TIMESTAMPTZ | NOT NULL, default now(), on update now() |

### stored_job

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default uuid4 |
| external_id | VARCHAR(255) | nullable |
| portal_id | UUID | NOT NULL, FK → portal(id) ON DELETE CASCADE |
| title | VARCHAR(500) | NOT NULL |
| company | VARCHAR(255) | NOT NULL |
| location | VARCHAR(255) | nullable |
| description | TEXT | NOT NULL |
| url | VARCHAR(1000) | NOT NULL |
| salary_range | VARCHAR(255) | nullable |
| posted_at | TIMESTAMPTZ | nullable |
| scraped_at | TIMESTAMPTZ | NOT NULL, default now() |
| language | VARCHAR(10) | NOT NULL, default 'en' |
| **Unique** | (portal_id, external_id) | |

### application

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default uuid4 |
| user_id | UUID | NOT NULL, FK → user(id) ON DELETE CASCADE |
| stored_job_id | UUID | NOT NULL, FK → stored_job(id) ON DELETE CASCADE |
| pipeline_run_id | UUID | nullable, FK → pipeline_run(id) ON DELETE SET NULL |
| status | VARCHAR(50) | NOT NULL, default 'pending' |
| match_score | FLOAT | nullable |
| cover_letter_generated | BOOLEAN | NOT NULL, default false |
| cover_letter_text | TEXT | nullable |
| submitted_at | TIMESTAMPTZ | nullable |
| error_message | TEXT | nullable |
| created_at | TIMESTAMPTZ | NOT NULL, default now() |
| updated_at | TIMESTAMPTZ | NOT NULL, default now(), on update now() |

### scrape_session

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default uuid4 |
| portal_id | UUID | NOT NULL, FK → portal(id) ON DELETE CASCADE |
| user_id | UUID | nullable |
| status | VARCHAR(50) | NOT NULL |
| jobs_found | INTEGER | NOT NULL, default 0 |
| error_message | TEXT | nullable |
| started_at | TIMESTAMPTZ | NOT NULL, default now() |
| completed_at | TIMESTAMPTZ | nullable |

### pipeline_run

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default uuid4 |
| user_id | UUID | NOT NULL, FK → user(id) ON DELETE CASCADE |
| portal_id | UUID | nullable |
| status | VARCHAR(50) | NOT NULL, default 'pending' |
| trigger | VARCHAR(50) | NOT NULL, default 'manual' |
| steps | JSONB | nullable |
| error_step | VARCHAR(50) | nullable |
| error_msg | TEXT | nullable |
| created_at | TIMESTAMPTZ | NOT NULL, default now() |
| completed_at | TIMESTAMPTZ | nullable |

### notification

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default uuid4 |
| user_id | UUID | NOT NULL, FK → user(id) ON DELETE CASCADE |
| application_id | UUID | nullable, FK → application(id) ON DELETE SET NULL |
| type | VARCHAR(50) | NOT NULL |
| channel | VARCHAR(20) | NOT NULL, default 'in_app' |
| title | VARCHAR(255) | NOT NULL |
| body | TEXT | NOT NULL |
| is_read | BOOLEAN | NOT NULL, default false |
| sent_at | TIMESTAMPTZ | NOT NULL, default now() |
| read_at | TIMESTAMPTZ | nullable |

## Interfaces / Contracts

### Auth dependencies

```python
# Dependency: extracts Bearer token, decodes JWT, returns user_id
async def get_current_user_id(token: str = Depends(get_token_from_header)) -> str

# Dependency: extracts raw Bearer token from Authorization header
async def get_token_from_header(authorization: str = Header(...)) -> str
```

### Auth schemas (Pydantic)

```python
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: str
    email: str
    name: str | None = None
    model_config = {"from_attributes": True}
```

### Profile schemas (Pydantic)

```python
class ProfileResponse(BaseModel):
    id: str
    user_id: str
    target_roles: list[str]
    tech_stack: list[str]
    experience_level: str
    min_salary: int | None = None
    max_salary: int | None = None
    locations: list[str]
    remote_only: bool
    languages: list[str]
    is_active: bool
    model_config = {"from_attributes": True}

class ProfileUpdate(BaseModel):
    target_roles: list[str] | None = None
    tech_stack: list[str] | None = None
    experience_level: str | None = None
    ...
```

### ScraperEngine (future)

```python
# backend/app/scrapers/
@dataclass
class PortalSelectors:
    job_card: str       # CSS/XPath for each job card container
    title: str
    company: str
    location: str
    description: str
    url: str
    salary: str | None
    posted_date: str | None
    apply_button: str | None

@dataclass
class ScrapedJob:
    external_id: str | None
    title: str
    company: str
    location: str | None
    description: str
    url: str
    salary_range: str | None
    posted_at: datetime | None
    language: str
```

### MatcherEngine (future)

```python
# backend/app/matching/
@dataclass
class MatchResult:
    score: float  # 0–100
    factors: dict  # {"keyword_match": float, "role_match": float, ...}
```

### CoverLetterGenerator (future)

```python
# backend/app/cover_letter/
@dataclass
class CoverLetterInput:
    job_title: str
    company: str
    job_description: str
    profile: dict  # target_roles, tech_stack, experience_level
    language: str  # target language for the letter
```

### Notifier (future)

```python
# backend/app/notifications/
@dataclass
class NotificationInput:
    user_id: str
    application_id: str | None
    type: str  # application_submitted | application_failed | portal_error | match_found
    title: str
    body: str
    channels: list[str]  # ["in_app"] | ["email"] | ["in_app", "email"]
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Scoring functions, prompt building, selector parsing | pytest — pure function tests, no external deps |
| Unit | JWT auth helpers, password hashing | pytest — token sign/verify, hash comparison |
| Integration | Scraper engine against Playwright browser | pytest + Playwright — launch headless, parse known HTML fixtures |
| Integration | SQLAlchemy CRUD operations | pytest + test database (asyncpg via testcontainers or SQLite aiosqlite) |
| Integration | LLM cover letter generation | Mock API responses (httpx mock / respx) — test prompt construction, not the API |
| E2E | Full pipeline: scrape → match → apply → notify | pytest + Playwright — mock portal HTML, intercept LLM calls, assert DB rows |
| E2E | User registration, login, portal config, dashboard | pytest + httpx AsyncClient (FastAPI TestClient) — endpoint-level flows |
| Dry-run test | User-configured portal selectors | Scraper engine in test mode: returns parsed jobs without persisting |

## Migration / Rollout

1. **Phase 0 — Scaffold (current)**: Delete Node/TS artifacts, create Python project structure, SQLAlchemy models + Alembic migration, FastAPI skeleton with config, auth module, profiles module.
2. **Phase 1 — Portal Config + Scraper**: `backend/app/portals/` + `backend/app/scrapers/` with engine + 4 built-in configs, dry-run test mode, portal CRUD API.
3. **Phase 2 — Worker Pipeline**: Celery setup with Redis, scrape → match → apply → notify tasks, PipelineRun state machine.
4. **Phase 3 — Frontend**: React/Vite scaffold, dashboard UI, auth login/register pages, profile editor.
5. **Phase 4 — Polish**: Scheduled scraping (Celery beat), error handling, rate limiting, anti-detection delays.
6. **Phase 5 — Tests**: Full test suite (unit, integration, E2E).

## Open Questions

- [ ] Email provider: SMTP (aiosmtplib) vs transactional API (Resend/SendGrid)? aiosmtplib is async-native; Resend has best DX but needs API key.
- [ ] Built-in portal selectors: seed via Alembic migration (data migration) or load from code? Code-loading means updates via package releases; DB seeding means users get updates through migrations.
- [ ] Anti-detection strategy for Playwright Python: `playwright-stealth` pip package vs manual randomization? Stealth plugin has fewer updates in Python ecosystem.
- [ ] Match threshold: configurable per user or global default (e.g., 60/100)?
