# StreetSense AI

> **Cross-Authority Roadworks Intelligence Platform**
> All 6 phases complete · 335 backend tests · 0 TypeScript errors

An AI-powered platform that turns UK open government roadworks data into operational intelligence — corridor disruption risk scoring, underground asset strike risk, permit–TRO conflict detection, non-compliance analytics, and a conversational AI copilot for highway authority officers and permit managers.

Built entirely on Street Manager open data, NUAR, and the D-TRO public beta. Delivers the cross-authority intelligence layer the DfT's own roadmap won't ship until September 2027.

---

## What It Does

| Capability | Description |
|---|---|
| **Corridor Risk Map** | Heatmap of A/B/C road corridors scored 0–100 for disruption risk. Weighted by concurrent works, overruns, traffic management type, and timing proximity. 3D satellite view with fog and atmosphere. Streets / Dark / Satellite basemap switcher. |
| **Underground Strike Risk** | Per-permit risk score (Low → Critical) based on NUAR underground asset density within 25 m. Inline badge on every work card. Composite score (60% surface + 40% underground) in corridor detail panel. |
| **D-TRO Conflict Detection** | Real-time overlay of Digital Traffic Regulation Orders (D-TRO v4.0.0) on the map as sky-blue dashed lines. Per-corridor conflict detector flags permits that spatially and/or temporally clash with active TROs — severity mapped from road closure (critical) to speed limit (low). |
| **AI Copilot** | Claude Sonnet 4 streaming assistant grounded in Street Manager permit data. Permit citations rendered inline. Suggested follow-up questions. Full audit trail. |
| **Scheduling Advisor** | Pairwise conflict detector across open permits. Flags works on the same USRN with overlapping dates or conflicting traffic management. |
| **Non-Compliance Analytics** | Promoter league table ranked by compliance score. 12-month trend sparklines. FPN opportunity detector (overrunning works). AI-generated authority briefing. CSV export. |
| **Authority Portal** | Clerk-authenticated `/authority/*` routes for highway authority officers. Dashboard and alerts pages — expandable post-launch. |
| **Embeddable Widget** | `/embed/corridor/[id]` — frameable risk card for third-party integrations (e.g. CausewayOne). Supports `?theme=light\|dark`. No auth, no navigation chrome. |
| **Admin Console** | API health + live test runner, data source mode selector (Synthetic / API / Auto), record counts, webhook endpoint registry. |
| **Location Search** | Mapbox Forward Geocoding — GB-restricted, flyTo animation. |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend framework | Next.js 15 — App Router, TypeScript 5 strict |
| Styling | Tailwind CSS v3.4 + shadcn/ui |
| Map | Mapbox GL JS 3 — 3D buildings, satellite, style switcher, D-TRO GeoJSON layer |
| Auth | Clerk (`@clerk/nextjs`) — protects `/authority/*` routes |
| State / data fetching | Zustand 4 + TanStack Query 5 |
| Backend | Python 3.12 + FastAPI |
| AI | Anthropic Claude Sonnet 4 (`claude-sonnet-4-20250514`) + Haiku 4.5 via LangChain |
| Database | PostgreSQL 16 + PostGIS |
| Cache / broker | Redis 7 — D-TRO OAuth token (25-min TTL), Street Manager cursor, USRN lookups |
| Background jobs | Celery |
| ORM / migrations | SQLAlchemy 2 + Alembic |
| Python tooling | uv + pyproject.toml |
| Hosting | Hetzner CX23 VPS (backend) + Vercel (frontend) |

---

## Repository Structure

```
streetsense/
├── apps/
│   ├── web/                      # Next.js 15 frontend
│   │   ├── app/
│   │   │   ├── page.tsx          # Map canvas (primary view)
│   │   │   ├── analytics/        # Non-compliance dashboard
│   │   │   ├── audit/            # AI audit log
│   │   │   ├── scheduling/       # Scheduling conflict advisor
│   │   │   ├── authority/        # Clerk-protected authority portal
│   │   │   │   ├── dashboard/    # Authority overview page
│   │   │   │   └── alerts/       # TRO conflict alerts
│   │   │   ├── embed/
│   │   │   │   └── corridor/[id] # Embeddable risk widget
│   │   │   └── admin/            # Admin console (cookie-protected)
│   │   ├── components/
│   │   │   ├── map/              # MapCanvas, MapSearch, MapStyleControl (incl. D-TRO toggle)
│   │   │   ├── copilot/          # AI copilot panel
│   │   │   ├── risk/             # RiskBadge, risk-config
│   │   │   └── analytics/        # Compliance table, sparklines, FPN list
│   │   └── lib/
│   │       ├── api.ts            # TanStack Query hooks (incl. useDTROsGeoJSON, useCorridorConflicts)
│   │       └── stores/           # Zustand: map state (incl. showDtro) + panel state machine
│   │
│   └── api/                      # FastAPI Python backend
│       ├── routers/              # works, corridors, nuar, compliance, copilot, dtro, embed, admin, webhooks
│       ├── services/
│       │   ├── dtro.py           # D-TRO OAuth2 client (three-mode: synthetic / integration / production)
│       │   ├── conflict_detector.py  # Permit–TRO spatial+temporal conflict detection
│       │   └── synthetic/
│       │       ├── sm_generator.py   # Street Manager synthetic data
│       │       ├── nuar_synthetic.py # NUAR underground asset generator
│       │       └── dtro_generator.py # D-TRO synthetic orders (500 permanent + 200 TTROs)
│       ├── models/               # SQLAlchemy models (street_work, corridor, nuar, audit, dtro)
│       ├── schemas/              # Pydantic schemas (incl. dtro.py — D-TRO v4.0.0)
│       ├── alembic/versions/     # 0001–0005 migrations
│       ├── tasks/                # Celery ingestion tasks
│       └── tests/                # 335 pytest tests
│
└── infra/
    ├── docker-compose.yml        # Local dev: Postgres + Redis
    ├── docker-compose.prod.yml   # Hetzner production: full stack + Nginx + Certbot
    ├── nginx/streetsense.conf    # Reverse proxy + SSL termination
    └── .env.prod.example         # Production environment template
```

---

## Local Development

### Prerequisites

- Docker Desktop (for Postgres + Redis)
- Node.js 20+ and pnpm
- Python 3.12 and uv (`pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)

### 1 — Environment

```bash
cp .env.example .env.local
# Edit .env.local — minimum required for local dev:
#   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/streetsense
#   REDIS_URL=redis://localhost:6379/0
#   NEXT_PUBLIC_API_URL=http://localhost:8000
# Everything else is optional — synthetic data works without any API keys.
```

### 2 — Start infrastructure

```bash
cd infra
docker compose up -d
# Starts PostgreSQL 16 + PostGIS and Redis 7 on default ports
```

### 3 — Backend

```bash
cd apps/api
uv sync                                # Install dependencies from lockfile
uv run alembic upgrade head            # Create all tables (PostGIS extension required)
uv run uvicorn main:app --reload       # API at http://localhost:8000
```

To also run the Celery worker (needed for polling fallback SM-005):

```bash
uv run celery -A celery_app worker --loglevel=info
```

### 4 — Frontend

```bash
cd apps/web
pnpm install
pnpm dev       # http://localhost:3000
```

### 5 — Seed synthetic data

With the API running, seed 5 000+ Street Manager permits, 395 NUAR underground assets, and 700 D-TRO orders:

```bash
curl -X POST http://localhost:8000/works/admin/seed
curl -X POST http://localhost:8000/nuar/admin/seed
curl -X POST http://localhost:8000/dtros/admin/seed
curl -X POST http://localhost:8000/corridors/admin/score
```

Or use the **Admin Console** at `http://localhost:3000/admin` → Loaded Data tab → Reseed buttons.

---

## Running Tests

```bash
cd apps/api
uv run pytest              # 335 tests, ~9 seconds
uv run pytest -k "dtro"    # D-TRO tests only (30 tests across 3 files)
uv run pytest -k "corridor"  # Run a subset by keyword
uv run mypy .              # Python type check

cd apps/web
npx tsc --noEmit           # TypeScript check (0 errors)
pnpm build                 # Production build
```

---

## Environment Variables

See `.env.example` for the full reference with comments. Key variables:

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string (asyncpg driver) |
| `REDIS_URL` | Yes | Redis connection string |
| `ANTHROPIC_API_KEY` | For live AI | Unlocks AI copilot + compliance briefing with zero code changes |
| `SM_EMAIL` + `SM_PASSWORD` | For live SM data | Street Manager JWT credentials (ADR-026) |
| `SM_BASE_URL` | | Street Manager API base URL (defaults to production) |
| `OS_CLIENT_ID` + `OS_CLIENT_SECRET` | For live OS data | OS Data Hub OAuth2 credentials — USRN resolver + road classifier |
| `NEXT_PUBLIC_MAPBOX_TOKEN` | For map tiles | Mapbox public token |
| `PUBLIC_API_URL` | For webhooks | Publicly reachable URL of this API — SM sends events here |
| `DTRO_CLIENT_ID` + `DTRO_CLIENT_SECRET` | For live D-TRO data | D-TRO OAuth2 credentials — leave blank to use synthetic D-TRO data |
| `DTRO_BASE_URL` | | D-TRO API base URL (integration: `https://dtro-integration.dft.gov.uk`) |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | For authority portal | Clerk publishable key — protects `/authority/*` |
| `CLERK_SECRET_KEY` | For authority portal | Clerk secret key |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | For admin console | Protects `/admin/*` |
| `ADMIN_SESSION_SECRET` | For admin console | Signs the session cookie |

Four modules activate automatically when their key is set — no code changes required:

| Module | Key needed | What activates |
|---|---|---|
| AI-001 / NC-007 | `ANTHROPIC_API_KEY` | Real Claude responses instead of word-by-word mock |
| SM-001–006 | `SM_EMAIL` + `SM_PASSWORD` | Live Street Manager permit data |
| CR-002 / SM-003 | `OS_CLIENT_ID/SECRET` | Live USRN and road classification lookups |
| DT-001 | `DTRO_CLIENT_ID` + `DTRO_CLIENT_SECRET` | Live D-TRO orders via OAuth2 (integration or production) |

---

## Data Sources

| Source | Purpose | Access |
|---|---|---|
| Street Manager Open Data v7 | All street works permits in England | Free — register at manage-roadworks.service.gov.uk |
| OS Data Hub (NSG API) | USRN resolution | Free tier — 1M requests/month at osdatahub.os.uk |
| OS Open Roads (OGC API) | Road classification (A/B/C) | Free tier — 1M requests/month |
| OS Vector Tiles | UK road label overlay on Mapbox | Free tier — 1M requests/month |
| NUAR | Underground asset register | Apply at nuar.uk — currently using synthetic data |
| D-TRO Public Beta | Digital traffic regulation orders (v4.0.0) | DfT integration environment — synthetic fallback included |
| Mapbox | Map tiles, geocoding, 3D buildings | Free tier — 50k loads/month |
| Anthropic Claude | AI copilot reasoning | Usage-based pricing |

---

## Phase Roadmap

```
Phase 1 — Foundation & Open Data Ingestion          ✅ Complete   (9/9 modules)
Phase 2 — Corridor Risk Engine                      ✅ Complete   (7/7 modules)
Phase 3 — AI Copilot Layer                          ✅ Complete*  (7/7 — needs ANTHROPIC_API_KEY for live AI)
Phase 4 — NUAR Underground Risk                     ⚠  Partial    (5/8 — 3 deferred post-launch)
Phase 5 — Non-Compliance Analytics                  ✅ Complete*  (7/7 — needs ANTHROPIC_API_KEY for live AI)
Phase 6 — D-TRO Integration & Market Launch         ✅ Complete   (7/7 modules)
```

`*` Functionally complete with synthetic data and mock AI stream. Setting `ANTHROPIC_API_KEY` activates real Claude responses with zero code changes.

**Data modes:** All phases run fully on synthetic data today. Setting the relevant API key switches each domain to live data independently — no code changes required.

The current active phase is stored in `.phase` at the repo root:

```bash
cat .phase   # → 6
```

---

## Production Deployment

### Backend — Hetzner CX23

```bash
# On the server (Ubuntu 22.04)
curl -fsSL https://get.docker.com | sh

git clone <repo> /opt/streetsense
cd /opt/streetsense/infra

cp .env.prod.example .env.prod
# Edit .env.prod with production values

# Start Postgres + Redis, then bring up the full stack
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d postgres redis
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d nginx

# Get SSL certificate (first time only)
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm certbot \
  certonly --webroot --webroot-path /var/www/certbot \
  -d api.YOUR_DOMAIN --email YOUR_EMAIL --agree-tos --no-eff-email

# Reload nginx and bring up API + worker
docker compose -f docker-compose.prod.yml --env-file .env.prod exec nginx nginx -s reload
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

Migrations run automatically at container start via `entrypoint.sh`.

### Frontend — Vercel

1. Connect the repo at vercel.com
2. Set environment variables: `NEXT_PUBLIC_API_URL=https://api.YOUR_DOMAIN` plus all `NEXT_PUBLIC_*` and Clerk vars
3. Vercel auto-deploys on push to `main`

### After deploying

Update `PUBLIC_API_URL` in `.env.prod` to `https://api.YOUR_DOMAIN`, then notify the Street Manager onboarding team of the new webhook endpoints:

```
Permits:    https://api.YOUR_DOMAIN/webhooks/permits
Activities: https://api.YOUR_DOMAIN/webhooks/activities
Section 58: https://api.YOUR_DOMAIN/webhooks/section58
```

---

## AI Safety & Guardrails

The copilot endpoint is protected by a five-layer guardrail architecture. See [`AI_GUARDRAILS.md`](AI_GUARDRAILS.md) for the full threat model and upgrade paths.

| Layer | What it does | Where |
|-------|-------------|-------|
| **1 — Input Gate** | Rejects queries over 600 chars, prompt injection attempts, and off-topic requests (creative writing, code help, financial advice) | `apps/web/lib/copilot-guardrails.ts` |
| **2 — Topic Classifier** | Stub that always passes in mock mode; swap body for a Haiku single-turn call when `ANTHROPIC_API_KEY` is set | `copilot-guardrails.ts · classifyTopic()` |
| **3 — System Prompt Hardening** | Explicit domain scope, refusal templates, anti-extraction rules, and model-identity anchoring | `apps/api/services/agent.py` |
| **4 — Output Audit Flagging** | Scans each AI response for system-prompt leakage, PII, and guardrail-bypass signals. Sets `flagged + flag_reason` on the audit log row — does not suppress the response | `copilot-guardrails.ts · checkOutput()` |
| **5 — Rate Limiter** | 10 requests / 60 s per sessionId (sliding window). Module-level Map; Redis upgrade is a 1-file change | `guardInput()` in `copilot-guardrails.ts` |

Flagged interactions are highlighted in the `/audit` page for human review. The `ai_audit_log` table has `flagged` (bool, indexed) and `flag_reason` (varchar 64) columns added by migration `0006`.

---

## Architecture Decisions

Key decisions are recorded in `DECISIONS.md` (27 ADRs). Notable ones:

| ADR | Decision |
|---|---|
| ADR-002 | Map is the primary canvas — minimum 60% viewport at all times |
| ADR-007 | NUAR geometry never persisted — query on demand, cache 1 hour max |
| ADR-019 | Street Manager delivers via HTTP webhooks, not SNS/SQS |
| ADR-022 | Three-mode data strategy: Synthetic → Sandbox → Production |
| ADR-023 | Four-track NUAR strategy: schema conformance, synthetic, enquiry API, live application |
| ADR-026 | Street Manager uses JWT username/password auth — `token` header, not `Authorization: Bearer` |
| ADR-027 | D-TRO uses OAuth2 client credentials — token cached in Redis for 25 min (5-min buffer on 30-min TTL) |

---

## Licence

Licensed under the [Apache License 2.0](LICENSE).

Copyright 2026 Shadab Khan.

You are free to use, modify, and distribute this software under the terms of the Apache 2.0 licence. See the `LICENSE` file for the full text.
