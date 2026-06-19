# Design: Search Jobs App

## Technical Approach

Monorepo (npm workspaces + Turborepo) with three runtimes: Next.js web app (dashboard + API routes), background worker (scrape→match→apply→notify pipeline as a long-lived Node.js process), and shared packages (database client, scraper engine, matcher, cover letter generator, notifier). Prisma + PostgreSQL for persistence. Playwright for both scraping and application automation. JWT auth (bcrypt + jsonwebtoken) — no framework coupling, works for both web and worker.

## Architecture Decisions

### Monorepo layout

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Single Next.js app | API + worker in same process, no separation | ❌ |
| Separate repos | Shared types/DB client versioning overhead | ❌ |
| npm workspaces monorepo | Shared packages, independent deploy, single repo | ✅ |

### Auth strategy

| Option | Tradeoff | Decision |
|--------|----------|----------|
| NextAuth.js | Heavy for email-only; ties to Next.js runtime | ❌ |
| Direct JWT | Works in Next.js API + worker; bcrypt + jsonwebtoken | ✅ |

### Worker orchestration

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Bull/Redis queue | Ops overhead (Redis); overkill for personal tool | ❌ |
| DB polling loop | Simple; no extra infra; Prisma polls `pipeline_runs` table | ✅ |

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

## Data Flow

```
                         ┌──────────────────┐
                         │   User Dashboard  │
                         │   (Next.js App)   │
                         └────────┬─────────┘
                                  │ REST (/api/*)
                                  ▼
┌──────────────────────────────────────────────────────┐
│                   Next.js API Routes                   │
│  /api/auth/*  /api/portals/*  /api/profiles/*          │
│  /api/applications/*  /api/notifications/*             │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│                  Prisma (PostgreSQL)                    │
│  Users, Profiles, Portals, StoredJobs, Applications,   │
│  PipelineRuns, Notifications                           │
└────────────────────────┬───────────────────────────────┘
                         │ poll
                         ▼
┌──────────────────────────────────────────────────────┐
│                 Worker (Node.js process)                │
│  ┌────────┐  ┌────────────┐  ┌────────┐  ┌────────┐  │
│  │Scrape  │→ │Match+Score │→ │Apply   │→ │Notify  │  │
│  │Playwr. │  │(≥threshold)│  │Playwr. │  │Email+  │  │
│  │SaveJobs│  │            │  │+LLM CL │  │In-App  │  │
│  └────────┘  └────────────┘  └────────┘  └────────┘  │
└──────────────────────────────────────────────────────┘
```

**Scrape → Match pipeline detail:**

```
Worker polls pipeline_runs WHERE status='pending'
  → Step 1: Load PortalConfig selectors from DB
  → Step 2: Playwright opens portal URL, extracts job cards
  → Step 3: Parse each card using selectors, save StoredJobs
  → Step 4: Load User Profile, score each StoredJob
  → Step 5: If score ≥ threshold → create Application (pending)
  → Step 6: Playwright navigates to apply page, fills form
  → Step 7: Generate cover letter via LLM (formal, language matches posting)
  → Step 8: Submit, update Application status
  → Step 9: Create Notification (in-app row + email send)
  → Step 10: Update PipelineRun status = 'completed'
```

## File Changes (greenfield — all files are new)

| File | Action | Description |
|------|--------|-------------|
| **Apps** | | |
| `apps/web/package.json` | Create | Next.js app dependencies |
| `apps/web/next.config.ts` | Create | Next.js configuration |
| `apps/web/src/app/layout.tsx` | Create | Root layout with auth check |
| `apps/web/src/app/page.tsx` | Create | Landing/redirect page |
| `apps/web/src/app/login/page.tsx` | Create | Login form |
| `apps/web/src/app/register/page.tsx` | Create | Registration form |
| `apps/web/src/app/dashboard/page.tsx` | Create | Main dashboard with stats |
| `apps/web/src/app/dashboard/profile/page.tsx` | Create | Profile editor |
| `apps/web/src/app/dashboard/portals/page.tsx` | Create | Portal config list + CRUD |
| `apps/web/src/app/dashboard/portals/new/page.tsx` | Create | Add custom portal form |
| `apps/web/src/app/dashboard/portals/[id]/test/page.tsx` | Create | Dry-run/test portal |
| `apps/web/src/app/dashboard/applications/page.tsx` | Create | Application history |
| `apps/web/src/app/dashboard/notifications/page.tsx` | Create | Notification history |
| `apps/web/src/app/api/auth/login/route.ts` | Create | POST — authenticate, return JWT |
| `apps/web/src/app/api/auth/register/route.ts` | Create | POST — create user |
| `apps/web/src/app/api/auth/me/route.ts` | Create | GET — current user info |
| `apps/web/src/app/api/portals/route.ts` | Create | GET list, POST create portal |
| `apps/web/src/app/api/portals/[id]/route.ts` | Create | GET/PUT/DELETE portal config |
| `apps/web/src/app/api/portals/[id]/test/route.ts` | Create | POST dry-run scrape |
| `apps/web/src/app/api/profiles/route.ts` | Create | GET/PUT user profile |
| `apps/web/src/app/api/applications/route.ts` | Create | GET list applications |
| `apps/web/src/app/api/notifications/route.ts` | Create | GET notifications, PATCH read |
| `apps/web/src/app/api/pipeline/trigger/route.ts` | Create | POST trigger manual pipeline run |
| `apps/web/src/middleware.ts` | Create | Edge middleware — JWT verification, route guard |
| `apps/web/src/lib/auth.ts` | Create | JWT sign/verify helpers, password hashing |
| `apps/web/src/lib/api-client.ts` | Create | Typed fetch wrapper |
| `apps/web/src/components/ui/*.tsx` | Create | Button, Card, Input, Table, Modal — base UI kit |
| `apps/web/src/components/forms/PortalForm.tsx` | Create | Portal config form (selector fields) |
| `apps/web/src/components/forms/ProfileForm.tsx` | Create | Profile editor form |
| `apps/web/tailwind.config.ts` | Create | Tailwind CSS config |
| `apps/web/postcss.config.mjs` | Create | PostCSS config |
| `apps/worker/package.json` | Create | Worker dependencies (Playwright, prisma client) |
| `apps/worker/src/index.ts` | Create | Poll loop entry point |
| `apps/worker/src/pipeline.ts` | Create | Pipeline orchestrator |
| `apps/worker/src/handlers/scrape.ts` | Create | Scrape step handler |
| `apps/worker/src/handlers/match.ts` | Create | Match + score step handler |
| `apps/worker/src/handlers/apply.ts` | Create | Auto-apply + cover letter step handler |
| `apps/worker/src/handlers/notify.ts` | Create | Notification step handler |
| **Packages** | | |
| `packages/database/package.json` | Create | Prisma client package |
| `packages/database/prisma/schema.prisma` | Create | Full schema (see below) |
| `packages/database/src/index.ts` | Create | Re-export Prisma client singleton |
| `packages/scraper/package.json` | Create | Scraper engine package |
| `packages/scraper/src/index.ts` | Create | Public API |
| `packages/scraper/src/engine.ts` | Create | Core: takes PortalConfig → Playwright page → structured jobs |
| `packages/scraper/src/types.ts` | Create | Shared scraper types |
| `packages/scraper/src/built-in/linkedin.ts` | Create | LinkedIn default selector config |
| `packages/scraper/src/built-in/infojobs.ts` | Create | Infojobs default selector config |
| `packages/scraper/src/built-in/computrabajo.ts` | Create | Computrabajo default selector config |
| `packages/scraper/src/built-in/bumeran.ts` | Create | Bumeran default selector config |
| `packages/scraper/src/selectors.ts` | Create | Registry of built-in selector configs |
| `packages/matcher/package.json` | Create | Matcher engine package |
| `packages/matcher/src/index.ts` | Create | Public API |
| `packages/matcher/src/engine.ts` | Create | Core matching logic |
| `packages/matcher/src/scoring.ts` | Create | Keyword/role/skill/location scoring |
| `packages/matcher/src/types.ts` | Create | Shared matcher types |
| `packages/cover-letter/package.json` | Create | Cover letter generator package |
| `packages/cover-letter/src/index.ts` | Create | Public API |
| `packages/cover-letter/src/generator.ts` | Create | LLM API interaction |
| `packages/cover-letter/src/prompt.ts` | Create | Prompt templates (formal tone, multi-language) |
| `packages/cover-letter/src/language.ts` | Create | Language detection for postings |
| `packages/cover-letter/src/types.ts` | Create | Shared types |
| `packages/notifier/package.json` | Create | Notifier package |
| `packages/notifier/src/index.ts` | Create | Public API |
| `packages/notifier/src/email.ts` | Create | SMTP/Resend email sender |
| `packages/notifier/src/in-app.ts` | Create | In-app notification DB writer |
| `packages/notifier/src/types.ts` | Create | Shared types |
| **Root** | | |
| `package.json` | Create | Root workspace config |
| `turbo.json` | Create | Turborepo pipeline config |
| `tsconfig.json` | Create | Base TypeScript config |
| `.env.example` | Create | Required env vars template |
| `.gitignore` | Create | Standard ignores |
| `docker/docker-compose.yml` | Create | PostgreSQL + app services |
| `docker/Dockerfile.web` | Create | Next.js production build |
| `docker/Dockerfile.worker` | Create | Worker production build |

## Database Schema (Prisma)

```
model User {
  id             String   @id @default(uuid())
  email          String   @unique
  passwordHash   String
  name           String?
  createdAt      DateTime @default(now())
  updatedAt      DateTime @updatedAt
  profile        Profile?
  portals        Portal[]
  applications   Application[]
  notifications  Notification[]
  pipelineRuns   PipelineRun[]
}

model Profile {
  id              String   @id @default(uuid())
  userId          String   @unique
  user            User     @relation(fields: [userId], references: [id])
  targetRoles     String[] // JSON array of role titles
  techStack       String[] // skills, languages, frameworks
  experienceLevel String   // junior, mid, senior, lead
  minSalary       Int?
  maxSalary       Int?
  locations       String[] // preferred cities/countries
  remoteOnly      Boolean  @default(false)
  languages       String[] // spoken languages
  isActive        Boolean  @default(true)
  createdAt       DateTime @default(now())
  updatedAt       DateTime @updatedAt
}

model Portal {
  id                   String   @id @default(uuid())
  userId               String?
  user                 User?    @relation(fields: [userId], references: [id])
  name                 String
  baseUrl              String
  jobListingUrl        String   // URL template, e.g. "https://example.com/jobs?q={query}&location={location}"
  selectors            Json     // { jobCard, title, company, location, description, url, salary, postedDate, applyButton }
  isBuiltin            Boolean  @default(false)
  isEnabled            Boolean  @default(true)
  isVerified           Boolean  @default(false) // passed dry-run
  scrapeIntervalMin    Int      @default(60)
  createdAt            DateTime @default(now())
  updatedAt            DateTime @updatedAt
  storedJobs           StoredJob[]
  scrapeSessions       ScrapeSession[]
}

model StoredJob {
  id               String   @id @default(uuid())
  externalId       String?  // portal-specific job ID (nullable for custom portals)
  portalId         String
  portal           Portal   @relation(fields: [portalId], references: [id])
  title            String
  company          String
  location         String?
  description      String
  url              String
  salaryRange      String?
  postedAt         DateTime?
  scrapedAt        DateTime @default(now())
  language         String   @default("en")
  applications     Application[]
  @@unique([portalId, externalId]) // prevent duplicate jobs
}

model Application {
  id                   String   @id @default(uuid())
  userId               String
  user                 User     @relation(fields: [userId], references: [id])
  storedJobId          String
  storedJob            StoredJob @relation(fields: [storedJobId], references: [id])
  pipelineRunId        String?
  pipelineRun          PipelineRun? @relation(fields: [pipelineRunId], references: [id])
  status               String   @default("pending") // pending, submitted, failed, skipped
  matchScore           Float?
  coverLetterGenerated Boolean  @default(false)
  coverLetterText      String?
  submittedAt          DateTime?
  errorMessage         String?
  createdAt            DateTime @default(now())
  updatedAt            DateTime @updatedAt
  notifications        Notification[]
}

model ScrapeSession {
  id            String   @id @default(uuid())
  portalId      String
  portal        Portal   @relation(fields: [portalId], references: [id])
  userId        String?
  status        String   // running, completed, failed
  jobsFound     Int      @default(0)
  errorMessage  String?
  startedAt     DateTime @default(now())
  completedAt   DateTime?
}

model PipelineRun {
  id          String   @id @default(uuid())
  userId      String
  user        User     @relation(fields: [userId], references: [id])
  portalId    String?
  status      String   @default("pending") // pending, scraping, matching, applying, notifying, completed, failed
  trigger     String   @default("manual") // manual, scheduled
  steps       Json?    // { scrape: "done", match: "done", apply: "pending", notify: "pending" }
  errorStep   String?
  errorMsg    String?
  createdAt   DateTime @default(now())
  completedAt DateTime?
  applications Application[]
}

model Notification {
  id            String   @id @default(uuid())
  userId        String
  user          User     @relation(fields: [userId], references: [id])
  applicationId String?
  application   Application? @relation(fields: [applicationId], references: [id])
  type          String   // application_submitted, application_failed, portal_error, match_found
  channel       String   @default("in_app") // in_app, email, both
  title         String
  body          String
  isRead        Boolean  @default(false)
  sentAt        DateTime @default(now())
  readAt        DateTime?
}
```

## Interfaces / Contracts

### ScraperEngine

```typescript
// packages/scraper/src/types.ts
interface PortalConfig {
  id: string;
  name: string;
  baseUrl: string;
  jobListingUrl: string;
  selectors: PortalSelectors;
}

interface PortalSelectors {
  jobCard: string;         // CSS selector for each job card container
  title: string;           // CSS selector or XPath relative to jobCard
  company: string;
  location: string;
  description: string;
  url: string;
  salary: string | null;
  postedDate: string | null;
  applyButton: string | null; // selector for "apply" button on detail page
}

interface ScrapedJob {
  externalId: string | null;
  title: string;
  company: string;
  location: string | null;
  description: string;
  url: string;
  salaryRange: string | null;
  postedAt: Date | null;
  language: string;
}
```

### MatcherEngine

```typescript
// packages/matcher/src/types.ts
interface MatchInput {
  job: ScrapedJob;
  profile: Profile; // Prisma Profile type
}
interface MatchResult {
  score: number; // 0–100
  factors: { keywordMatch: number; roleMatch: number; locationMatch: number; seniorityMatch: number };
}
```

### CoverLetterGenerator

```typescript
// packages/cover-letter/src/types.ts
interface CoverLetterInput {
  jobTitle: string;
  company: string;
  jobDescription: string;
  profile: { targetRoles: string[]; techStack: string[]; experienceLevel: string };
  language: string; // target language for the letter
}
```

### Notifier

```typescript
// packages/notifier/src/types.ts
interface NotificationInput {
  userId: string;
  applicationId?: string;
  type: 'application_submitted' | 'application_failed' | 'portal_error' | 'match_found';
  title: string;
  body: string;
  channels: ('in_app' | 'email')[];
}
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Scorer functions, prompt building, selector parsing | Vitest — pure function tests, no external deps |
| Unit | JWT auth helpers, password hashing | Vitest — token sign/verify, hash comparison |
| Integration | Scraper engine against Playwright browser | Vitest + Playwright — launch headless, parse known HTML fixtures |
| Integration | Prisma CRUD operations | `testcontainers` with PostgreSQL or SQLite test DB |
| Integration | LLM cover letter generation | Mock API responses (nock/interceptors) — test prompt construction, not the API |
| E2E | Full pipeline: scrape → match → apply → notify | Playwright — mock portal HTML, intercept LLM calls, assert DB rows and notification creation |
| E2E | User registration, login, portal config, dashboard | Playwright — browser-level flows against the Next.js app |
| Dry-run test | User-configured portal selectors | Scraper engine in test mode: returns parsed jobs without persisting; validates selector coverage |

## Migration / Rollout

1. **Phase 0 — Scaffold**: Initialize monorepo, Turborepo config, shared TypeScript, Prisma schema. Run `prisma migrate dev` to create DB.
2. **Phase 1 — Auth + Profile**: Next.js app shell, JWT auth API, login/register pages, profile editor.
3. **Phase 2 — Portal Config + Scraper**: `packages/scraper` with engine + 4 built-in configs, portal CRUD API + UI, dry-run test mode.
4. **Phase 3 — Worker Pipeline**: `apps/worker` poll loop, scrape → match handlers, pipeline runs table updates. Manual trigger from dashboard.
5. **Phase 4 — Auto-Apply + Cover Letter**: Apply handler with Playwright form filling, LLM cover letter generation via `packages/cover-letter`.
6. **Phase 5 — Notifications**: Email + in-app notification system, notification history UI.
7. **Phase 6 — Polish**: Scheduled scraping (cron via node-schedule or OS cron), error handling, rate limiting, anti-detection delays.

## Open Questions

- [ ] Email provider preference: SMTP (nodemailer) vs transactional API (Resend/SendGrid)? Resend is simpler but requires API key; SMTP works with any provider.
- [ ] Should built-in portal selectors be seeded in DB (via migration) or loaded from code? Code-loading means updates via package releases; DB means users get updates through migrations.
- [ ] Anti-detection strategy for Playwright: stealth plugin vs manual randomization? `playwright-extra` with `puppeteer-extra-plugin-stealth` equivalent exists but adds complexity.
- [ ] Match threshold: configurable per user or global? Proposal implies per-user but should confirm default value (e.g., 60/100).
