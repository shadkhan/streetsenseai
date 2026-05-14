'use client'

import { useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { Bot, ChevronDown, ChevronUp, FileText } from 'lucide-react'
import { Header } from '@/components/layout/Header'
import { PermitSummarySheet } from '@/components/copilot/PermitSummarySheet'
import { useAuditLogs } from '@/lib/api'
import { cn } from '@/lib/utils'
import type { AuditLogEntry, PermitCitation } from '@/types'

function TypeBadge({ type }: { type: AuditLogEntry['interactionType'] }) {
  if (type === 'copilot') {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-brand bg-brand-light px-1.5 py-0.5 rounded">
        <Bot className="w-3 h-3" />
        Copilot
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium text-risk-low bg-risk-low-bg px-1.5 py-0.5 rounded">
      <FileText className="w-3 h-3" />
      Permit
    </span>
  )
}

interface EntryCardProps {
  entry: AuditLogEntry
  isExpanded: boolean
  onToggle: () => void
}

function EntryCard({ entry, isExpanded, onToggle }: EntryCardProps) {
  return (
    <div className={cn(
      'bg-white border border-line rounded-lg overflow-hidden',
      isExpanded && 'ring-1 ring-brand/20',
    )}>
      <button
        className="w-full text-left px-4 py-3 flex items-start gap-4 hover:bg-surface-panel/50 transition-colors"
        onClick={onToggle}
      >
        <div className="flex flex-col gap-1.5 flex-shrink-0 w-20 pt-0.5">
          <TypeBadge type={entry.interactionType} />
          <span className="text-xs text-ink-muted">
            {formatDistanceToNow(new Date(entry.createdAt), { addSuffix: true })}
          </span>
        </div>

        <div className="flex-1 min-w-0 space-y-0.5">
          <p className="text-sm font-medium text-ink truncate">{entry.query}</p>
          <p className="text-xs text-ink-muted line-clamp-2 leading-relaxed">
            {entry.response}
          </p>
        </div>

        <div className="flex-shrink-0 text-ink-subtle mt-0.5">
          {isExpanded
            ? <ChevronUp className="w-4 h-4" />
            : <ChevronDown className="w-4 h-4" />
          }
        </div>
      </button>

      {isExpanded && (
        <div className="px-4 pb-4 pt-3 border-t border-line space-y-3">
          <div>
            <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider mb-1.5">
              Full Response
            </p>
            <p className="text-sm text-ink leading-relaxed whitespace-pre-wrap">
              {entry.response}
            </p>
          </div>

          {entry.citations && entry.citations.length > 0 && (
            <div>
              <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider mb-1.5">
                Citations ({entry.citations.length})
              </p>
              <div className="flex flex-wrap gap-1.5">
                {(entry.citations as PermitCitation[]).map((c) => (
                  <span
                    key={c.permitReference}
                    className="font-mono text-xs bg-brand-light text-brand px-1.5 py-0.5 rounded"
                  >
                    {c.permitReference}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="flex items-center justify-between pt-1 border-t border-line">
            <p className="text-xs text-ink-subtle">
              {new Date(entry.createdAt).toLocaleString('en-GB', {
                day: 'numeric', month: 'short', year: 'numeric',
                hour: '2-digit', minute: '2-digit',
              })}
            </p>
            {entry.sessionId && (
              <p className="text-xs text-ink-subtle">
                Session <span className="font-mono">{entry.sessionId.slice(-8)}</span>
              </p>
            )}
          </div>
        </div>
      )}
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

export default function AuditPage() {
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const { data: logs = [], isLoading, error } = useAuditLogs(50)

  const copilotCount = logs.filter((l) => l.interactionType === 'copilot').length
  const permitCount = logs.filter((l) => l.interactionType === 'permit_summary').length
  const todayCount = logs.filter((l) => {
    const today = new Date().toISOString().slice(0, 10)
    return l.createdAt.startsWith(today)
  }).length

  const toggle = (id: string) =>
    setExpandedId((prev) => (prev === id ? null : id))

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-surface-page">
      <Header />
      <PermitSummarySheet />
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 py-8 space-y-6">
          <div>
            <h1 className="text-2xl font-semibold text-brand">Audit Trail</h1>
            <p className="text-sm text-ink-muted mt-1">
              Every AI interaction is logged here for accountability and review.
              Auto-refreshes every 30 seconds.
            </p>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <StatCard label="Total Interactions" value={isLoading ? '—' : String(logs.length)} />
            <StatCard
              label="Copilot / Permits"
              value={isLoading ? '—' : `${copilotCount} / ${permitCount}`}
            />
            <StatCard label="Today" value={isLoading ? '—' : String(todayCount)} />
          </div>

          {isLoading && (
            <div className="space-y-2">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-20 bg-white border border-line rounded-lg animate-pulse" />
              ))}
            </div>
          )}

          {error && (
            <div className="text-sm text-risk-high p-4 bg-risk-high-bg rounded-lg border border-line">
              Failed to load audit logs. Make sure the backend is running and the migration has been applied.
            </div>
          )}

          {!isLoading && !error && logs.length === 0 && (
            <div className="text-center py-16 space-y-2">
              <p className="text-sm font-medium text-ink">No interactions logged yet</p>
              <p className="text-xs text-ink-muted">
                Use the Copilot or click any permit reference to generate your first entry.
              </p>
            </div>
          )}

          {!isLoading && !error && logs.length > 0 && (
            <div className="space-y-2">
              {logs.map((entry) => (
                <EntryCard
                  key={entry.id}
                  entry={entry}
                  isExpanded={expandedId === entry.id}
                  onToggle={() => toggle(entry.id)}
                />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
