# ROADMAP.md — StreetSense AI
> The at-a-glance view of what's being built, what's next, what's done.
> Update at the end of every working session.
> For deep specs, see `StreetSense_AI_Planning_Document.docx`.
>
> **Last reviewed:** May 2026
> **Current phase:** 1 (read `.phase` to confirm)

---

## This Week

**Active module:** Phase 1 — SM-007 (health dashboard endpoint)

**Working on:**
- [x] Scaffold complete monorepo structure
- [x] Next.js 15 + Tailwind v3.4.x + shadcn/ui frontend
- [x] FastAPI Python backend with uv
- [x] Docker Compose (PostgreSQL 16 + PostGIS, Redis 7)
- [x] SM-001: Street Manager webhook + SQS ingestion pipeline (19 tests)
- [x] SM-002: PostgreSQL + PostGIS data store, works repository (32 tests)
- [x] SM-003: USRN resolver via OS NSG API (15 tests)
- [ ] Register for API keys (Street Manager, OS Data Hub, Mapbox, Anthropic)
- [ ] Set up Railway + Vercel accounts

**Blocked by:**
- API key registrations (manual steps — developer must complete)

---

## Phase 1 — Foundation & Open Data Ingestion
**Target completion:** End of June 2026
**Status:** 🟡 In progress

### Modules
| ID | Module | Status | Blockers |
|----|--------|--------|----------|
| SM-001 | Street Manager Open Data stream subscriber (SNS/SQS) | 🟢 Done | — |
| SM-002 | PostgreSQL + PostGIS data store | 🟢 Done | — |
| SM-003 | USRN resolver via OS NSG / DataVia API | 🟢 Done | — |
| SM-004 | Road classification via OS Open Roads | 🟢 Done | — |
| SM-005 | 15-minute polling fallback (Celery) | 🟢 Done | — |
| SM-006 | FastAPI query endpoints (USRN, bbox, date range) | 🟢 Done | — |
| SM-007 | Health dashboard endpoint | ⚪ Not started | Depends on SM-006 |

### Phase 1 Success Criteria
- [ ] Ingestion latency < 5 minutes from Street Manager event
- [ ] USRN resolution accuracy > 95% on 1,000-row test sample
- [ ] API response time < 200ms for bounding-box query
- [ ] Uptime > 99% over 7-day rolling window

### Phase 1 Pre-Work (Do These First)
- [x] Scaffold monorepo (Next.js 15, FastAPI, docker-compose)
- [x] Tailwind v3.4.x design tokens configured — DESIGN.md Section 2.1
- [x] shadcn/ui 17 components installed
- [x] FastAPI skeleton with /health endpoint
- [x] docker-compose.yml — PostgreSQL 16 + PostGIS + Redis 7
- [x] .env.example committed (no real values)
- [ ] Register for Anthropic API key
- [ ] Register for Mapbox public token
- [ ] Register for OS Data Hub account
- [ ] Register for Street Manager API access (DfT)
- [ ] Set up GitHub repo with branch protection on `main`
- [ ] Set up Railway account for backend hosting
- [ ] Set up Vercel account linked to GitHub repo
- [ ] Create `.env.local` with all keys filled in

---

## Phase 2 — Corridor Risk Engine
**Target completion:** End of August 2026
**Status:** ⚪ Not started

### Modules
| ID | Module | Status |
|----|--------|--------|
| CR-001 | Corridor definition engine (segment A-roads, B-roads) | ⚪ Not started |
| CR-002 | Works clustering — spatial join to corridors | ⚪ Not started |
| CR-003 | Disruption risk scoring algorithm | ⚪ Not started |
| CR-004 | Risk classification (Low/Medium/High/Critical) | ⚪ Not started |
| CR-005 | Public map interface (Mapbox + corridor heat map) | ⚪ Not started |
| CR-006 | Corridor detail Sheet (click-to-expand) | ⚪ Not started |
| CR-007 | Time-window slider | ⚪ Not started |

### Phase 2 Launch Milestone
- [ ] Public demo URL live with synthetic data
- [ ] First LinkedIn build-in-public post
- [ ] 50 unique visitors in 2 weeks post-launch

---

## Phase 3 — AI Copilot Layer
**Target completion:** End of October 2026
**Status:** ⚪ Not started

### Modules
| ID | Module | Status |
|----|--------|--------|
| AI-001 | LangChain agent with Street Manager tools | ⚪ Not started |
| AI-002 | Conversational UI panel (Sheet from right) | ⚪ Not started |
| AI-003 | Grounded response engine with permit citations | ⚪ Not started |
| AI-004 | Suggested questions on load | ⚪ Not started |
| AI-005 | Scheduling advisor | ⚪ Not started |
| AI-006 | Plain-English permit summary tool | ⚪ Not started |
| AI-007 | Response audit trail logging | ⚪ Not started |

### Phase 3 Engagement Milestone
- [ ] Tag a Causeway / Northumberland highways figure in copilot demo post
- [ ] First reply or DM from Causeway team member

---

## Phase 4 — NUAR Underground Risk Integration
**Target completion:** End of December 2026
**Status:** ⚪ Not started

### Pre-Work (Apply Now — 8+ week lead time)
- [ ] Apply for NUAR access at nuar.uk
- [ ] Read NUAR Harmonised Data Model
- [ ] Review MUDDI UK Excavation Profile

### Modules
| ID | Module | Status |
|----|--------|--------|
| UN-001 | NUAR API integration (bbox queries) | ⚪ Not started |
| UN-002 | Asset density scorer | ⚪ Not started |
| UN-003 | Strike risk classification | ⚪ Not started |
| UN-004 | Permit-level risk overlay | ⚪ Not started |
| UN-005 | Plain-English risk explanation | ⚪ Not started |
| UN-006 | Composite score (surface + underground) | ⚪ Not started |
| UN-007 | Contractor alert system | ⚪ Not started |

---

## Phase 5 — Non-Compliance Analytics
**Target completion:** End of February 2027
**Status:** ⚪ Not started

### Modules
| ID | Module | Status |
|----|--------|--------|
| NC-001 | Promoter compliance scorer | ⚪ Not started |
| NC-002 | Authority compliance dashboard | ⚪ Not started |
| NC-003 | Offender league table | ⚪ Not started |
| NC-004 | 12-month trend analytics | ⚪ Not started |
| NC-005 | FPN opportunity detector | ⚪ Not started |
| NC-006 | Exportable compliance report (PDF/CSV) | ⚪ Not started |
| NC-007 | AI monthly compliance briefing | ⚪ Not started |

### Phase 5 Engagement Milestone
- [ ] Submit HAUC Convention 2027 abstract
- [ ] First formal Causeway product/commercial team conversation

---

## Phase 6 — D-TRO Integration & Market Launch
**Target completion:** End of April 2027
**Status:** ⚪ Not started

### Modules
| ID | Module | Status |
|----|--------|--------|
| DT-001 | D-TRO public beta data consumer | ⚪ Not started |
| DT-002 | Permit + TRO conflict detector | ⚪ Not started |
| DT-003 | Three-layer composite map view (SM + D-TRO + NUAR) | ⚪ Not started |
| DT-004 | Authority-facing accounts (Clerk auth) | ⚪ Not started |
| DT-005 | CausewayOne embeddable widget | ⚪ Not started |
| DT-006 | Public launch content (blog, LinkedIn, ADEPT/HAUC) | ⚪ Not started |
| DT-007 | Causeway commercial proposition deck | ⚪ Not started |

### Phase 6 Outcome Milestone
- [ ] 10 highway authority accounts created
- [ ] 1 article in Construction News, Highways News, or ITS International
- [ ] Formal partnership / licensing conversation with Causeway initiated

---

## Status Legend
- 🟢 Done — module shipped and verified against success criteria
- 🟡 In progress — actively being worked on this week
- 🟠 Blocked — waiting on external dependency
- 🔵 In review — implementation complete, success criteria being measured
- ⚪ Not started

---

## Sessions Log

> Append a one-line summary at the end of every working session.
> Format: `YYYY-MM-DD — what got done`

```
2026-05-09 — Created planning document, CLAUDE.md, DESIGN.md, ROADMAP.md, DECISIONS.md
2026-05-09 — Monorepo scaffolded — Phase 1 ready for module work (Next.js 15, FastAPI, docker-compose, shadcn, design tokens)
2026-05-10 — SM-001 complete — StreetManagerClient (async, Redis cache, tenacity retry), SQSConsumer, HTTP webhooks router, Celery Beat task, 19 tests green
2026-05-10 — SM-002 complete — StreetWork SQLAlchemy/PostGIS model, Alembic migration, works_repository (upsert/bbox/usrn), 32 tests green; ADRs 019-021 added
2026-05-10 — SM-003 complete — USRNResolver (OS NSG API, indefinite Redis cache, injectable httpx), OSNSGResponse schemas, USRNInfo domain model, 15 tests green (47 total)
2026-05-10 — SM-004 complete — RoadClassifier (OS Open Roads OGC Features API, 24h Redis cache, priority sort Motorway>A>B), RoadInfo domain model + TypeScript type, 19 tests green (66 total)
2026-05-10 — SM-005 complete — poll_sm_rest Celery task (15min Beat, Redis cursor, _do_rest_poll extracted for testability), poll_sm_sqs tests added, 10 tests green (76 total)
2026-05-10 — SM-006 complete — works router (/permit/:path, /bbox, /usrn, /authority), date range + limit added to get_works_by_bbox, camelCase verified, 15 tests green (91 total)
2026-05-10 — OS Data Hub OAuth migration — os_api_key replaced by os_client_id/os_client_secret, services/os_auth.py token manager (Redis-cached, 5 min buffer), all services updated to Bearer auth, 9 new tests (100 total)
```

---

*ROADMAP.md is updated at the end of every session. If a session goes by without
an entry in the Sessions Log, that session did not happen.*
