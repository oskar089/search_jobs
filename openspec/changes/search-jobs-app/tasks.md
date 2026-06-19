# Tasks: Search Jobs App — Foundation

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~800–1,300 |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: Scaffold + DB → PR 2: Auth → PR 3: Profile + Tests |
| Delivery strategy | ask-on-risk → stacked-to-main |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes (resolved → stacked-to-main)
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Scaffold + Prisma schema + DB client | PR 1 | Root configs, packages/database, initial migration |
| 2 | Auth helpers + API auth routes + middleware | PR 2 | packages/auth, apps/web auth routes |
| 3 | Profile service + API + all tests | PR 3 | packages/profile, profile routes, full test suite |

## Phase 1: Monorepo Scaffold + Database

- [x] 1.1 Root configs: `package.json` (workspaces), `turbo.json`, `tsconfig.json`, `.gitignore`, `.env.example`, `eslint.config.js`
- [ ] 1.2 Vitest config: `vitest.workspace.ts`, root `vitest.config.ts` — deferred to Test Phase (PR #3)
- [x] 1.3 `packages/database`: `package.json`, `prisma/schema.prisma` (all 8 models: User, Profile, Portal, StoredJob, Application, ScrapeSession, PipelineRun, Notification), `src/index.ts` (client singleton)
- [x] 1.4 Initial migration created at `prisma/migrations/20260619184417_init/` — apply requires PostgreSQL running locally (`docker compose up` or local install)

## Phase 2: Auth — Package + API Routes

- [ ] 2.1 `packages/auth`: `package.json`, `src/types.ts`, `src/password.ts` (hash/compare), `src/jwt.ts` (sign/verify/refresh)
- [ ] 2.2 `apps/web`: `package.json`, `next.config.ts`, `tsconfig.json`
- [ ] 2.3 `apps/web/src/middleware.ts` — JWT verification, route guard
- [ ] 2.4 API: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
- [ ] 2.5 API: `POST /api/auth/request-reset`, `POST /api/auth/confirm-reset`

## Phase 3: Profile — Package + API Routes

- [ ] 3.1 `packages/profile`: `package.json`, `src/types.ts`, `src/service.ts` (CRUD + validation)
- [ ] 3.2 API: `GET /api/profiles`, `PUT /api/profiles`

## Phase 4: Tests

- [ ] 4.1 Unit: auth package — hash comparison, token sign/verify, refresh rotation
- [ ] 4.2 Unit: profile package — CRUD logic, salary max>min rejection
- [ ] 4.3 Integration: auth routes — register (success, duplicate, weak pass), login (valid, invalid), token expiry
- [ ] 4.4 Integration: profile routes — CRUD, validation errors, unauthenticated rejection
- [ ] 4.5 E2E: register → login → create/update profile → verify JWT guard on protected routes
