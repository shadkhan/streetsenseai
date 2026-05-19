import { useQuery } from '@tanstack/react-query'
import type {
  AssetDensity, AuditLogEntry, Corridor, CompositeRisk, ComplianceSummary,
  FPNOpportunity, MonthlyTrend, PermitCitation, PromoterCompliance,
  SchedulingConflict, StrikeRisk,
} from '@/types'
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

// ── Composite Risk (UN-006) ───────────────────────────────────────────────────

async function fetchCompositeRisk(corridorId: string): Promise<CompositeRisk> {
  const res = await fetch(`${API_BASE}/corridors/${corridorId}/composite-risk`)
  if (!res.ok) throw new Error(`Failed to fetch composite risk: ${res.status}`)
  return res.json() as Promise<CompositeRisk>
}

export function useCompositeRisk(corridorId: string | null) {
  return useQuery({
    queryKey: ['composite-risk', corridorId],
    queryFn: () => fetchCompositeRisk(corridorId!),
    enabled: corridorId !== null,
    staleTime: 5 * 60 * 1000,
  })
}

// ── NUAR Asset Density (UN-002) ──────────────────────────────────────────────

async function fetchAssetDensity(corridorId: string): Promise<AssetDensity> {
  const res = await fetch(`${API_BASE}/nuar/corridors/${corridorId}/density`)
  if (!res.ok) throw new Error(`Failed to fetch asset density: ${res.status}`)
  return res.json() as Promise<AssetDensity>
}

export function useAssetDensity(corridorId: string | null) {
  return useQuery({
    queryKey: ['asset-density', corridorId],
    queryFn: () => fetchAssetDensity(corridorId!),
    enabled: corridorId !== null,
    staleTime: 5 * 60 * 1000,
  })
}

// ── NUAR Strike Risk (UN-003) ─────────────────────────────────────────────────

async function fetchStrikeRisk(permitRef: string): Promise<StrikeRisk> {
  // permit references contain slashes (e.g. WG7/2025/04001234) — pass as path segments
  const res = await fetch(`${API_BASE}/nuar/permits/${permitRef}/strike-risk`)
  if (!res.ok) throw new Error(`Failed to fetch strike risk: ${res.status}`)
  return res.json() as Promise<StrikeRisk>
}

export function useStrikeRisk(permitRef: string | null) {
  return useQuery({
    queryKey: ['strike-risk', permitRef],
    queryFn: () => fetchStrikeRisk(permitRef!),
    enabled: permitRef !== null,
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

// ── Non-Compliance Analytics (NC-001 – NC-006) ────────────────────────────────

async function fetchComplianceSummary(): Promise<ComplianceSummary> {
  const res = await fetch(`${API_BASE}/compliance/summary`)
  if (!res.ok) throw new Error(`Failed to fetch compliance summary: ${res.status}`)
  return res.json() as Promise<ComplianceSummary>
}

export function useComplianceSummary() {
  return useQuery({
    queryKey: ['compliance-summary'],
    queryFn: fetchComplianceSummary,
    staleTime: 5 * 60 * 1000,
  })
}

async function fetchPromoters(region?: string): Promise<PromoterCompliance[]> {
  const url = new URL(`${API_BASE}/compliance/promoters`)
  if (region) url.searchParams.set('region', region)
  const res = await fetch(url.toString())
  if (!res.ok) throw new Error(`Failed to fetch promoters: ${res.status}`)
  return res.json() as Promise<PromoterCompliance[]>
}

export function usePromoters(region?: string) {
  return useQuery({
    queryKey: ['compliance-promoters', region ?? null],
    queryFn: () => fetchPromoters(region),
    staleTime: 5 * 60 * 1000,
  })
}

async function fetchFPNOpportunities(): Promise<FPNOpportunity[]> {
  const res = await fetch(`${API_BASE}/compliance/fpn-opportunities`)
  if (!res.ok) throw new Error(`Failed to fetch FPN opportunities: ${res.status}`)
  return res.json() as Promise<FPNOpportunity[]>
}

export function useFPNOpportunities() {
  return useQuery({
    queryKey: ['fpn-opportunities'],
    queryFn: fetchFPNOpportunities,
    staleTime: 5 * 60 * 1000,
  })
}

async function fetchMonthlyTrend(licenceNumber: string): Promise<MonthlyTrend[]> {
  const res = await fetch(
    `${API_BASE}/compliance/promoters/${encodeURIComponent(licenceNumber)}/monthly-trend`,
  )
  if (!res.ok) throw new Error(`Failed to fetch monthly trend: ${res.status}`)
  return res.json() as Promise<MonthlyTrend[]>
}

export function useMonthlyTrend(licenceNumber: string | null) {
  return useQuery({
    queryKey: ['monthly-trend', licenceNumber],
    queryFn: () => fetchMonthlyTrend(licenceNumber!),
    enabled: licenceNumber !== null,
    staleTime: 10 * 60 * 1000,
  })
}
