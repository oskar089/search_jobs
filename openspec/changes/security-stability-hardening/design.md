# Design: Security & Stability Hardening

## Technical Approach

Hardening in 4 phases: Secrets → Auth → API & Infra → Scraper. Zero new DB schemas. Redis handles refresh rotation blacklist. pydantic-settings drives config with Docker secrets file fallback. Dual auth mode (cookie + Bearer) for zero-downtime JWT migration.

## Architecture Decisions

| Decision | Options | Choice | Rationale |
|----------|---------|--------|-----------|
| Config source | pydantic-settings / python-dotenv / environs | **pydantic-settings** | Already present in `config.py`; extend with `secrets_dir` for Docker secrets |
| Refresh blacklist | Redis SET / DB table / JWT jti | **Redis SET** | TTL-native (auto-expire with refresh TTL), no DB migration, sub-ms checks |
| Rate limit store | slowapi memory / Redis | **slowapi memory** | Single-instance deployment; Redis adds latency & infra complexity for rate data |
| JWT migration | Dual auth / flag flip / parallel endpoints | **Dual auth** | Backend accepts both cookie + Bearer; frontend removes localStorage, cookie auto-sent by browser |
| Stealth | playwright-stealth / custom JS / puppeteer-extra | **playwright-stealth** | Maintained 1st-party addon, injects via `add_init_script`, works in async API |
| File validation | middleware / decorator / inline | **Dedicated `validate_file` helper** | Reusable across routers, testable in isolation, no middleware overhead |

## Component Design

### Secrets Management (`backend/app/core/config.py`)
- Extend `Settings` with `model_config = SettingsConfigDict(secrets_dir="/run/secrets")`
- Remove hardcoded defaults for `database_url`, `jwt_secret`, `redis_url` — fail closed with `Field(validation_alias=...)`
- Add `validate_startup()` method: checks JWT_SECRET length (≥32), DATABASE_URL non-empty, known defaults rejected
- `APP_ENV` gates debug mode: `debug = Field(default=False, alias="APP_ENV")` with validator

### JWT Cookie Migration (`backend/app/auth/`)
- **Login**: set `Set-Cookie: access_token=<JWT>; HttpOnly; Secure; SameSite=Lax; Path=/api; Max-Age=900`
- **Get token from** `request.cookies`, fallback to `Authorization: Bearer` header
- **Refresh rotation**: `POST /auth/refresh` returns new access cookie + new refresh token in body; old refresh token added to Redis SET `refresh_blacklist:{user_id}` with TTL 7d
- **Logout**: `POST /auth/logout` blacklists current refresh token, clears cookie
- **Theft detection**: if blacklisted refresh used → clear ALL user refresh tokens (DEL `refresh_blacklist:{user_id}`), force re-login

### Rate Limiting (`backend/app/middleware/rate_limit.py`)
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=[])
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

# On routes:
@router.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, ...):
```

### File Upload Security (`backend/app/profiles/file_storage.py`)
- Add `validate_file(file: UploadFile)`: check allowed extensions → check content-type starts with `application/pdf` → read first 4 bytes for `%PDF` magic bytes
- Path traversal: sanitize `cv_id` via UUID validation (already UUID, but add guard on `serve()` filename param)
- Max size: keep existing 10MB guard

### API Security (`backend/app/main.py`)
- CORS: `cors_origins` as single origin string (not comma-list) for production
- Debug: `debug = settings.app_env == "development"`
- Health: `GET /health` probes DB (`SELECT 1`), Redis (`PING`), Celery (`inspect.ping()` with 3s timeout). Returns 503 on any failure.

### Infrastructure (`docker-compose.yml`)
- Multi-stage `Dockerfile`: `builder` stage (pip install + playwright install chromium), `runtime` stage (slim image, COPY `--from=builder`)
- Resource limits: backend (0.5 CPU / 512MB), celery-worker (1 CPU / 1GB), postgres (1 CPU / 512MB), redis (0.25 CPU / 256MB), frontend (0.25 CPU / 128MB)
- Health checks: backend (`/health`), redis (`redis-cli -a $REDIS_PASSWORD ping`), frontend (port 80)
- Redis password: `REDIS_PASSWORD` env, `redis:7-alpine` with `--requirepass $REDIS_PASSWORD`
- Internal network: `internal_network` with `external: false`; only backend + frontend expose ports
- nginx security headers: `add_header X-Frame-Options DENY; add_header X-Content-Type-Options nosniff; add_header Strict-Transport-Security "max-age=31536000; includeSubDomains"`

### Scraper Reliability (`backend/app/scrapers/engine.py`)
- Stealth: `await context.add_init_script(stealth_script)` from `playwright_stealth import stealth_async`
- Backoff: replace `2**attempt` sleep with `min(16000, 1000 * 2**attempt + random.uniform(0, 500))`
- Fallback: if stealth retries all fail → retry once without stealth, log warning

## Sequence Diagrams

```
Login → Cookie Set:
  Client                Backend                Redis
    │── POST /auth/login──│                     │
    │                     │─ verify password    │
    │                     │─ create access+refresh JWT
    │                     │────────────────────> SET refresh_blacklist:{uid}:old (TTL 7d) [future use]
    │← Set-Cookie + refresh_token body
    │

Refresh Rotation:
  Client                Backend                Redis
    │── POST /auth/refresh──│                     │
    │   (cookie: expired)   │                     │
    │   (body: refresh_token)│                    │
    │                     │─ check refresh in blacklist?
    │                     │────────────────────> SISMEMBER refresh_blacklist:{uid}
    │                     │<─── 0 (not blacklisted)
    │                     │─ create new access+refresh JWTs
    │                     │────────────────────> SADD refresh_blacklist:{uid}:old (TTL 7d)
    │← Set-Cookie + new refresh_token body
    │

File Upload Validation:
  Client                Backend
    │── POST /cv/upload──│
    │   (file: .exe)     │
    │                     │─ validate_file():
    │                     │  1. extension: .exe → reject
    │                     │  2. content-type: ? → reject
    │                     │  3. magic bytes: ? → reject
    │← 422 Only PDF files │
```

## Data Model Changes

**No new DB tables.** Refresh blacklist uses Redis:

| Redis Key | Type | TTL | Value |
|-----------|------|-----|-------|
| `refresh_blacklist:{user_id}` | SET | 7d | list of blacklisted refresh JWT hashes |
| `rate_limit:{ip}:login` | String (auto by slowapi) | 1min | counter |
| `rate_limit:{ip}:register` | String (auto by slowapi) | 1min | counter |

## Configuration Changes

| Env Var | Required | Default | Description |
|---------|----------|---------|-------------|
| `JWT_SECRET` | Yes | — | ≥32 chars, no default |
| `DATABASE_URL` | Yes | — | No default |
| `JWT_ACCESS_EXPIRE_MINUTES` | No | 15 | Access token TTL |
| `JWT_REFRESH_EXPIRE_DAYS` | No | 7 | Refresh token TTL |
| `RATE_LIMIT_LOGIN` | No | 5 | Login attempts/min/IP |
| `RATE_LIMIT_REGISTER` | No | 10 | Registration attempts/min/IP |
| `REDIS_PASSWORD` | No | — | Redis auth password |
| `APP_ENV` | No | `development` | Gates debug mode |
| `CORS_ORIGINS` | No | `http://localhost:5173` | Single allowed origin |

## Migration Strategy

1. **Deploy config changes first** (pydantic-settings + Docker secrets fallback). No runtime impact.
2. **Deploy dual-auth backend** — accepts both cookies and Bearer headers. Existing frontend continues working.
3. **Deploy frontend changes** — remove localStorage JWT, rely on cookies. Sessions survive transition because `/auth/me` still works via cookie.
4. **Remove Bearer fallback** after one release cycle (optional — low risk to keep).
5. **Infra changes** (Docker limits, health checks, nginx headers) deploy independently — no user impact.
6. **Scraper changes** deploy independently — no user impact.

**Rollback**: revert any PR. Dual auth means old frontend still works with new backend and vice versa.

## Open Questions

- [ ] Celery ping timeout value for `/health` — 3s enough for busy worker?
- [ ] Rate limit by IP behind Docker: use `X-Forwarded-For` header or `get_remote_address` (which checks nginx proxy)?
- [ ] SMTP STARTTLS: use `smtplib.SMTP.starttls()` or async via `aiosmtplib` (if available)?
