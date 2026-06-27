# Tasks: Security & Stability Hardening

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~630 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (Secrets + Infra foundations) → PR 2 (JWT Cookie Auth) → PR 3 (API Security + Infra Docker) → PR 4 (Scraper) |
| Delivery strategy | ask-on-risk |
| Chain strategy | feature-branch-chain |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Secrets extraction + infra foundations | PR 1 | main base; .env.example, config refactor, docker-compose mounts, network isolation |
| 2 | JWT Cookie Auth (backend + frontend) | PR 2 | main base; dual-auth, cookie middleware, refresh rotation, frontend localStorage removal |
| 3 | API Security + Infra hardening | PR 3 | main base; rate limiting, file validation, CORS, multi-stage Docker, nginx headers |
| 4 | Scraper reliability | PR 4 | main base; stealth injection, backoff with jitter, fallback logic |

## Phase 1: Secrets Extraction

- [x] 1.1 Refactor `backend/app/config.py`: remove hardcoded defaults for `database_url`, `jwt_secret`, `redis_url`; add `secrets_dir` via `SettingsConfigDict`; add `validate_startup()` method
- [x] 1.2 Add startup validation hook in `backend/app/main.py` — call `settings.validate_startup()` before `FastAPI()` init
- [x] 1.3 Create `backend/.env.example` with all required env vars documented and placeholders marked invalid for production
- [x] 1.4 Update `docker-compose.yml`: drop default secrets, wire `REDIS_PASSWORD`, add `/run/secrets` mount to backend/celery services

## Phase 2: JWT Cookie Auth

- [ ] 2.1 Cookie auth middleware: read `request.cookies["access_token"]` before `Authorization` header in `get_token_from_header`
- [ ] 2.2 Login: set `Set-Cookie` httpOnly/Secure/SameSite with 15min access token; return refresh token in response body
- [ ] 2.3 Refresh rotation: `POST /auth/refresh` blacklists old refresh via Redis `SADD refresh_blacklist:{uid}` 7d TTL; issues new cookie + refresh body
- [ ] 2.4 Logout: `POST /auth/logout` — blacklist current refresh, clear cookie with `Max-Age=0`
- [ ] 2.5 Theft detection: if blacklisted refresh reused (`SISMEMBER`), `DEL refresh_blacklist:{uid}` — force re-login
- [ ] 2.6 Frontend: remove `localStorage` `"token"` read/write from `AuthContext.tsx`
- [ ] 2.7 Frontend: remove `Authorization: Bearer` header from `api.ts` (cookies auto-sent)
- [ ] 2.8 Tests: cookie auth flow, refresh rotation, logout, stolen token detection

## Phase 3: API Security

- [ ] 3.1 Add `slowapi` `Limiter` middleware in `backend/app/main.py` with 429 handler
- [x] 3.2 Apply `@limiter.limit("5/minute")` on login, `"10/minute"` on register
- [x] 3.3 Account lockout: 5 consecutive failed logins → 15min Redis lockout key `lockout:{email}`
- [ ] 3.4 Add `validate_file()` helper: check extension → content-type → magic bytes for `%PDF-`
- [ ] 3.5 Path traversal guard on CV download: validate UUID format on `serve()` filename param
- [ ] 3.6 CORS: single origin from env, restrict methods to `GET,POST,PUT,DELETE`, headers to `Content-Type,Authorization`
- [ ] 3.7 Debug mode: disabled unless `APP_ENV == "development"`
- [x] 3.8 Rewrite `/health`: probe DB (`SELECT 1`), Redis (`PING`), Celery (`inspect.ping()` 3s timeout); 503 on any failure
- [ ] 3.9 Tests: rate limiting returns 429, file validation rejects non-PDF, health check reports unhealthy

## Phase 4: Infra Hardening

- [x] 4.1 Multi-stage `backend/Dockerfile`: `builder` stage (pip + playwright install chromium), `runtime` stage (slim, COPY `--from=builder`)
- [x] 4.2 CPU/memory limits on all services: backend (0.5/512MB), celery-worker (1/1GB), postgres (1/512MB), redis (0.25/256MB), frontend (0.25/128MB)
- [x] 4.3 Health checks for backend (`/health`), celery-worker, celery-beat; update redis healthcheck with `-a $REDIS_PASSWORD`
- [x] 4.4 Redis password auth: `--requirepass $REDIS_PASSWORD`, update `REDIS_URL` in all services
- [x] 4.5 Internal Docker network: `internal_network` with no public ports for DB/Redis; only backend+frontend expose ports
- [x] 4.6 nginx security headers: CSP, `X-Frame-Options DENY`, `X-Content-Type-Options nosniff`, HSTS `31536000; includeSubDomains`
- [x] 4.7 SMTP: enforce STARTTLS in notification service; add startup connectivity check with warning log

## Phase 5: Scraper Reliability

- [ ] 5.1 Extract stealth script into shared `backend/app/scrapers/stealth.py` module using `playwright_stealth.stealth_async`
- [ ] 5.2 Inject stealth in `ScraperEngine._scrape_page()` via `context.add_init_script()` before navigation
- [ ] 5.3 Exponential backoff with jitter: `min(16000, 1000*2^attempt + random.uniform(0,500))` replacing `2**attempt`
- [ ] 5.4 Fallback: after all stealth retries fail, retry once without stealth, log warning
- [ ] 5.5 Tests: backoff values with mocked sleep, jitter clamping, stealth fallback path
