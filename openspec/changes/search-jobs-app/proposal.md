# Proposal: Search Jobs App — Automated Job Search Engine

## Intent

Automate the full job search pipeline: scrape multiple portals, match postings against user profiles, auto-apply, and generate personalized AI cover letters. Currently manual — candidates browse, filter, apply, and write cover letters by hand. This app eliminates repetitive work for job seekers managing multiple applications across platforms.

## Scope

### In Scope

- Multi-user auth with per-user profiles and settings
- Scraping: built-in selectors for LinkedIn, Infojobs, Computrabajo, Bumeran; users can configure additional portals via CSS/XPath selectors
- Portal config UI: users add/remove/modify portals to scrape per their needs
- Profile-driven job matching with auto-application
- AI cover letter generation (dynamic language, formal tone)
- Email + dashboard notifications with full history
- Python backend (FastAPI) with Playwright + BeautifulSoup
- SQLAlchemy + Alembic for database (using existing Neon PostgreSQL)

### Out of Scope

- Mobile apps (web dashboard only, responsive)
- Third-party job board APIs (scraping only — no official API integrations)
- Manual review before auto-apply (fully automated by design)
- Cover letter editing before sending (generated and sent inline)
- Social login (email/password auth only)
- Intelligent portal detection (user must configure selectors for custom portals)

## Capabilities

### New Capabilities

- `user-auth`: Registration, login, session management, password reset
- `profile-management`: Tech stack, experience, preferences, target roles
- `portal-scraping`: Pluggable scraping system — built-in selectors for 4 portals, user-configurable for any job portal via CSS/XPath
- `portal-config`: UI for users to add, edit, enable/disable portals with custom selectors and scraping rules
- `job-matching`: Match scoring against user profile, triggers auto-apply
- `ai-cover-letter`: Dynamically generates cover letters via LLM API
- `auto-application`: Submits applications via browser automation
- `notification`: Email delivery + in-app notification history
- `dashboard`: History viewer, stats, configuration UI

### Modified Capabilities

None — first change on empty project.

## Approach

Python monorepo with FastAPI backend. Playwright (Python binding) handles scraping and auto-application; Celery + Redis orchestrates the worker pipeline (scrape→match→apply→notify). SQLAlchemy + Alembic for database access and migrations over PostgreSQL (Neon). LLM API (OpenAI/Claude) generates cover letters per job posting language. Frontend dashboard in React/Vite, fully decoupled from the Python backend via REST API.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/app/auth/` | New | User registration, login, JWT sessions |
| `backend/app/scrapers/` | New | Pluggable scraping engine via Playwright |
| `backend/app/portal_config/` | New | Portal config CRUD + dry-run |
| `backend/app/matching/` | New | Profile-job match engine |
| `backend/app/cover_letter/` | New | AI prompt construction and generation |
| `backend/app/applicator/` | New | Auto-submit via Playwright |
| `backend/app/notifications/` | New | Email + in-app notifications |
| `backend/app/models/` | New | SQLAlchemy models |
| `backend/alembic/` | New | Database migrations |
| `frontend/` | New | React/Vite dashboard |
| `infra/` | New | Docker, CI/CD config |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Portal layout changes break built-in scrapers | High | Circuit breakers, alerts, per-portal tests |
| User-configured portals break easily (bad selectors) | High | Dry-run/test mode before enabling, error rate alerts |
| Auto-apply detected as spam | Med | Human-like delays, session rotation, fingerprint mitigation |
| LLM cost at scale | Med | Token budgeting, caching, fallback templates |
| Profile data PII exposure | Low | Encrypted storage, env-based secrets, no PII in logs |

## Rollback Plan

- Database: Alembic migrations are reversible — `alembic downgrade -1` to roll back
- No production data loss risk during early dev (no real users yet)
- Git revert change branch, drop deployment, re-scaffold
- Scrapers: feature-flagged — disable per portal without full rollback

## Dependencies

- Python 3.12+ / FastAPI
- Playwright (Python binding) + BeautifulSoup
- Celery + Redis (worker pipeline)
- LLM API key (OpenAI or Claude)
- Neon PostgreSQL (existing)
- SMTP server (email notifications)

## Success Criteria

- [ ] User can register, log in, and configure a search profile
- [ ] Built-in scrapers for 4 portals (LinkedIn, Infojobs, Computrabajo, Bumeran) return structured postings
- [ ] User can add a custom portal with CSS/XPath selectors and see results
- [ ] Dry-run mode validates user portal configs before enabling
- [ ] Match engine triggers auto-apply above configurable threshold
- [ ] AI cover letter generated per posting language with formal tone
- [ ] Notification sent (email + dashboard) for each application
- [ ] Dashboard shows application history with status and cover letter
