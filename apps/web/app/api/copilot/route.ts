import { type NextRequest, NextResponse } from 'next/server'
import { guardInput, checkOutput } from '@/lib/copilot-guardrails'
import type { PermitCitation } from '@/types'

// ── Mock response bank (AI-001 — replaced by LangChain agent when API key is present) ──

interface MockResponse {
  text: string
  citations: PermitCitation[]
  suggestedQuestions: string[]
}

const RESPONSES: Record<string, MockResponse> = {
  // ── A38 corridor ──────────────────────────────────────────────────────────────
  a38: {
    text: `The A38 corridor network shows elevated risk across two monitored segments in Birmingham City Centre.

A38 Corporation Street is currently rated **high risk** (score 78/100). Permit WG7/2026/04003821 (Cadent Gas Networks, major works, road closure) is active from 15 May to 2 June 2026. A concurrent permit WG7/2026/04003744 (BT Openreach, standard works, lane closure) creates a two-permit overlap at the Colmore Row junction from 15–20 May, compounding traffic management complexity.

A38 Bristol Road is **medium risk** (score 44/100), with permit WG7/2026/04003876 (Severn Trent Water, lane closure) scheduled 14–22 May 2026. No immediate scheduling conflicts are present on this segment.

Recommend monitoring the Corporation Street overlap closely — both permits have different traffic management schemes and may require a coordination meeting under TMA 2004 Section 59.

Based on Street Manager data · Updated ${new Date().toISOString()}`,
    citations: [
      { permitReference: 'WG7/2026/04003821', streetName: 'A38 Corporation Street', promoter: 'Cadent Gas Networks', relevance: 'Major works, road closure, 15 May – 2 Jun' },
      { permitReference: 'WG7/2026/04003744', streetName: 'A38 Corporation Street', promoter: 'BT Openreach', relevance: 'Standard works, lane closure, 15–20 May' },
      { permitReference: 'WG7/2026/04003876', streetName: 'A38 Bristol Road', promoter: 'Severn Trent Water', relevance: 'Lane closure, 14–22 May' },
    ],
    suggestedQuestions: [
      "What's the risk on New Street this week?",
      'Are there road closures planned after June?',
      'Show me all Cadent Gas Networks permits',
    ],
  },

  // ── Corridor risk overview ────────────────────────────────────────────────────
  corridors: {
    text: `Corridor risk overview for Birmingham City Centre — 5 monitored corridors:

**A38 Corporation Street** — High risk (78/100)
Concurrent works from Cadent Gas Networks (road closure) and BT Openreach (lane closure) overlap 15–20 May. Active TRO conflict: TTRO-2026-BCC-0041 restricts lane rental on this stretch. Underground strike risk: Critical (8 NUAR assets within 25m of WG7/2026/04003821).

**New Street** — Medium risk (52/100)
Birmingham City Council resurfacing (permit WG7/2026/04003512) in progress. No concurrent works. Section 58 protection window opens 20 May on completion.

**Broad Street** — Low risk (21/100)
No active works. One permit (WG7/2026/04003330, Western Power Distribution) planned from 28 May — minor incursion, two-way signals.

**Bull Street** — Low risk (18/100)
Permit WG7/2026/04003103 (Western Power Distribution, minor works) completing 16 May. No overrun risk detected.

**A38 Bristol Road** — Medium risk (44/100)
Severn Trent Water lane closure 14–22 May (WG7/2026/04003876). No conflicts. 3 NUAR assets within 25m — medium underground strike risk.

Based on Street Manager data · Updated ${new Date().toISOString()}`,
    citations: [
      { permitReference: 'WG7/2026/04003821', streetName: 'A38 Corporation Street', promoter: 'Cadent Gas Networks', relevance: 'High risk, road closure — concurrent overlap' },
      { permitReference: 'WG7/2026/04003512', streetName: 'New Street', promoter: 'Birmingham City Council', relevance: 'Medium risk, resurfacing in progress' },
      { permitReference: 'WG7/2026/04003876', streetName: 'A38 Bristol Road', promoter: 'Severn Trent Water', relevance: 'Medium risk, lane closure 14–22 May' },
    ],
    suggestedQuestions: [
      "Why is A38 Corporation Street rated high risk?",
      'Which corridor has the highest underground strike risk?',
      'Are there any Section 58 protections active?',
    ],
  },

  // ── Scheduling conflicts ──────────────────────────────────────────────────────
  clash: {
    text: `Analysing permit date overlaps across Birmingham corridors for the next 30 days.

The highest-priority scheduling conflict is on New Street between 19–21 May 2026. Permit WG7/2026/04003621 (Birmingham City Council, major works, road closure) overlaps with WG7/2026/04003699 (National Grid, immediate permit, two-way signals). Two concurrent works with separate traffic management schemes on the same 200-metre stretch creates an unmanageable conflict.

Under the Lane Rental Scheme, both promoters face potential penalty charges. Under Section 58 of the New Roads and Street Works Act 1991, the authority can restrict further works on New Street for up to 5 years after the City Council permit completes in July 2026.

I recommend issuing a coordination direction to National Grid to defer their emergency works until 28 May 2026, after the road closure lifts.

Based on Street Manager data · Updated ${new Date().toISOString()}`,
    citations: [
      { permitReference: 'WG7/2026/04003621', streetName: 'New Street', promoter: 'Birmingham City Council', relevance: 'Major works, road closure, 17 May – 4 Jul' },
      { permitReference: 'WG7/2026/04003699', streetName: 'New Street', promoter: 'National Grid', relevance: 'Immediate permit, two-way signals, 19–21 May' },
    ],
    suggestedQuestions: [
      'Which promoters have the most permit clashes?',
      'Can National Grid reschedule under TMA powers?',
      "What's the Section 58 protection period for New Street?",
    ],
  },

  // ── New Street / Broad Street / Bull Street ───────────────────────────────────
  newstreet: {
    text: `New Street is currently rated medium risk with one active permit in the section between Corporation Street and Stephenson Street.

Permit WG7/2026/04003512 (Birmingham City Council, standard works, two-way signals) has been in progress since 12 May 2026 for carriageway resurfacing. Estimated completion is 20 May 2026. No concurrent works are co-located within 100 metres during this period.

Bull Street and Broad Street both show low risk this week. Bull Street has permit WG7/2026/04003103 (Western Power Distribution, minor works, some incursion) completing 16 May — this has negligible traffic impact.

No FPN-triggering overruns are recorded on the New Street corridor in the last 90 days.

Based on Street Manager data · Updated ${new Date().toISOString()}`,
    citations: [
      { permitReference: 'WG7/2026/04003512', streetName: 'New Street', promoter: 'Birmingham City Council', relevance: 'Resurfacing, two-way signals, 12–20 May' },
      { permitReference: 'WG7/2026/04003103', streetName: 'Bull Street', promoter: 'Western Power Distribution', relevance: 'Minor works, some incursion, completing 16 May' },
    ],
    suggestedQuestions: [
      "What's the disruption score for the A38?",
      'Show me permits completing before 25 May',
      'Are there any overrunning works in Birmingham?',
    ],
  },

  // ── D-TRO / Traffic Regulation Orders ────────────────────────────────────────
  dtro: {
    text: `Active Digital Traffic Regulation Orders (D-TRO v4.0.0) for Birmingham — 14 orders currently in the monitored corridor network.

**Temporary TROs (TTROs) — 3 active:**

TTRO-2026-BCC-0041 (Birmingham City Council) — A38 Corporation Street, lane rental restriction. Valid 15 May – 2 Jun 2026. Conflicts with permit WG7/2026/04003821 (Cadent Gas Networks) — severity: **medium** (lane rental overlap, not a hard closure conflict).

TTRO-2026-BCC-0038 (Birmingham City Council) — New Street, temporary speed limit 20mph. Valid 12 May – 20 May 2026. Associated with resurfacing permit WG7/2026/04003512. No conflict detected.

TTRO-2026-NGrid-0012 (National Grid) — Broad Street, two-way signals. Valid 19–21 May 2026. Conflicts with WG7/2026/04003621 — severity: **critical** (competing traffic management on same stretch).

**Permanent TROs — notable:**
TRO-BCC-2024-081 — A38 Corporation Street, no loading 8am–6pm Mon–Sat (permanent). Referenced by 2 active permits.
TRO-BCC-2023-044 — New Street, pedestrianisation zone restrictions (permanent).

Based on D-TRO v4.0.0 data · Updated ${new Date().toISOString()}`,
    citations: [
      { permitReference: 'WG7/2026/04003821', streetName: 'A38 Corporation Street', promoter: 'Cadent Gas Networks', relevance: 'Conflicts with TTRO-2026-BCC-0041 (lane rental)' },
      { permitReference: 'WG7/2026/04003621', streetName: 'New Street', promoter: 'Birmingham City Council', relevance: 'Conflicts with TTRO-2026-NGrid-0012 (critical)' },
      { permitReference: 'WG7/2026/04003512', streetName: 'New Street', promoter: 'Birmingham City Council', relevance: 'Associated with TTRO-2026-BCC-0038 (speed limit)' },
    ],
    suggestedQuestions: [
      'Which permits have critical TRO conflicts?',
      'Show me all permanent TROs on the A38',
      'What is the D-TRO conflict severity on New Street?',
    ],
  },

  // ── Promoter compliance / most active ────────────────────────────────────────
  promoter: {
    text: `Promoter activity and compliance summary for Birmingham City Centre — last 90 days.

**Most active promoters (by permit count):**

1. **Cadent Gas Networks** — 23 permits, compliance score 71/100. Overrun rate 8.7% — 2 FPN opportunities flagged this month. 1 active major works permit (WG7/2026/04003821, A38 Corporation Street).

2. **Birmingham City Council** — 19 permits, compliance score 88/100. Strong track record. 0 overruns in last 30 days. Currently holds the highest-impact active permit (WG7/2026/04003621, New Street road closure).

3. **BT Openreach** — 17 permits, compliance score 65/100. Late start rate 12.4% — highest in the monitored network. Recommend scrutiny on permit WG7/2026/04003744 (A38 Corporation Street, lane closure, active from 15 May).

4. **Severn Trent Water** — 14 permits, compliance score 82/100. Stable trend. Active lane closure on A38 Bristol Road (WG7/2026/04003876).

5. **Western Power Distribution** — 11 permits, compliance score 79/100. No current FPN exposure.

Under the Lane Rental Scheme, Cadent Gas Networks and BT Openreach are the highest-cost promoters this quarter.

Based on Street Manager data · Updated ${new Date().toISOString()}`,
    citations: [
      { permitReference: 'WG7/2026/04003821', streetName: 'A38 Corporation Street', promoter: 'Cadent Gas Networks', relevance: 'Major works — 2 FPN opportunities flagged' },
      { permitReference: 'WG7/2026/04003744', streetName: 'A38 Corporation Street', promoter: 'BT Openreach', relevance: 'Late start risk — compliance score 65/100' },
      { permitReference: 'WG7/2026/04003621', streetName: 'New Street', promoter: 'Birmingham City Council', relevance: 'Highest-impact active permit, good compliance' },
    ],
    suggestedQuestions: [
      'Show me all Cadent Gas Networks overruns',
      'Which promoters are eligible for FPNs this month?',
      "What's BT Openreach's compliance trend over 12 months?",
    ],
  },

  // ── NUAR underground assets ───────────────────────────────────────────────────
  underground: {
    text: `Underground asset strike risk assessment for active permits in Birmingham City Centre.

**Critical strike risk:**
Permit WG7/2026/04003821 (Cadent Gas Networks, A38 Corporation Street) — 8 NUAR assets within 25m. Asset mix: 2 × gas (medium pressure), 3 × electric (11kV), 2 × telecoms, 1 × water. Highest-risk asset: 11kV electricity cable at 0.6m depth (operator: National Grid). Overall strike risk: **Critical**.

**High strike risk:**
Permit WG7/2026/04003699 (National Grid, New Street) — 6 NUAR assets within 25m. 2 × gas, 2 × water, 2 × telecoms. Minimum depth recorded: 0.4m. Strike risk: **High**.

**Medium strike risk:**
Permit WG7/2026/04003876 (Severn Trent Water, A38 Bristol Road) — 3 NUAR assets within 25m. Strike risk: **Medium**.

Permits WG7/2026/04003512 and WG7/2026/04003103 show low underground strike risk (0–1 assets within 25m).

All strike risk scores use the composite formula: 60% surface corridor risk + 40% underground asset density.

Based on NUAR synthetic data (Ordnance Survey) · Updated ${new Date().toISOString()}`,
    citations: [
      { permitReference: 'WG7/2026/04003821', streetName: 'A38 Corporation Street', promoter: 'Cadent Gas Networks', relevance: 'Critical underground strike risk — 8 NUAR assets, 11kV cable at 0.6m' },
      { permitReference: 'WG7/2026/04003699', streetName: 'New Street', promoter: 'National Grid', relevance: 'High underground strike risk — 6 assets, min depth 0.4m' },
      { permitReference: 'WG7/2026/04003876', streetName: 'A38 Bristol Road', promoter: 'Severn Trent Water', relevance: 'Medium underground strike risk — 3 assets' },
    ],
    suggestedQuestions: [
      'What assets are under A38 Corporation Street?',
      'Which active permits have critical strike risk?',
      'Show me gas pipe locations near New Street works',
    ],
  },

  // ── General overview (fallback) ───────────────────────────────────────────────
  default: {
    text: `Currently monitoring 5 corridors across Birmingham City Centre. Here is today's operational summary.

**Risk overview:**
- A38 Corporation Street — High risk (78/100) — concurrent works, TRO conflict
- New Street — Medium risk (52/100) — resurfacing in progress
- A38 Bristol Road — Medium risk (44/100) — Severn Trent Water lane closure
- Broad Street — Low risk (21/100)
- Bull Street — Low risk (18/100)

**Active permits:** 12 granted, 3 in progress, 2 submitted awaiting decision.

**Alerts:** 1 critical TRO conflict (New Street — National Grid vs BCC road closure). 1 permit with critical underground strike risk (WG7/2026/04003821, A38 Corporation Street). BT Openreach showing elevated late-start rate (12.4%).

**Recommended actions:** Monitor A38 Corporation Street overlap 15–20 May. Consider Section 58 protection on New Street after permit WG7/2026/04003512 completes 20 May.

Based on Street Manager data · Updated ${new Date().toISOString()}`,
    citations: [
      { permitReference: 'WG7/2026/04003821', streetName: 'A38 Corporation Street', promoter: 'Cadent Gas Networks', relevance: 'High risk — concurrent overlap + critical underground strike' },
      { permitReference: 'WG7/2026/04003744', streetName: 'A38 Corporation Street', promoter: 'BT Openreach', relevance: 'Concurrent, lane closure, late-start risk' },
      { permitReference: 'WG7/2026/04003512', streetName: 'New Street', promoter: 'Birmingham City Council', relevance: 'Resurfacing, completing 20 May — S58 opportunity' },
    ],
    suggestedQuestions: [
      "What's the risk breakdown for each corridor?",
      'Are there any D-TRO conflicts this week?',
      'Which promoter has the most active works?',
    ],
  },
}

// ── Response picker ────────────────────────────────────────────────────────────

function pickResponse(question: string): MockResponse {
  const q = question.toLowerCase()

  // D-TRO / Traffic Regulation Orders
  if (/d-?tro|traffic\s+regulation|regulation\s+order|\bttro\b|\btro\b/.test(q)) {
    return RESPONSES.dtro
  }

  // Underground / NUAR / strike risk
  if (/underground|nuar|asset|strike\s+risk|cable|pipe|duct|utility\s+asset/.test(q)) {
    return RESPONSES.underground
  }

  // Promoter compliance / most active / FPN
  if (/promoter|compliance|overrun|\bfpn\b|most\s+active|penalty|licence/.test(q)) {
    return RESPONSES.promoter
  }

  // Scheduling conflicts / clashes
  if (/clash|conflict|schedul|overlap|coordinat/.test(q)) {
    return RESPONSES.clash
  }

  // A38 specific
  if (/a38|corporation\s+street|bristol\s+road/.test(q)) {
    return RESPONSES.a38
  }

  // New Street / Broad Street / Bull Street
  if (/new\s+street|bull\s+street|broad\s+street/.test(q)) {
    return RESPONSES.newstreet
  }

  // Corridor risk overview (any mention of corridors or risk levels/scores)
  if (/corridor|risk\s+(level|score|overview|breakdown|rating|all)|all\s+corridor|network\s+risk/.test(q)) {
    return RESPONSES.corridors
  }

  return RESPONSES.default
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

// ── Route handler ──────────────────────────────────────────────────────────────

export async function POST(request: NextRequest) {
  const body = await request.json() as { question: string; sessionId?: string }
  const question = body.question ?? ''
  const sessionId = body.sessionId ?? 'anonymous'

  // Layer 1 + 5 — input gate and rate limiter
  const guard = guardInput(question, sessionId)
  if (!guard.allowed) {
    const status = guard.status === 'rate_limited' ? 429 : 400
    return NextResponse.json(
      { error: guard.status, message: guard.message },
      { status },
    )
  }

  const response = pickResponse(question)

  // Layer 4 — output audit: check assembled response before streaming
  const flagReason = checkOutput(response.text)
  const flagged = flagReason !== null

  // Tokenise preserving whitespace so newlines stream through correctly
  const tokens = response.text.match(/\S+|\s+/g) ?? []
  const enc = new TextEncoder()

  const stream = new ReadableStream({
    async start(controller) {
      for (const token of tokens) {
        controller.enqueue(enc.encode(JSON.stringify({ type: 'text', content: token }) + '\n'))
        // Vary delay: faster on whitespace, realistic on words
        await sleep(token.trim() ? 45 + Math.random() * 35 : 10)
      }

      controller.enqueue(enc.encode(
        JSON.stringify({
          type: 'meta',
          citations: response.citations,
          suggestedQuestions: response.suggestedQuestions,
          dataTimestamp: new Date().toISOString(),
          flagged,
          flagReason,
        }) + '\n'
      ))
      controller.enqueue(enc.encode(JSON.stringify({ type: 'done' }) + '\n'))
      controller.close()
    },
  })

  return new Response(stream, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  })
}
