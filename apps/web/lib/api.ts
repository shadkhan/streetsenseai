import { useQuery } from '@tanstack/react-query'
import type { AuditLogEntry, Corridor, PermitCitation, SchedulingConflict } from '@/types'
import type { TimeWindow } from '@/lib/stores/map'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

function applyWindow(url: URL, timeWindow: TimeWindow | null): URL {
  if (timeWindow) {
    url.searchParams.set('start_date', timeWindow.startDate)
    url.searchParams.set('end_date', timeWindow.endDate)
  }
  return url
}

async function fetchCorridors(timeWindow: TimeWindow | null): Promise<Corridor[]> {
  const url = applyWindow(new URL(`${API_BASE}/corridors`), timeWindow)
  const res = await fetch(url.toString())
  if (!res.ok) throw new Error(`Failed to fetch corridors: ${res.status}`)
  return res.json() as Promise<Corridor[]>
}

async function fetchCorridor(id: string, timeWindow: TimeWindow | null): Promise<Corridor> {
  const url = applyWindow(new URL(`${API_BASE}/corridors/${id}`), timeWindow)
  const res = await fetch(url.toString())
  if (!res.ok) throw new Error(`Failed to fetch corridor: ${res.status}`)
  return res.json() as Promise<Corridor>
}

export function useCorridors(timeWindow: TimeWindow | null = null) {
  return useQuery({
    queryKey: ['corridors', timeWindow?.startDate ?? null, timeWindow?.endDate ?? null],
    queryFn: () => fetchCorridors(timeWindow),
    staleTime: 5 * 60 * 1000,
  })
}

export function useCorridor(id: string | null, timeWindow: TimeWindow | null = null) {
  return useQuery({
    queryKey: ['corridor', id, timeWindow?.startDate ?? null, timeWindow?.endDate ?? null],
    queryFn: () => fetchCorridor(id!, timeWindow),
    enabled: id !== null,
    staleTime: 60 * 1000,
  })
}

async function fetchConflicts(): Promise<SchedulingConflict[]> {
  const url = new URL(`${API_BASE}/scheduling/conflicts`)
  const res = await fetch(url.toString())
  if (!res.ok) throw new Error(`Failed to fetch conflicts: ${res.status}`)
  return res.json() as Promise<SchedulingConflict[]>
}

export function useConflicts() {
  return useQuery({
    queryKey: ['scheduling-conflicts'],
    queryFn: fetchConflicts,
    staleTime: 5 * 60 * 1000,
  })
}

// ── Audit Trail (AI-007) ──────────────────────────────────────────────────────

export async function logInteraction(entry: {
  interactionType: 'copilot' | 'permit_summary'
  query: string
  response: string
  citations?: PermitCitation[] | null
  sessionId?: string | null
}): Promise<void> {
  try {
    await fetch(`${API_BASE}/audit/log`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(entry),
    })
  } catch { /* best-effort — audit logging must never block the UI */ }
}

async function fetchAuditLogs(limit: number): Promise<AuditLogEntry[]> {
  const url = new URL(`${API_BASE}/audit/logs`)
  url.searchParams.set('limit', String(limit))
  const res = await fetch(url.toString())
  if (!res.ok) throw new Error(`Failed to fetch audit logs: ${res.status}`)
  return res.json() as Promise<AuditLogEntry[]>
}

export function useAuditLogs(limit = 50) {
  return useQuery({
    queryKey: ['audit-logs', limit],
    queryFn: () => fetchAuditLogs(limit),
    staleTime: 30 * 1000,
    refetchInterval: 30 * 1000,
  })
}
