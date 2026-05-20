# StreetSense AI — Build Status
> Last updated: 2026-05-20
> Current phase: 5 (read `.phase` to confirm)
> Tests passing: 119+ backend · 0 TS errors frontend

---

## Phase 1 — Foundation & Open Data Ingestion ✅ Complete
**9/9 modules done · 119 tests · All passing**

| Module | What it does |
|--------|-------------|
| SM-001 | Street Manager SNS/SQS subscriber + webhook ingestion |
| SM-002 | PostgreSQL/PostGIS data store + works repository |
| SM-003 | USRN resolver (OS NSG API, indefinite Redis cache) |
| SM-004 | Road classifier (OS Open Roads OGC API) |
| SM-005 | 15-min polling fallback via Celery Beat |
| SM-006 | FastAPI query endpoints (USRN, bbox, date range) |
| SM-007 | `/health/detail` system health endpoint |
| SM-008 | Synthetic data generator — 5,045-record deterministic fixture |
| UN-001-prep | NUAR Harmonised Data Model schema in PostGIS (4 tables) |

**Pending (manual):** API key registrations, Railway/Vercel account setup.

---

## Phase 2 — Corridor Risk Engine ✅ Complete
**7/7 modules done**

| Module | What it does |
|--------|-------------|
| CR-001 | Corridor definition engine (A/B/C road segments) |
| CR-002 | Works-to-corridor spatial join (ST_DWithin) |
| CR-003 | Weighted disruption risk scoring (0–100) |
| CR-004 | Risk classification (Low/Medium/High/Critical) |
| CR-005 | Mapbox map with corridor heat map, hover popup, click |
| CR-006 | Corridor detail Sheet (risk factors, concurrent works, composite score) |
| CR-007 | Time-window filter control (Today / 7 / 30 days) |

**Phase 2 milestone pending:** Public demo URL, first LinkedIn post.

---

## Phase 3 — AI Copilot Layer ✅ Functionally Complete (mocked)
**6/7 modules fully done · 1 module needs real API key**

| Module | Status | Notes |
|--------|--------|-------|
| AI-001 | Mock | Word-by-word mock stream works; swap `ANTHROPIC_API_KEY` to go live |
| AI-002 | Done | CopilotSheet (480px slide-in, streaming UI) |
| AI-003 | Done | Grounded responses with permit citations |
| AI-004 | Done | Suggested follow-up questions |
| AI-005 | Done | Scheduling Advisor (pairwise conflict detector) |
| AI-006 | Done | Plain-English permit summary Sheet |
| AI-007 | Done | Full audit trail (DB log + `/audit` page with 30s refresh) |

---

## Phase 4 — NUAR Underground Risk ⚠️ Partially Complete
**5/8 modules done · 3 deferred**

| Module | Status | Notes |
|--------|--------|-------|
| UN-008 | Done | Synthetic generator (395 assets, 6 owners, 15 types) |
| UN-002 | Done | Asset density scorer (0–100, ST_DWithin 100m) |
| UN-003 | Done | Permit strike risk (25m buffer, 5-min cache) |
| UN-004 | Done | Inline strike risk badge on each work card |
| UN-006 | Done | Composite score (60% surface + 40% underground, CorridorSheet) |
| UN-001 | Not started | Live NUAR API integration (waiting for access grant) |
| UN-005 | Deferred | Plain-English risk explanation — resume after Phase 5 |
| UN-007 | Deferred | Contractor alert system — resume after Phase 5 |
| UN-009 | Deferred | NUAR Proposed Works Enquiry API client — resume after Phase 5 |

---

## Phase 5 — Non-Compliance Analytics ✅ Functionally Complete (mocked)
**7/7 modules done**

| Module | Status | Notes |
|--------|--------|-------|
| NC-001 | Done | Promoter compliance scorer (overrun/late-start/reinstatement) |
| NC-002 | Done | Authority compliance dashboard with stats cards |
| NC-003 | Done | Offender league table (sortable, click-to-expand trend) |
| NC-004 | Done | 12-month trend sparklines per promoter |
| NC-005 | Done | FPN opportunity detector (overrun works list) |
| NC-006 | Done | CSV export endpoint |
| NC-007 | Mock | AI briefing stream — swap `ANTHROPIC_API_KEY` to go live |

---

## Phase 6 — D-TRO Integration & Launch ⚪ Not Started
**0/7 modules · Target April 2027**

| Module | Status |
|--------|--------|
| DT-001 | Not started — D-TRO public beta consumer |
| DT-002 | Not started — Permit + TRO conflict detector |
| DT-003 | Not started — Three-layer composite map (SM + D-TRO + NUAR) |
| DT-004 | Not started — Authority-facing accounts (Clerk auth) |
| DT-005 | Not started — CausewayOne embeddable widget |
| DT-006 | Not started — Public launch content (blog, LinkedIn, ADEPT/HAUC) |
| DT-007 | Not started — Causeway commercial proposition deck |

> D-TRO public beta confirmed September 2027 on the DfT roadmap. Building ahead
> of their own timeline is the strategic window for StreetSense AI.

---

## Additional Features Built (beyond module spec)

| Feature | Description |
|---------|-------------|
| 3D Map | Mapbox streets-v12 with 3D buildings, fog/atmosphere, pitch 45° |
| Map Style Control | Streets / Dark / Satellite switcher + 2D/3D toggle (top-left) |
| Location Search | Mapbox Forward Geocoding (GB-restricted), flyTo on selection |
| Muted Risk Colours | Replaced neon palette with professional deep greens/ambers/crimsons |
| Tooltips / Hints | Every action button, nav link, column header, and badge has help text |
| Admin Console | `/admin` — 4-tab dashboard: API health + live testing, data source config, loaded data stats, system info |
| Auth Guard | Next.js middleware cookie-based session protecting `/admin/*` |
| Analytics Breadcrumb | Header + `Map → Analytics` breadcrumb on analytics page |
| SM JWT Auth (ADR-026) | fix(auth): SM-001 JWT authentication — SM_EMAIL/SM_PASSWORD replaces STREET_MANAGER_API_KEY; id_token cached 55 min in Redis, refresh on 401 |

---

## Priority Action Plan

| Priority | Action | What it unlocks |
|----------|--------|----------------|
| 🔴 Highest | Set `ANTHROPIC_API_KEY` in `.env.local` | AI-001 + NC-007 go live — zero code changes needed |
| 🔴 Highest | Deploy backend to **Hetzner CX23** + frontend to **Vercel** | Phase 2 public demo milestone, LinkedIn post |
| 🔴 Highest | Get a domain, point DNS → Hetzner IP, run Certbot | Enables HTTPS; required before SM team re-registers production webhook URLs |
| 🟡 High | Update `PUBLIC_API_URL` in `infra/.env.prod` → notify SM onboarding team of new webhook URLs | Live permit event delivery to production server |
| 🟡 High | Register `OS_CLIENT_ID/SECRET`, `NEXT_PUBLIC_MAPBOX_TOKEN` in `infra/.env.prod` | Real OS data + map tiles in production |
| 🟡 High | Confirm SM REST API credentials with onboarding team (separate from webhook delivery) | Admin API health probe turns green; on-demand permit queries |
| 🟡 High | Complete UN-005, UN-007, UN-009 | Closes Phase 4 fully |
| 🟢 When ready | Start Phase 6 DT-001 | D-TRO consumer (can build against public beta spec now) |

> The three mocked pieces (AI-001, NC-007, UN-001) all become real the moment
> the corresponding API keys are configured. Zero code changes required.
> API key registrations are the single highest-leverage action right now.

---

## Test Count Summary

| Layer | Tests |
|-------|-------|
| SM-001 (Street Manager ingestion) | 19 |
| SM-002 (Data store) | 32 |
| SM-003 (USRN resolver) | 15 |
| SM-004 (Road classifier) | 19 |
| SM-005 (Polling fallback) | 10 |
| SM-006 (Query endpoints) | 15 |
| SM-007 (Health endpoint) | 8 |
| UN-001-prep (NUAR schema) | 8 |
| UN-008 (NUAR synthetic) | 14 |
| UN-002 (Asset density) | 18 |
| UN-003 (Strike risk) | 22 |
| Compliance (NC-001–006) | 20 |
| UN-006 (Composite risk) | 16 |
| **Total backend** | **216** |
| **Frontend TypeScript** | **0 errors** |
