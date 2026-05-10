# StreetSense AI

> Cross-Authority Roadworks Intelligence Platform

An AI-powered web application that turns UK open government roadworks data
into operational intelligence — corridor disruption risk scoring, underground
asset strike risk, non-compliance analytics, and a conversational AI copilot
for highway authority officers and permit managers.

Built on Street Manager open data, the D-TRO public beta, and NUAR —
delivering the cross-authority intelligence layer the DfT's own roadmap
won't ship until September 2027.

---

## Quick Start

```bash
# 1. Clone and install
git clone [repo]
cd streetsense

# 2. Environment
cp .env.example .env.local
# Fill in .env.local with your API keys

# 3. Start infrastructure
cd infra && docker-compose up -d   # PostgreSQL + Redis

# 4. Backend (uv-managed)
cd ../apps/api
uv sync
uv run alembic upgrade head
uv run uvicorn main:app --reload

# 5. Frontend (pnpm workspace)
cd ../web
pnpm install
pnpm dev
```

Open http://localhost:3000

---

## Data Sources

| Source | Purpose | Access | Used in Phase |
|--------|---------|--------|---------------|
| Street Manager Open Data v7 | All streetworks permits in England | Free, register at DfT | 1, 2, 3, 5, 6 |
| OS Data Hub — NSG | USRN resolution | Free, 1M req/month | 1+ |
| OS Open Roads | Road classification | Free download | 2 |
| OS Vector Tiles | UK road labels overlay | Free, 1M req/month | 2+ |
| NUAR | Underground asset data | Free, apply at nuar.uk | 4+ |
| D-TRO Public Beta | Digital traffic orders | Free, public beta | 6 |

---

## Project Docs
Still in Devlopment

## Current Phase

Read the `.phase` file at the repo root to see the active phase.
The current phase determines which modules are in scope.

```bash
cat .phase
# 1
```

---

## Licence

Private — not open source. All rights reserved.
