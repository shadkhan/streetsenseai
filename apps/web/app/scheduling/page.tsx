'use client'

import { useState } from 'react'
import { Header } from '@/components/layout/Header'
import { ConflictCard } from '@/components/scheduling/ConflictCard'
import { PermitSummarySheet } from '@/components/copilot/PermitSummarySheet'
import { useConflicts } from '@/lib/api'
import { cn } from '@/lib/utils'
import type { RiskLevel } from '@/types'

const SEVERITY_FILTERS: Array<{ label: string; value: RiskLevel | 'all' }> = [
  { label: 'All', value: 'all' },
  { label: 'Critical', value: 'critical' },
  { label: 'High', value: 'high' },
  { label: 'Medium', value: 'medium' },
  { label: 'Low', value: 'low' },
]

export default function SchedulingPage() {
  const [severityFilter, setSeverityFilter] = useState<RiskLevel | 'all'>('all')
  const [search, setSearch] = useState('')
  const { data: conflicts = [], isLoading, error } = useConflicts()

  const filtered = conflicts.filter((c) => {
    if (severityFilter !== 'all' && c.severity !== severityFilter) return false
    if (search) {
      const q = search.toLowerCase()
      return (
        c.corridorName.toLowerCase().includes(q) ||
        c.permitA.toLowerCase().includes(q) ||
        c.permitB.toLowerCase().includes(q) ||
        c.promoterA.toLowerCase().includes(q) ||
        c.promoterB.toLowerCase().includes(q)
      )
    }
    return true
  })

  const criticalCount = conflicts.filter((c) => c.severity === 'critical').length
  const highCount = conflicts.filter((c) => c.severity === 'high').length
  const affectedCorridors = new Set(conflicts.map((c) => c.corridorId)).size

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-surface-page">
      <Header />
      <PermitSummarySheet />
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-6 py-8 space-y-6">
          <div>
            <h1 className="text-2xl font-semibold text-brand">Scheduling Advisor</h1>
            <p className="text-sm text-ink-muted mt-1">
              Detect overlapping permit schedules on the same corridor before they cause disruption.
            </p>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <StatCard label="Total Conflicts" value={isLoading ? '—' : String(conflicts.length)} />
            <StatCard
              label="Critical / High"
              value={isLoading ? '—' : `${criticalCount} / ${highCount}`}
            />
            <StatCard
              label="Corridors Affected"
              value={isLoading ? '—' : String(affectedCorridors)}
            />
          </div>

          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex items-center gap-1 bg-white border border-line rounded-md p-1 shrink-0">
              {SEVERITY_FILTERS.map(({ label, value }) => (
                <button
                  key={value}
                  onClick={() => setSeverityFilter(value)}
                  className={cn(
                    'px-3 py-1 rounded text-xs font-medium transition-colors',
                    severityFilter === value
                      ? 'bg-brand text-ink-inverse'
                      : 'text-ink-muted hover:text-ink',
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
            <input
              type="text"
              placeholder="Search by corridor, permit or promoter…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="flex-1 h-9 px-3 text-sm border border-line rounded-md bg-white text-ink placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brand/20"
            />
          </div>

          {isLoading && (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="h-36 bg-white border border-line rounded-lg animate-pulse"
                />
              ))}
            </div>
          )}

          {error && (
            <div className="text-sm text-risk-high p-4 bg-risk-high-bg rounded-lg border border-line">
              Failed to load conflicts. Is the backend running?
            </div>
          )}

          {!isLoading && !error && filtered.length === 0 && (
            <div className="text-center py-16 space-y-2">
              <p className="text-sm font-medium text-ink">
                {conflicts.length === 0
                  ? 'No scheduling conflicts detected'
                  : 'No conflicts match your filters'}
              </p>
              <p className="text-xs text-ink-muted">
                {conflicts.length === 0
                  ? 'All works on your corridors have non-overlapping schedules.'
                  : 'Try adjusting the severity filter or clearing your search.'}
              </p>
            </div>
          )}

          {!isLoading && !error && filtered.length > 0 && (
            <div className="space-y-3">
              {filtered.map((conflict, i) => (
                <ConflictCard
                  key={`${conflict.permitA}-${conflict.permitB}-${i}`}
                  conflict={conflict}
                />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white border border-line rounded-lg px-4 py-3">
      <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider">{label}</p>
      <p className="text-2xl font-semibold text-ink mt-1">{value}</p>
    </div>
  )
}
