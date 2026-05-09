# DECISIONS.md — StreetSense AI

> **Architecture Decision Log.** Every non-obvious technical or product
> decision is recorded here with date, context, and reasoning.
>
> **Why this file exists:** In six months, neither you nor Claude Code will
> remember why something was decided. Without this log, you will accidentally
> reverse decisions or re-debate them. Read this before changing anything
> structural.
>
> **How to add a new decision:**
> 1. Pick the next ADR number (sequential, never reused)
> 2. One-line title that summarises the decision
> 3. Status: Accepted / Superseded by ADR-NNN / Deprecated
> 4. Three short sections: Context, Decision, Consequences
> 5. Keep it tight — five to ten lines per ADR is the sweet spot

---

## ADR-001 — Build entirely on UK open government data
**Date:** 2026-05-09
**Status:** Accepted

**Context:** Causeway Technologies' commercial APIs are not publicly
accessible. Independent builders cannot pitch products that require
Causeway data they do not yet have access to.

**Decision:** Use only Street Manager Open Data (DfT), D-TRO public beta,
NUAR public access, OS Data Hub free tier. No Causeway commercial agreement
needed for any phase 1–6 module.

**Consequences:** Product is publicly demoable from day one. Independent
of Causeway's roadmap. Any developer can verify our claims by checking
the same APIs. Removes commercial-licence cost and gatekeeping risk.

---

## ADR-002 — Map is the primary canvas, not a widget
**Date:** 2026-05-09
**Status:** Accepted

**Context:** Existing highways products (Street Manager UI, one.network,
Causeway Alloy) treat the map as a container with controls beside it.
The data is the content, the map is the frame.

**Decision:** Map occupies minimum 60% of viewport at all times. All other
UI elements (Sheets, controls, legends) overlay the map via `position:
absolute` and z-index. Sheets never resize the map.

**Consequences:** Visually distinctive vs every competitor. Forces every
interaction to start from a spatial context. Mobile layout becomes harder
(deferred to Phase 3+). Layout flexibility for analytics page only — that
is the one full-width non-map view.

---

## ADR-003 — Sheet conflict resolution: mutual exclusivity
**Date:** 2026-05-09
**Status:** Accepted

**Context:** The Corridor Sheet (420px) and Copilot Sheet (480px) both
slide in from the right. If a user opens the corridor panel, then triggers
the copilot, what should happen? Stacking, side-by-side, or replace?

**Decision:** Mutually exclusive — opening one closes the other instantly.
Single Zustand store (`lib/stores/panels.ts`) tracks `active: 'none' |
'corridor' | 'copilot'`. No animation chaining.

**Consequences:** Simpler state, simpler interaction model. Loses the
ability to ask the copilot a question while looking at corridor details
(future improvement: copilot accepts an active corridor as context when
opened from a corridor sheet). Acceptable trade-off for MVP simplicity.

---

## ADR-004 — Tailwind v3.4.x, not v4
**Date:** 2026-05-09
**Status:** Accepted

**Context:** Tailwind v4 is generally available with significantly
different config approach (`@theme` directive instead of
`tailwind.config.ts`). shadcn/ui's canonical setup is still v3-based as
of May 2026.

**Decision:** Lock at v3.4.x. Migrate to v4 only after Phase 6 ships.

**Consequences:** Stable, well-documented stack. shadcn components work
out of the box. Migration to v4 will require config rewrite later (one
focused day of work). Worth deferring.

---

## ADR-005 — Python tooling: uv + pyproject.toml, never requirements.txt
**Date:** 2026-05-09
**Status:** Accepted

**Context:** Python project dependency management has fragmented options:
pip + requirements.txt, Poetry, PDM, uv. Need to pick one and stick with it.

**Decision:** uv with pyproject.toml. If a `requirements.txt` is needed
for deployment (e.g. Railway buildpack), generate it via `uv export`.

**Consequences:** Faster installs (uv is significantly faster than pip).
Modern lockfile format. No two-source-of-truth confusion. Slight learning
curve if Claude Code defaults to `pip install` — CLAUDE.md §11 forbids it.

---

## ADR-006 — Colour token name: `line` not `border`
**Date:** 2026-05-09
**Status:** Accepted

**Context:** Initial DESIGN.md v1.0 named the divider colour group `border`
(`border.DEFAULT`, `border.strong`). This clashes with Tailwind's
`border-*` width utilities — `border-strong` is ambiguous (colour or width?).

**Decision:** Rename to `line`. Use as `border-line` for divider colour,
`border-2` for width — no collision.

**Consequences:** Slightly less obvious naming, but unambiguous.
Documented in DESIGN.md §2.2 with rationale.

---

## ADR-007 — NUAR asset geometry never persisted in our database
**Date:** 2026-05-09
**Status:** Accepted

**Context:** NUAR contains over 3 million km of underground asset data
across 350+ asset owners. The data is sensitive (security and commercial
implications), licensed for specific purposes, and updates frequently.

**Decision:** Query NUAR on demand via API. In-memory cache for 1 hour
maximum. Never write asset geometry or location to PostgreSQL. Store only
the derived `StrikeRisk` score per permit reference.

**Consequences:** Cannot do offline NUAR queries. Slightly higher API
costs at scale. Avoids licence violation risk, avoids stale data, avoids
storing security-sensitive data we are not authorised to keep.

---

## ADR-008 — Corridors are LineString-only in the type system
**Date:** 2026-05-09
**Status:** Accepted

**Context:** Initial type definition allowed `Corridor.geometry` to be
`Point | LineString`. This is logically wrong — a corridor by definition
is a linear segment of road, not a single point.

**Decision:** Type `CorridorGeometry = LineStringGeometry` strictly.
Works can be Point or LineString (`WorksGeometry`), corridors never.
TypeScript enforces this at compile time.

**Consequences:** Compile-time guarantee against the bug class of
"point treated as corridor". Slight verbosity in type definitions.

---

## ADR-009 — Local geometry types, no @types/geojson dependency
**Date:** 2026-05-09
**Status:** Accepted

**Context:** Standard approach uses `@types/geojson` for `GeoJSON.Point`
etc. This adds a dependency for what is ultimately three small interfaces.

**Decision:** Define `Position`, `PointGeometry`, `LineStringGeometry`
locally in `types/index.ts`. Compatible with the GeoJSON spec — Mapbox
accepts these directly.

**Consequences:** One less dependency. Full control over the types.
If we later add `Polygon` (e.g. for authority boundaries), we add it
ourselves — minor cost.

---

## ADR-010 — Phase tracking via single-line `.phase` file
**Date:** 2026-05-09
**Status:** Accepted

**Context:** Claude Code needs to know the active phase to avoid building
out-of-scope features. Hardcoding the phase in CLAUDE.md means manual
edits at every transition, which we will forget.

**Decision:** Single-line `.phase` file at repo root containing just the
phase number (1–6). Claude Code reads it at session start. Developer
advances by writing a new number to it.

**Consequences:** Trivially simple. Git-tracked, so phase advancement is
visible in history. Forces deliberate phase transitions. Cannot
automatically progress (which is correct — phase advancement requires
exit-criteria validation).

---

## ADR-011 — Map base: Mapbox Standard + OS Vector Tile labels
**Date:** 2026-05-09
**Status:** Accepted

**Context:** Mapbox Standard alone has generic global road labels. UK
highway officers expect authoritative UK road labelling (motorway numbers,
local road names) which OS provides.

**Decision:** Mapbox Standard as base canvas. OS Vector Tiles overlaid for
road labels via the `roadname` source layer. OS attribution required.

**Consequences:** Dual data dependency — fails gracefully if OS tiles fail
(map still works, labels missing). Two API keys needed. Better professional
appearance for target users.

---

## ADR-012 — Single LLM provider: Anthropic Claude
**Date:** 2026-05-09
**Status:** Accepted

**Context:** Could use OpenAI, Anthropic, Google, or open-source models.
Multi-provider abstraction adds complexity for limited benefit at MVP stage.

**Decision:** Anthropic Claude only. Sonnet 4 (claude-sonnet-4-20250514)
for copilot reasoning. Haiku 4.5 (claude-haiku-4-5-20251001) for permit
summaries and quick lookups.

**Consequences:** Vendor lock-in risk. Mitigated by LangChain abstraction
making swap feasible later. Single API key, single billing relationship,
simpler ops. Re-evaluate if pricing changes materially.

---

## ADR-013 — Strategic dual-document structure: planning doc + CLAUDE.md
**Date:** 2026-05-09
**Status:** Accepted

**Context:** Risk of duplication between the deep planning document
(StreetSense_AI_Planning_Document.docx) and CLAUDE.md.

**Decision:** Planning doc = the **PRD/specs** (deep, infrequent reads,
phase definitions, success metrics, problem statements). CLAUDE.md =
the **architecture rules** (read every session, code-level rules,
type definitions, do/don't lists). No content duplicated between them.

**Consequences:** Two files to maintain, but each has a clear distinct
purpose. Planning doc is for strategic review, CLAUDE.md is for daily
session input.

---

## ADR-014 — No authentication until Phase 6
**Date:** 2026-05-09
**Status:** Accepted

**Context:** Adding auth early creates significant complexity (user
sessions, password reset, role permissions, multi-tenancy). The product
is a public read-only tool for Phases 1–5 — no user-specific data.

**Decision:** No login, no accounts, no auth in Phases 1–5. Public access
only. Phase 6 introduces authority accounts for saved corridors and
custom alerts.

**Consequences:** Faster Phase 1–5 development. Anyone can demo the tool
without credentials, including Causeway leadership. Phase 6 auth is a
clean greenfield addition rather than a retrofit.

---

## ADR-015 — Streaming AI responses via Next.js Route Handler ReadableStream
**Date:** 2026-05-09
**Status:** Accepted

**Context:** AI copilot responses can take 3–10 seconds. Showing a static
loading state for that duration feels broken. Multiple ways to stream:
Server-Sent Events, WebSockets, or fetch-based ReadableStream.

**Decision:** Use Next.js App Router route handler returning a
`ReadableStream`. Frontend consumes via `fetch` + `response.body.getReader()`.
No fake streaming via setTimeout — real token-by-token streaming.

**Consequences:** Standard HTTP (no WebSocket infrastructure needed).
Works with Vercel edge runtime. Slightly more complex client code, but
the streaming UX is the trust-building feature — it has to be real.

---

## ADR-016 — Permit references rendered as monospace inline citations
**Date:** 2026-05-09
**Status:** Accepted

**Context:** AI responses must be verifiable. Plain-text mentions of permit
references are easy to miss in flowing prose. Need a visual pattern that
flags every fact as auditable.

**Decision:** Every permit reference (pattern: `[A-Z0-9]+/\d{4}/\d+`) in
AI responses is rendered via the `<PermitReference>` component — monospace
font, slate blue background chip. Done via regex split in
`CopilotMessage.tsx`.

**Consequences:** Visual signal that the AI is making a specific, citable
claim. Failure mode: AI responses that should cite a permit but do not are
visibly less authoritative — pressures the system prompt and grounding
quality. Acceptable.

---

## Template for New ADRs

```
## ADR-NNN — [One-line title]
**Date:** YYYY-MM-DD
**Status:** Accepted | Superseded by ADR-NNN | Deprecated

**Context:** [What problem or question prompted this decision?]

**Decision:** [What was decided? Be specific.]

**Consequences:** [What does this enable, prevent, or trade off?]
```

---

*DECISIONS.md is append-only. Never delete an ADR — supersede it.*
*If a decision changes, add a new ADR and mark the old one "Superseded by ADR-NNN".*
*Last updated: 2026-05-09 | 16 ADRs recorded*
