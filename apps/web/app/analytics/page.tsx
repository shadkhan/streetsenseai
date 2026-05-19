'use client'

import { useState, useRef } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { StatsCard } from '@/components/analytics/StatsCard'
import { ComplianceTable } from '@/components/analytics/ComplianceTable'
import { FPNList } from '@/components/analytics/FPNList'
import { TrendBadge } from '@/components/analytics/TrendBadge'
import { TrendSparkline } from '@/components/analytics/TrendSparkline'
import {
  useComplianceSummary,
  usePromoters,
  useFPNOpportunities,
  useMonthlyTrend,
} from '@/lib/api'
import type { PromoterCompliance } from '@/types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

// ── Detail drawer ─────────────────────────────────────────────────────────────

function PromoterDetail({
  promoter,
  onClose,
}: {
  promoter: PromoterCompliance
  onClose: () => void
}) {
  const { data: trend, isLoading } = useMonthlyTrend(promoter.promoterLicenceNumber)

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-surface-raised border-l border-line shadow-xl z-50 flex flex-col">
      <div className="flex items-center justify-between px-5 py-4 border-b border-line">
        <div>
          <p className="text-sm font-semibold text-ink">{promoter.promoterName}</p>
          <p className="font-mono text-xs text-ink-subtle">{promoter.promoterLicenceNumber}</p>
        </div>
        <button
          onClick={onClose}
          className="text-ink-muted hover:text-ink text-lg leading-none px-1"
          aria-label="Close"
        >
          ×
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
        <div className="grid grid-cols-2 gap-3">
          <StatsCard label="Compliance Score" value={promoter.complianceScore.toFixed(1)} />
          <StatsCard label="Total Works" value={promoter.totalWorks} />
          <StatsCard
            label="Overrun Rate"
            value={`${(promoter.overrunRate * 100).toFixed(0)}%`}
            accent={promoter.overrunRate > 0.2 ? 'risk' : 'default'}
          />
          <StatsCard
            label="Late Start Rate"
            value={`${(promoter.lateStartRate * 100).toFixed(0)}%`}
            accent={promoter.lateStartRate > 0.15 ? 'risk' : 'default'}
          />
        </div>

        <div>
          <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider mb-2">Trend</p>
          <TrendBadge trend={promoter.trend} />
        </div>

        <div>
          <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider mb-2">
            12-Month Compliance
          </p>
          {isLoading ? (
            <Skeleton className="h-8 w-full" />
          ) : trend ? (
            <div>
              <TrendSparkline data={trend} width={330} height={48} />
              <div className="flex justify-between mt-1">
                <span className="text-xs text-ink-subtle">{trend[0]?.month}</span>
                <span className="text-xs text-ink-subtle">{trend[trend.length - 1]?.month}</span>
              </div>
            </div>
          ) : null}
        </div>

        <div>
          <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider mb-2">
            Missing Reinstatement
          </p>
          <p className="text-sm text-ink">
            {(promoter.missingReinstatementRate * 100).toFixed(0)}% of works
          </p>
        </div>

        <p className="text-xs text-ink-subtle">
          Region: {promoter.region} · Last updated: {promoter.lastUpdated.slice(0, 10)}
        </p>
      </div>
    </div>
  )
}

// ── AI Briefing tab ───────────────────────────────────────────────────────────

function AIBriefingTab() {
  const [briefing, setBriefing] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [done, setDone] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  async function generate() {
    setBriefing('')
    setDone(false)
    setStreaming(true)
    abortRef.current = new AbortController()

    try {
      const res = await fetch(`${API_BASE}/compliance/briefing/generate`, {
        signal: abortRef.current.signal,
      })
      if (!res.body) return
      const reader = res.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done: doneReading, value } = await reader.read()
        if (doneReading) break
        setBriefing(prev => prev + decoder.decode(value))
      }
      setDone(true)
    } catch {
      // aborted — no-op
    } finally {
      setStreaming(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-ink-muted">
          Generate a plain-English compliance briefing from the current dataset.
        </p>
        <Button
          onClick={generate}
          disabled={streaming}
          size="sm"
          className="bg-brand text-ink-inverse hover:bg-brand/90 shrink-0"
        >
          {streaming ? 'Generating…' : 'Generate Briefing'}
        </Button>
      </div>

      {(briefing || streaming) && (
        <div className="rounded-lg border border-line bg-surface-panel px-5 py-4 min-h-40">
          <p className="text-sm text-ink whitespace-pre-wrap leading-relaxed">
            {briefing}
            {streaming && (
              <span className="inline-block w-1.5 h-4 bg-ink-muted ml-0.5 animate-pulse align-middle" />
            )}
          </p>
          {done && (
            <p className="mt-4 text-xs text-ink-subtle border-t border-line pt-3">
              Based on Street Manager data · Updated {new Date().toLocaleDateString('en-GB')}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const [selectedPromoter, setSelectedPromoter] = useState<PromoterCompliance | null>(null)

  const { data: summary, isLoading: summaryLoading } = useComplianceSummary()
  const { data: promoters, isLoading: promotersLoading } = usePromoters()
  const { data: fpn, isLoading: fpnLoading } = useFPNOpportunities()

  function handleExport() {
    window.open(`${API_BASE}/compliance/export/promoters.csv`, '_blank')
  }

  return (
    <div className="bg-surface-page min-h-screen">
      {selectedPromoter && (
        <PromoterDetail
          promoter={selectedPromoter}
          onClose={() => setSelectedPromoter(null)}
        />
      )}

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-brand">Non-Compliance Analytics</h1>
            <p className="text-sm text-ink-muted mt-1">
              Promoter performance league table · FPN opportunities · AI briefing
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleExport}
            className="border-line text-ink-muted hover:text-ink"
          >
            Export CSV
          </Button>
        </div>

        {/* Summary stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {summaryLoading ? (
            Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-20 rounded-lg" />
            ))
          ) : summary ? (
            <>
              <StatsCard
                label="Total Promoters"
                value={summary.totalPromoters}
              />
              <StatsCard
                label="Avg Compliance Score"
                value={`${summary.avgComplianceScore.toFixed(1)}/100`}
                accent={summary.avgComplianceScore >= 70 ? 'good' : 'risk'}
              />
              <StatsCard
                label="FPN Opportunities"
                value={summary.totalFpnOpportunities}
                sub="Overrun works this period"
                accent={summary.totalFpnOpportunities > 0 ? 'risk' : 'default'}
              />
              <StatsCard
                label="Worst Offender Score"
                value={summary.worstOffender ? `${summary.worstOffender.complianceScore.toFixed(1)}` : '—'}
                sub={summary.worstOffender?.promoterName ?? ''}
                accent="risk"
              />
            </>
          ) : null}
        </div>

        {/* Tabs */}
        <Tabs defaultValue="league">
          <TabsList className="mb-4 bg-surface-panel border border-line">
            <TabsTrigger value="league" className="text-sm">League Table</TabsTrigger>
            <TabsTrigger value="fpn" className="text-sm">
              FPN Opportunities
              {fpn && fpn.length > 0 && (
                <span className="ml-1.5 rounded-full bg-risk-high-bg text-risk-high text-xs px-1.5 py-0">
                  {fpn.length}
                </span>
              )}
            </TabsTrigger>
            <TabsTrigger value="briefing" className="text-sm">AI Briefing</TabsTrigger>
          </TabsList>

          <TabsContent value="league">
            <ComplianceTable
              data={promoters ?? []}
              isLoading={promotersLoading}
              onRowClick={setSelectedPromoter}
            />
          </TabsContent>

          <TabsContent value="fpn">
            <FPNList data={fpn ?? []} isLoading={fpnLoading} />
          </TabsContent>

          <TabsContent value="briefing">
            <AIBriefingTab />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
