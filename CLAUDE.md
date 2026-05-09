# CLAUDE.md — StreetSense AI
> This file is read by Claude Code at the start of every session.
> It defines the project context, architecture decisions, coding rules,
> and what Claude Code is and is not allowed to do autonomously.
>
> **Version 1.2** — May 2026
> Pair with `DESIGN.md` (visual system), `ROADMAP.md` (phase tracker),
> `DECISIONS.md` (ADR log), and `.phase` (current phase pointer).

---

## 1. Project Identity

**Product:** StreetSense AI
**Tagline:** Cross-Authority Roadworks Intelligence Platform
**Purpose:** An AI-powered web application that consumes UK open government
data (Street Manager, D-TRO, NUAR) to provide corridor disruption risk
scoring, underground asset strike risk, non-compliance analytics, and a
conversational AI copilot for highway authority officers and permit managers.

**Strategic goal:** Attract Causeway Technologies leadership (CEO Paul Devlin,
CTO Charlie Pickering, SVP Infrastructure Nick Smee) by demonstrating the
AI intelligence layer their CausewayOne platform is missing — built on open
data, publicly accessible, and shipped before their own roadmap catches up
(D-TRO integration confirmed September 2027 on the public Street Manager roadmap).

**Solo founder project. Every line of code must be production-quality.**
There is no team to fix shortcuts later.

---

## 2. Tech Stack — Locked. Do Not Deviate.

| Layer            | Technology                                  | Version             |
|------------------|---------------------------------------------|---------------------|
| Framework        | Next.js (App Router)                        | 15.x                |
| Language         | TypeScript                                  | 5.x strict          |
| Styling          | **Tailwind CSS v3.x** (NOT v4)              | 3.4.x               |
| Components       | shadcn/ui                                   | Latest              |
| Map              | Mapbox GL JS                                | 3.x                 |
| Data fetching    | TanStack Query                              | 5.x                 |
| State            | Zustand                                     | 4.x                 |
| Backend          | Python 3.12 + FastAPI                       | Latest              |
| Python tooling   | **uv + pyproject.toml** (NOT requirements.txt) | uv 0.5+          |
| Database         | PostgreSQL 16 + PostGIS                     | 16.x                |
| AI Orchestration | LangChain Python                            | Latest              |
| LLM (primary)    | Anthropic Claude Sonnet 4                   | claude-sonnet-4-20250514 |
| LLM (fast)       | Anthropic Claude Haiku 4.5                  | claude-haiku-4-5-20251001 |
| Background jobs  | Celery + Redis                              | Latest              |
| ORM              | SQLAlchemy 2.x + Alembic                    | 2.x                 |
| Testing (FE)     | Vitest + React Testing Library              | Latest              |
| Testing (BE)     | pytest + pytest-asyncio                     | Latest              |
| Hosting          | Railway (backend) + Vercel (frontend)       | —                   |

### Tailwind Version Decision
Use Tailwind **v3.4.x**, not v4. Reasons:
- shadcn/ui canonical setup is v3-based as of May 2026
- DESIGN.md uses `tailwind.config.ts` (v3 syntax), not v4's `@theme` directive
- v4 migration is a Phase 7+ consideration, not Phase 1

### Python Tooling Decision
Use **uv** with **pyproject.toml** for dependency management:
```bash
uv init                        # Create pyproject.toml
uv add fastapi sqlalchemy      # Add dependencies
uv sync                        # Install from lock file
uv run uvicorn main:app        # Run with project venv
```
Never create or maintain `requirements.txt`. If one is needed for deployment,
generate it via `uv export -o requirements.txt`.

**Never suggest replacing any item in this table without explicit instruction.**
If a dependency conflict arises, resolve it — do not swap the library.

---

## 3. Project Structure

```
streetsense/
├── CLAUDE.md                  ← This file
├── DESIGN.md                  ← Design system reference
├── ROADMAP.md                 ← Phase tracker + this-week status
├── DECISIONS.md               ← Architecture decision log (ADRs)
├── README.md                  ← Public-facing project description
├── .phase                     ← Current phase number (1–6). Single line.
├── .env.local                 ← Never commit. Never read aloud.
├── .env.example               ← Committed. No real values.
├── pnpm-workspace.yaml        ← Monorepo workspace config
│
├── apps/
│   ├── web/                   ← Next.js 15 frontend (App Router)
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx           ← Map canvas — the primary experience
│   │   │   ├── analytics/
│   │   │   │   └── page.tsx       ← Non-compliance dashboard
│   │   │   └── api/
│   │   │       └── copilot/
│   │   │           └── route.ts   ← Streaming AI endpoint
│   │   ├── components/
│   │   │   ├── map/               ← All Mapbox components
│   │   │   ├── copilot/           ← AI panel components
│   │   │   ├── risk/              ← Risk score components
│   │   │   ├── analytics/         ← Dashboard components
│   │   │   ├── layout/            ← Header, Sheet wrappers
│   │   │   └── ui/                ← shadcn/ui components (auto-generated)
│   │   ├── lib/
│   │   │   ├── api.ts             ← API client (TanStack Query hooks)
│   │   │   ├── stores/
│   │   │   │   ├── map.ts         ← Zustand map state
│   │   │   │   └── panels.ts      ← Sheet open/close state machine
│   │   │   └── utils.ts           ← cn() and shared helpers
│   │   ├── types/
│   │   │   └── index.ts           ← All shared TypeScript types
│   │   └── tailwind.config.ts
│   │
│   └── api/                       ← FastAPI Python backend
│       ├── pyproject.toml         ← uv-managed dependencies
│       ├── uv.lock
│       ├── main.py
│       ├── routers/
│       │   ├── works.py           ← Street Manager data endpoints
│       │   ├── corridors.py       ← Corridor risk scoring
│       │   ├── nuar.py            ← Underground asset endpoints
│       │   ├── compliance.py      ← Non-compliance analytics
│       │   └── copilot.py         ← LangChain AI agent endpoint
│       ├── models/                ← SQLAlchemy models
│       ├── schemas/               ← Pydantic request/response schemas
│       ├── services/              ← All external API clients + business logic
│       │   ├── street_manager.py
│       │   ├── nuar.py
│       │   ├── dtro.py
│       │   ├── risk_scorer.py
│       │   └── agent.py
│       ├── tasks/
│       │   └── ingest.py          ← Celery ingestion tasks
│       └── tests/
│
└── infra/
    ├── docker-compose.yml         ← Local dev: postgres, redis
    └── .env.example
```

### Note on Removed Routes
The previous version of this file listed `app/corridors/[id]/page.tsx` —
this has been **removed** because corridor detail is rendered in a slide-in
Sheet that overlays the map (see DESIGN.md Section 4.1). Deep-linking to a
corridor is supported via URL search params on the map page
(`/?corridor={id}`), not via a separate route.

---

## 4. Phase Tracking

The current active phase is stored in the **`.phase`** file at the repo root.
Read this file at the start of every session to determine which phase the
developer is working on.

```bash
$ cat .phase
1
```

Valid values: `1`, `2`, `3`, `4`, `5`, `6` — corresponding to the six phases
defined in the StreetSense AI Planning Document.

**When in doubt, ask the developer which phase is active. Never assume.**

| Phase | Name                                  | Module Set Allowed |
|-------|---------------------------------------|--------------------|
| 1     | Foundation & Open Data Ingestion      | SM-001 to SM-007 |
| 2     | Corridor Risk Engine                  | All Phase 1 + CR-001 to CR-007 |
| 3     | AI Copilot Layer                      | All previous + AI-001 to AI-007 |
| 4     | NUAR Underground Risk Integration     | All previous + UN-001 to UN-007 |
| 5     | Non-Compliance Analytics              | All previous + NC-001 to NC-007 |
| 6     | D-TRO Integration & Market Launch     | All previous + DT-001 to DT-007 |

**Do not build features from a higher phase than `.phase` indicates.**
If the developer asks for something out of phase, confirm before proceeding.

---

## 5. Environment Variables

**Never read, print, log, or expose any value from `.env.local`.**
**Never commit `.env.local` under any circumstances.**

Required variables (see `.env.example` for the complete list with comments):

```
ANTHROPIC_API_KEY=
NEXT_PUBLIC_MAPBOX_TOKEN=
OS_API_KEY=
STREET_MANAGER_API_KEY=
STREET_MANAGER_BASE_URL=
NUAR_API_KEY=                  # Phase 4+ only
NUAR_BASE_URL=                 # Phase 4+ only
DTRO_API_KEY=                  # Phase 6+ only
DTRO_BASE_URL=                 # Phase 6+ only
DATABASE_URL=
REDIS_URL=
```

---

## 6. Design Rules — DESIGN.md Is the Source of Truth

The complete design system lives in `DESIGN.md`. This section lists the
non-negotiable rules that must be enforced in every commit.

### 6.1 Layout
- The map canvas always occupies **minimum 60% of the viewport** on desktop
- The copilot panel is a **slide-in Sheet** from the right — never a modal
- The corridor detail panel is a **Sheet from the right** at 420px width
- The copilot panel is a **Sheet from the right** at 480px width
- **Sheet conflict resolution**: opening the copilot panel automatically
  closes the corridor panel, and vice versa — they never coexist on screen
  (panel state machine in `lib/stores/panels.ts`)
- The analytics page is the **only full-page layout** without a map
- Mobile layout is **out of scope until Phase 3** — do not add responsive
  breakpoints below `md:` unless explicitly instructed

### 6.2 Colour Tokens — Use ONLY DESIGN.md Tokens

**The canonical token names live in DESIGN.md Section 2.1.**
Do not invent token names. Do not use Tailwind default colour palettes
(`bg-green-*`, `bg-red-*`, `text-gray-*`).

```tsx
// ✅ CORRECT — uses DESIGN.md tokens
<div className="bg-brand text-ink-inverse" />
<div className="bg-surface-page" />
<Badge className="bg-risk-low-bg text-risk-low" />
<p className="text-ink-muted" />
<hr className="border-line" />

// ❌ WRONG — invented or default tokens
<div className="bg-slate-brand" />              // Token does not exist
<div className="bg-emerald-signal" />           // Token does not exist
<Badge className="bg-green-100 text-green-700" /> // Use risk-low tokens
<p className="text-gray-500" />                 // Use text-ink-muted
```

### 6.3 Typography
- Body text: `font-sans` (Inter) — always
- Permit reference numbers: `font-mono text-xs` — always, no exceptions
- USRN codes: `font-mono text-xs` — always
- Page headings: `text-2xl font-semibold text-brand`
- Section labels: `text-xs font-medium text-ink-subtle uppercase tracking-wider`

### 6.4 Risk Score Display
Risk levels must always use the **exact tokens defined in DESIGN.md
Section 2.1**. Never invent new variants. The canonical mapping is:

```tsx
// components/risk/risk-config.ts — single source of truth
import type { RiskLevel } from '@/types'

export const RISK_CONFIG: Record<RiskLevel, {
  label: string
  dot: string
  bg: string
  text: string
}> = {
  low:      { label: 'Low',      dot: 'bg-risk-low',      bg: 'bg-risk-low-bg',      text: 'text-risk-low'      },
  medium:   { label: 'Medium',   dot: 'bg-risk-medium',   bg: 'bg-risk-medium-bg',   text: 'text-risk-medium'   },
  high:     { label: 'High',     dot: 'bg-risk-high',     bg: 'bg-risk-high-bg',     text: 'text-risk-high'     },
  critical: { label: 'Critical', dot: 'bg-risk-critical', bg: 'bg-risk-critical-bg', text: 'text-risk-critical' },
} as const
```

### 6.5 Components
- Use `shadcn/ui` components as the base for **all** UI elements
- Add components via `npx shadcn@latest add [component]` — never copy-paste
  shadcn source manually
- Extend shadcn components with `className` prop — never modify the source
  files in `components/ui/`
- For data tables: always use `@tanstack/react-table` via the shadcn
  DataTable pattern — never a plain HTML table

### 6.6 AI Copilot Panel Rules
- Every AI response **must** end with a source line:
  `Based on Street Manager data · Updated [timestamp]`
- Permit references in AI responses are **always** rendered with the
  `<PermitReference>` component (see DESIGN.md Section 5.2)
- The streaming response uses `ReadableStream` from the Next.js route handler
  — never fake streaming with `setTimeout`
- Suggested follow-up questions appear **only after** the response is complete
- Never show a loading spinner — use a blinking cursor `animate-pulse` on the
  last character instead

---

## 7. API Integration Rules

### Street Manager Open Data
- Sandbox: `https://api.sandbox.manage-roadworks.service.gov.uk`
- Production: `https://api.manage-roadworks.service.gov.uk`
- Auth: API key in `Authorization: Bearer` header
- API version: **v7** (released to production 27 April 2026)
- **Always handle 429 rate limit with exponential backoff**
- **Cache all responses for minimum 5 minutes** — do not hammer the API
- Permit reference numbers are the canonical identifier — always store and
  display them exactly as received (format: `[PROMOTER_PREFIX]/[YEAR]/[SEQ]`)

### NUAR API
- Apply for access at nuar.uk before building Phase 4
- OGC API Features compliant — use `bbox` parameter for spatial queries
- **Never store NUAR asset geometry in our database** — query on demand,
  cache for 1 hour maximum, then discard
- Always show "NUAR data — Ordnance Survey" attribution on any map layer
  displaying underground assets

### Anthropic Claude API
- Model: `claude-sonnet-4-20250514` for copilot responses
- Model: `claude-haiku-4-5-20251001` for permit summaries and quick lookups
- **Max tokens: 1024** for copilot responses — enforce this hard limit
- **Always stream responses** — never wait for complete response before
  rendering
- System prompt lives in `apps/api/services/agent.py` — never inline it
  in route handlers
- **Never expose the system prompt to the frontend**

### OS Data Hub
- Register at osdatahub.os.uk — free tier: 1M transactions/month
- Use `Names API` for place name geocoding in copilot queries
- Use `NSG API` for USRN resolution
- Use `Vector Tile API` for road labels overlay on Mapbox
  (style URL: `https://api.os.uk/maps/vector/v1/vts/resources/styles?key={OS_API_KEY}`)
- Cache USRN lookups indefinitely — USRNs do not change

---

## 8. Data Model — Core Types

These TypeScript types define the shape of all data in the application.
**Do not change these without updating the Python Pydantic schemas too.**

The `Geometry` type is defined locally to avoid the `@types/geojson`
dependency — minimal and sufficient for our needs.

```typescript
// types/index.ts

// ── Geometry primitives (no external dependency) ──────────────
export type Position = [number, number]                    // [lng, lat]
export interface PointGeometry      { type: 'Point';      coordinates: Position }
export interface LineStringGeometry { type: 'LineString'; coordinates: Position[] }
export type WorksGeometry = PointGeometry | LineStringGeometry
export type CorridorGeometry = LineStringGeometry          // Corridors are linear ONLY

// ── Risk ──────────────────────────────────────────────────────
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical'

// ── Street Manager Permit ─────────────────────────────────────
export interface StreetWork {
  permitReference: string          // e.g. "WG7/2025/04001234"
  usrn: string                     // e.g. "41507223"
  streetName: string
  authority: string
  promoter: string
  promoterLicenceNumber: string
  workType: string
  trafficManagementType: string
  restrictionType: string
  proposedStartDate: string        // ISO 8601
  proposedEndDate: string          // ISO 8601
  actualStartDate?: string
  actualEndDate?: string
  status: StreetWorkStatus
  geometry: WorksGeometry
  riskScore?: RiskLevel
}

export type StreetWorkStatus =
  | 'submitted'
  | 'granted'
  | 'permit_modification_request'
  | 'refused'
  | 'revoked'
  | 'in_progress'
  | 'completed'
  | 'closed'

// ── Corridor (always a LineString) ────────────────────────────
export interface Corridor {
  id: string
  name: string                     // e.g. "A38 — Birmingham City Centre"
  roadClassification: 'A' | 'B' | 'C' | 'unclassified'
  geometry: CorridorGeometry       // Always LineString — never Point
  riskLevel: RiskLevel
  riskScore: number                // 0–100
  riskFactors: RiskFactor[]
  concurrentWorks: StreetWork[]
  activeWorksCount: number
  plannedWorksCount: number
  lastCalculated: string           // ISO 8601
}

export interface RiskFactor {
  factor: string
  weight: number
  contribution: number
  description: string
}

// ── NUAR (never persisted — query on demand only) ─────────────
export interface NUARAsset {
  assetId: string
  assetType: 'gas' | 'electric' | 'water' | 'telecoms' | 'other'
  depth?: number                   // metres
  pressureTier?: string
  voltageLevel?: string
  operatorName: string
  geometry: WorksGeometry
  // ⚠ NEVER store this in the database. In-memory cache 1h max.
}

export interface StrikeRisk {
  permitReference: string
  overallRisk: RiskLevel
  assetCount: number
  assetsByType: Record<string, number>
  highestRiskAsset?: {
    type: string
    operator: string
    risk: string
  }
  calculatedAt: string
}

// ── Promoter Compliance ───────────────────────────────────────
export interface PromoterCompliance {
  promoterLicenceNumber: string
  promoterName: string
  totalWorks: number
  overrunRate: number              // 0–1 percentage
  lateStartRate: number
  missingReinstatementRate: number
  complianceScore: number          // 0–100, higher is better
  trend: 'improving' | 'stable' | 'deteriorating'
  region: string
  lastUpdated: string
}

// ── Copilot ───────────────────────────────────────────────────
export interface CopilotMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations: PermitCitation[]
  suggestedQuestions?: string[]
  dataTimestamp: string
  createdAt: string
}

export interface PermitCitation {
  permitReference: string
  streetName: string
  promoter: string
  relevance: string
}
```

---

## 9. Coding Standards

### TypeScript
- **Strict mode always** — `"strict": true` in tsconfig
- No `any` — use `unknown` and narrow, or define a proper type
- No non-null assertions (`!`) without a comment explaining why
- All async functions must handle errors — no unhandled promise rejections
- Prefer `const` everywhere — `let` only when reassignment is necessary

### React / Next.js
- **Server Components by default** — only add `'use client'` when the
  component requires browser APIs, event handlers, or React hooks
- Data fetching happens in Server Components or API route handlers —
  never in `useEffect`
- Mapbox GL JS requires `'use client'` — wrap in a dynamic import:
  ```tsx
  const MapCanvas = dynamic(() => import('@/components/map/MapCanvas'), {
    ssr: false,
    loading: () => <MapSkeleton />
  })
  ```
- No inline styles — Tailwind classes only
- Component files: PascalCase (`CorridorPanel.tsx`)
- Utility files: camelCase (`riskScorer.ts`)
- All components accept a `className` prop for extension

### Python / FastAPI
- Type hints on every function — no bare `def`
- Pydantic models for all request/response bodies
- SQLAlchemy models in `models/`, Pydantic schemas in `schemas/`
- All database queries go through the service layer — never raw SQL in
  route handlers
- All external API calls (Street Manager, NUAR, OS) go through the
  `services/` layer — never called directly from routes
- Use `async def` for all FastAPI route handlers
- Background tasks via Celery — never `asyncio.create_task` for long jobs
- Dependencies managed with **uv** — never edit `pyproject.toml` directly,
  use `uv add` / `uv remove`

### Git
- Commit messages: `type(scope): description`
  - Types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`
  - Examples: `feat(map): add corridor heat map overlay`
  - Examples: `fix(copilot): handle empty Street Manager response`
- Never commit: `.env.local`, API keys, NUAR asset geometry data
- Branch naming: `phase-1/sm-data-ingestion`, `phase-2/corridor-risk`

---

## 10. What Claude Code Can Do Autonomously

✅ Create new files and components following the structure above
✅ Add npm packages within the locked tech stack via `pnpm add`
✅ Add Python packages within the locked tech stack via `uv add`
✅ Run `npx shadcn@latest add [component]` to add UI components
✅ Write and run tests
✅ Create database migrations with Alembic
✅ Refactor code that does not change external behaviour
✅ Fix TypeScript errors and linting issues
✅ Write inline comments explaining complex logic
✅ Read `.phase` to determine current phase

---

## 11. What Claude Code Must NOT Do Without Explicit Instruction

🚫 Change any item in the tech stack table (Section 2)
🚫 Add dependencies not in the tech stack without asking first
🚫 Migrate to Tailwind v4 (locked at v3.4.x)
🚫 Create or maintain `requirements.txt` (use uv + pyproject.toml)
🚫 Modify files in `components/ui/` (shadcn source)
🚫 Add mobile responsive styles below `md:` breakpoint
🚫 Add dark mode styles
🚫 Call any external API directly from a React component
🚫 Store NUAR asset geometry in the database
🚫 Add any authentication system before Phase 6
🚫 Create a `pages/` directory — App Router only
🚫 Create the `app/corridors/[id]/page.tsx` route — corridor detail is a Sheet
🚫 Use `fetch` in a `useEffect` — use TanStack Query or Server Components
🚫 Add animations to data tables or lists
🚫 Change the TypeScript types in Section 8 without updating Pydantic schemas
🚫 Hardcode any API keys, even as placeholders
🚫 Use Tailwind default colour palettes (`bg-green-*`, `bg-gray-*`) — only DESIGN.md tokens
🚫 Build Phase N+1 features when `.phase` says N
🚫 Console.log in production code — use proper error boundaries

---

## 12. First Session Checklist

When starting a new Claude Code session on this project, run through:

1. Confirm `CLAUDE.md`, `DESIGN.md`, `ROADMAP.md`, `DECISIONS.md`, and `.phase` are present and readable
2. Read `.phase` — confirm current phase number (1–6)
3. Read `ROADMAP.md` "This Week" section — confirm active module
4. Skim `DECISIONS.md` for any ADRs relevant to the current task
5. Confirm `.env.local` exists (do not read its contents)
6. Run existing tests before making changes:
   `pnpm test` (frontend) and `uv run pytest` (backend)
7. Check for any `TODO(phase-N)` comments left in previous session
8. At end of session: append a one-line entry to `ROADMAP.md` Sessions Log

---

## 13. Useful Commands

```bash
# Frontend (from apps/web)
pnpm dev                    # Next.js dev server
pnpm build                  # Production build
pnpm test                   # Vitest
pnpm lint                   # ESLint
npx shadcn@latest add [component]   # Add shadcn component
npx tsc --noEmit            # TypeScript check (no build)

# Backend (from apps/api)
uv sync                     # Install/sync dependencies
uv run uvicorn main:app --reload         # FastAPI dev server
uv run celery -A tasks worker --loglevel=info  # Celery worker
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head # Run migrations
uv run pytest               # Run all tests
uv run pytest -k "corridor" # Run specific tests
uv run mypy .               # Python type check
uv add fastapi              # Add a new dependency
uv remove pydantic-old      # Remove a dependency
uv export -o requirements.txt  # Export for deployment if needed

# Database (local docker, from infra/)
docker-compose up -d        # Start postgres + redis
docker-compose down         # Stop
psql $DATABASE_URL          # Connect to postgres

# Phase management
cat .phase                  # Show current phase (1–6)
echo "2" > .phase           # Advance to Phase 2 (developer-controlled only)
```

---

## 14. Changelog

**v1.2 — May 2026**
- Added `ROADMAP.md` (phase tracker + sessions log) and `DECISIONS.md` (ADR log) to required project files
- Updated First Session Checklist to require reading `ROADMAP.md` "This Week" and skimming relevant ADRs from `DECISIONS.md`
- Added end-of-session requirement to append to `ROADMAP.md` Sessions Log

**v1.1 — May 2026**
- Aligned all colour token names with DESIGN.md (no more `slate-brand`/`emerald-signal` aliases)
- Locked Tailwind to v3.4.x explicitly
- Standardised Python tooling on `uv` + `pyproject.toml`
- Added `.phase` file mechanism for phase tracking
- Removed dead `app/corridors/[id]/page.tsx` route (corridor detail is a Sheet)
- Fixed `geometry` typing — removed implicit `@types/geojson` dependency, defined local `Position`/`PointGeometry`/`LineStringGeometry`
- Added Sheet conflict resolution rule (corridor and copilot mutually exclusive)
- Added explicit OS Vector Tile API guidance
- Added `pnpm-workspace.yaml` to project structure (monorepo workspace)
- Added Street Manager API v7 reference (production release 27 April 2026)

**v1.0 — May 2026** — Initial version

---

*CLAUDE.md is a living document. Update it when architecture decisions change.*
*Last updated: May 2026 | Version: 1.2*
