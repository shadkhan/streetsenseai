import { type NextRequest } from 'next/server'
import type { PermitCitation } from '@/types'

// ── Mock response bank (AI-001 — replaced by LangChain agent when API key is present) ──

interface MockResponse {
  text: string
  citations: PermitCitation[]
  suggestedQuestions: string[]
}

const RESPONSES: Record<string, MockResponse> = {
  a38: {
    text: `The A38 corridor network shows elevated risk across two monitored segments in Birmingham City Centre.

A38 Corporation Street is currently rated high risk. Permit WG7/2026/04003821 (Cadent Gas Networks, major works, road closure) is active from 15 May to 2 June 2026. A concurrent permit WG7/2026/04003744 (BT Openreach, standard works, lane closure) creates a two-permit overlap at the Colmore Row junction from 15–20 May, compounding traffic management complexity.

A38 Bristol Road is medium risk, with permit WG7/2026/04003876 (Severn Trent Water, lane closure) scheduled 14–22 May 2026. No immediate scheduling conflicts are present on this segment.

Recommend monitoring the Corporation Street overlap closely — both permits have different traffic management schemes and may require a coordination meeting under TMA 2004 Section 59.`,
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

  clash: {
    text: `Analysing permit date overlaps across Birmingham corridors for the next 30 days.

The highest-priority scheduling conflict is on New Street between 19–21 May 2026. Permit WG7/2026/04003621 (Birmingham City Council, major works, road closure) overlaps with WG7/2026/04003699 (National Grid, immediate permit, two-way signals). Two concurrent works with separate traffic management schemes on the same 200-metre stretch creates an unmanageable conflict.

Under the Lane Rental Scheme, both promoters face potential penalty charges. Under Section 58 of the New Roads and Street Works Act 1991, the authority can restrict further works on New Street for up to 5 years after the City Council permit completes in July 2026.

I recommend issuing a coordination direction to National Grid to defer their emergency works until 28 May 2026, after the road closure lifts.`,
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

  newstreet: {
    text: `New Street is currently rated medium risk with one active permit in the section between Corporation Street and Stephenson Street.

Permit WG7/2026/04003512 (Birmingham City Council, standard works, two-way signals) has been in progress since 12 May 2026 for carriageway resurfacing. Estimated completion is 20 May 2026. No concurrent works are co-located within 100 metres during this period.

Bull Street and Broad Street both show low risk this week. Bull Street has permit WG7/2026/04003103 (Western Power Distribution, minor works, some incursion) completing 16 May — this has negligible traffic impact.

No FPN-triggering overruns are recorded on the New Street corridor in the last 90 days.`,
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

  default: {
    text: `Currently monitoring 5 corridors across Birmingham City Centre. Two are showing elevated risk this week.

A38 Corporation Street is rated high risk due to concurrent works from Cadent Gas Networks (permit WG7/2026/04003821) and BT Openreach (permit WG7/2026/04003744) creating overlapping lane closures from 15–20 May 2026.

New Street is medium risk with an in-progress resurfacing permit WG7/2026/04003512 completing 20 May.

Broad Street, Bull Street, and A38 Bristol Road are currently low risk. No scheduling conflicts are present on these corridors.

Overall, the Birmingham network is operating within normal disruption parameters. The most time-sensitive action is monitoring the A38 Corporation Street overlap — consider a promoter coordination meeting before 15 May.`,
    citations: [
      { permitReference: 'WG7/2026/04003821', streetName: 'A38 Corporation Street', promoter: 'Cadent Gas Networks', relevance: 'High impact, road closure, 15 May – 2 Jun' },
      { permitReference: 'WG7/2026/04003744', streetName: 'A38 Corporation Street', promoter: 'BT Openreach', relevance: 'Concurrent, lane closure, 15–20 May' },
      { permitReference: 'WG7/2026/04003512', streetName: 'New Street', promoter: 'Birmingham City Council', relevance: 'Resurfacing, in progress, completing 20 May' },
    ],
    suggestedQuestions: [
      "What's the risk on the A38 corridors?",
      'Are there any scheduling conflicts this week?',
      'Which promoter has the most active works?',
    ],
  },
}

function pickResponse(question: string): MockResponse {
  const q = question.toLowerCase()
  if (q.includes('a38') || q.includes('corporation') || q.includes('bristol road')) {
    return RESPONSES.a38
  }
  if (q.includes('clash') || q.includes('conflict') || q.includes('schedul') || q.includes('overlap')) {
    return RESPONSES.clash
  }
  if (q.includes('new street') || q.includes('bull') || q.includes('broad')) {
    return RESPONSES.newstreet
  }
  return RESPONSES.default
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export async function POST(request: NextRequest) {
  const body = await request.json() as { question: string }
  const response = pickResponse(body.question ?? '')

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
