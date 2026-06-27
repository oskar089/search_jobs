# Proposal: Security & Stability Hardening

## Intent

Eliminate 4 critical and 8 high-severity vulnerabilities found in the security review before production deployment. Migrate JWT auth from localStorage to httpOnly cookies. Harden infrastructure (Docker, nginx, SMTP) and scraper reliability.

## Scope

### In Scope
- Secrets: extract hardcoded creds, NeonDB string, JWT_SECRET to env/Docker secrets (C1, C3, C4, H7)
- Auth: JWT delivery via httpOnly/Secure/SameSite cookies, refresh token rotation, expiry 15min/7d (C2, H2, H5, H8)
- API: rate limiting on auth, file upload validation, CORS hardening (H1, H3, H6)
- Infra: nginx security headers, debug mode env-flag, Docker resource limits, real health checks, multi-stage Dockerfile
- Scraper: Playwright stealth addon, exponential backoff with jitter
- SMTP: enforce STARTTLS

### Out of Scope
- Low-severity findings (LV1-LV10)
- UI redesign, new features, functional changes
- Code refactoring outside security scope
- Database migration or schema changes

## Capabilities

### New Capabilities
- `secrets-management`: secure secret injection via env vars and Docker secrets
- `api-security`: rate limiting, file upload validation, CORS policy

### Modified Capabilities
- `user-auth`: JWT delivered via httpOnly cookie, refresh token rotation, shorter expiry, rate limiting on login/register
- `portal-scraping`: Playwright stealth mode, exponential backoff with jitter

## Approach

**Phase 1 — Secrets**: extract hardcoded values to `.env` via pydantic-settings; wire Docker secrets support; add `PRODUCTION` env flag.

**Phase 2 — Auth**: backend sets JWT as httpOnly/Secure/SameSite cookie on login; frontend removes localStorage logic; refresh rotation (old token blacklisted); access=15min, refresh=7d; rate limit via slowapi (5/min login, 10/min register).

**Phase 3 — API & Infra**: file upload validation (magic bytes, size cap); CORS single origin; nginx security headers; Docker resource limits + healthchecks; multi-stage Dockerfile; /health endpoint; STARTTLS on SMTP.

**Phase 4 — Scraper**: Playwright stealth addon; exponential backoff (1s, 2s, 4s, 8s, 16s + jitter).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/app/core/config.py` | Modified | Secrets from env, production flag |
| `backend/app/auth/` | Modified | JWT → httpOnly cookies, rotation |
| `backend/app/middleware/` | New | Rate limiter, CORS |
| `backend/app/scrapers/` | Modified | Stealth, backoff |
| `backend/app/api/` | Modified | Upload validation, /health |
| `frontend/src/lib/auth.ts` | Modified | Remove localStorage JWT |
| `docker-compose.yml` | Modified | Secrets, limits, healthchecks |
| `Dockerfile` | Modified | Multi-stage |
| `nginx.conf` | Modified | Security headers |
| `backend/.env.example` | New | Documented env vars |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| JWT cookie change breaks active sessions | Med | Support both header + cookie auth during transition |
| Rate limiting locks out legitimate user | Low | Conservative limits, configurable via env |
| Multi-stage Dockerfile breaks build | Low | Test build before deploy |
| Playwright stealth breaks on portal update | Med | Log failure, fallback to non-stealth |

## Rollback Plan

1. **Secrets**: old hardcoded values still in git history — revert commit
2. **JWT**: keep old `/auth/token` JSON endpoint alongside cookie; frontend falls back to localStorage if cookie auth fails
3. **Infra**: revert to single-stage Dockerfile, remove resource limits
4. **Full revert**: `git revert HEAD~N` on each PR

## Dependencies

- Python: `slowapi`, `python-multipart`, `pydantic-settings` (already present)
- Docker: BuildKit for multi-stage
- Playwright: `playwright-stealth` addon

## Success Criteria

- [ ] Secrets scan: zero hardcoded credentials in repo
- [ ] Auth: JWT never accessible via `localStorage` or `document.cookie` from JS
- [ ] Rate limiting: auth endpoints return 429 on >5 req/min from same IP
- [ ] nginx: A+ on securityheaders.com
- [ ] Docker: all services have CPU/memory limits and pass healthchecks
- [ ] Scraper: retries 5x with backoff on network failure
- [ ] Tests: existing auth tests pass with cookie flow
