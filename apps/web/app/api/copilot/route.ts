// TODO(phase-3): Streaming AI copilot endpoint — AI-001 through AI-007
import { type NextRequest } from 'next/server'

export async function POST(_request: NextRequest) {
  return new Response(JSON.stringify({ error: 'Not implemented — Phase 3' }), {
    status: 501,
    headers: { 'Content-Type': 'application/json' },
  })
}
