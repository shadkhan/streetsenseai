import { NextRequest } from 'next/server'

// Four mock permit summary templates — real implementation uses claude-haiku-4-5-20251001.
// Selected deterministically by last digit of permit sequence number.
const TEMPLATES = [
  // 0, 4, 8 — Highway authority resurfacing
  `This permit covers carriageway resurfacing works on a 220 m section of the A38 Bristol Road, Selly Oak, Birmingham. Submitted by Amey Plc on behalf of Birmingham City Council, the programme runs over 8 days with two-way traffic signals in operation between 07:00 and 19:00. A signed HGV diversion is in place via the A441.

Work type is classified as Standard. One lane in each direction will be maintained during off-peak hours. Permanent Category A reinstatement is included within the same programme.

The permit is currently Granted. Under the Traffic Management Act 2004, works must commence within 5 days of the proposed start date.`,

  // 1, 5, 9 — Utility installation
  `This permit covers the installation of new fibre-optic ducting beneath the footway on Corporation Street, Birmingham. Submitted by BT Openreach, the works span 6 days with a single lane closure on the westbound carriageway and temporary pedestrian barriers where the footway is affected.

The promoter has co-ordinated this programme with Birmingham City Council to avoid conflict with an adjacent gas mains scheme on Lower Bull Street. Work type is Standard.

The permit is currently Granted. All operatives hold valid NRSWA Unit 2 and Unit 10 competency cards as required under street works licence conditions.`,

  // 2, 6 — Immediate / emergency
  `This is an immediate permit for emergency repair of a fractured water main on the Hagley Road, Edgbaston. Submitted by Severn Trent Water, the works commenced within 2 hours of the fault being identified and are expected to complete within 48 hours.

A two-lane road closure with contra-flow is in operation; delays of up to 20 minutes are expected during morning and evening peaks. A Section 74 overrun charge will apply if works are not completed within the permitted duration.

The permit is currently In Progress. Immediate works notifications are submitted under Section 57 of the New Roads and Street Works Act 1991 without the standard advance notice requirement.`,

  // 3, 7 — Minor maintenance
  `This permit covers minor utility maintenance on a 15 m section of footway on New Street, Birmingham city centre. Submitted by Cadent Gas Ltd, the works are expected to complete within 3 days using give-and-take working, with no carriageway closure required.

The works fall within the Highway Authority's Traffic Sensitive designation for New Street and are therefore restricted to off-peak hours only (19:00–07:00). Work type is Minor.

The permit is currently Submitted and awaiting Highway Authority approval. The authority has a 5-day decision window under the Traffic Management Act 2004.`,
]

function pickTemplate(ref: string): string {
  const seq = ref.split('/')[2] ?? '0'
  const lastDigit = parseInt(seq.slice(-1) || '0', 10)
  return TEMPLATES[lastDigit % TEMPLATES.length]!
}

export async function GET(req: NextRequest) {
  const ref = req.nextUrl.searchParams.get('ref') ?? 'Unknown'
  const text = pickTemplate(ref)

  const encoder = new TextEncoder()
  const stream = new ReadableStream({
    async start(controller) {
      const tokens = text.match(/\S+|\s+/g) ?? []
      for (const token of tokens) {
        const line = JSON.stringify({ type: 'text', content: token }) + '\n'
        controller.enqueue(encoder.encode(line))
        await new Promise<void>((resolve) =>
          setTimeout(resolve, Math.random() * 35 + 20),
        )
      }
      controller.enqueue(encoder.encode(JSON.stringify({ type: 'done' }) + '\n'))
      controller.close()
    },
  })

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'Cache-Control': 'no-cache',
      'X-Accel-Buffering': 'no',
    },
  })
}
