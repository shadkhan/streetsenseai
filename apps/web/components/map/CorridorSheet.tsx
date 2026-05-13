'use client'

import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import { PermitReference } from '@/components/ui/PermitReference'
import { RiskBadge } from '@/components/risk/RiskBadge'
import { usePanels } from '@/lib/stores/panels'
import { useMapStore } from '@/lib/stores/map'
import { useCorridor } from '@/lib/api'
import type { Corridor, RiskFactor, StreetWork, RiskLevel } from '@/types'
import { cn } from '@/lib/utils'

const ROAD_CLASS_LABEL: Record<string, string> = {
  A: 'A Road',
  B: 'B Road',
  C: 'C Road',
  unclassified: 'Unclassified',
}

const STATUS_LABEL: Record<string, string> = {
  submitted: 'Submitted',
  granted: 'Granted',
  permit_modification_request: 'Modification Requested',
  refused: 'Refused',
  revoked: 'Revoked',
  in_progress: 'In Progress',
  completed: 'Completed',
  closed: 'Closed',
}

function formatDate(iso: string): string {
  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(new Date(iso))
}

function SheetSkeleton() {
  return (
    <div className="flex flex-col h-full">
      <div className="px-4 pt-4 pb-3 border-b border-line bg-surface-panel">
        <Skeleton className="h-3 w-14 mb-2" />
        <Skeleton className="h-5 w-3/4" />
      </div>
      <div className="px-4 py-4 space-y-5">
        <div className="space-y-2">
          <Skeleton className="h-3 w-20" />
          <div className="flex items-center gap-3">
            <Skeleton className="h-6 w-20 rounded" />
            <Skeleton className="h-8 w-16" />
          </div>
        </div>
        <Separator />
        <div className="space-y-3">
          <Skeleton className="h-3 w-24" />
          {[0, 1, 2].map((i) => (
            <div key={i} className="space-y-1.5">
              <div className="flex justify-between">
                <Skeleton className="h-4 w-48" />
                <Skeleton className="h-4 w-20" />
              </div>
              <Skeleton className="h-1.5 w-full rounded-full" />
            </div>
          ))}
        </div>
        <Separator />
        <div className="space-y-3">
          <Skeleton className="h-3 w-32" />
          {[0, 1].map((i) => (
            <div key={i} className="p-3 rounded-lg border border-line space-y-2">
              <div className="flex justify-between">
                <Skeleton className="h-4 w-36" />
                <Skeleton className="h-4 w-20 rounded" />
              </div>
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-3 w-2/3" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function RiskSection({ level, score }: { level: RiskLevel | null; score: number | null }) {
  return (
    <div>
      <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider mb-3">
        Risk Level
      </p>
      {level === null ? (
        <p className="text-sm text-ink-subtle">Not yet scored</p>
      ) : (
        <div className="flex items-center gap-3">
          <RiskBadge level={level} />
          {score !== null && (
            <span className="text-2xl font-semibold text-ink tabular-nums">
              {Math.round(score)}
              <span className="text-sm font-normal text-ink-muted">/100</span>
            </span>
          )}
        </div>
      )}
    </div>
  )
}

function RiskFactorsSection({ factors }: { factors: RiskFactor[] }) {
  return (
    <div>
      <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider mb-3">
        Risk Factors
      </p>
      {factors.length === 0 ? (
        <p className="text-sm text-ink-subtle">No risk factors recorded</p>
      ) : (
        <div className="space-y-4">
          {factors.map((f, i) => {
            const pct = Math.min(100, Math.max(0, Math.round(f.contribution)))
            return (
              <div key={i} className="space-y-1.5">
                <div className="flex items-start justify-between gap-2">
                  <span className="text-sm text-ink leading-tight">{f.factor}</span>
                  <div className="flex items-center gap-2 text-xs text-ink-muted tabular-nums whitespace-nowrap flex-shrink-0">
                    <span>{Math.round(f.weight * 100)}% wt</span>
                    <span className="font-medium text-ink">{Math.round(f.contribution)} pts</span>
                  </div>
                </div>
                <div className="h-1.5 bg-surface-sunken rounded-full overflow-hidden">
                  <div
                    className="h-full bg-brand-muted rounded-full"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function WorkCard({ work }: { work: StreetWork }) {
  const isActive = work.status === 'in_progress'
  const isGranted = work.status === 'granted'

  return (
    <div className="p-3 rounded-lg border border-line bg-surface-raised space-y-1.5">
      <div className="flex items-start justify-between gap-2">
        <PermitReference reference={work.permitReference} />
        <span className={cn(
          'text-xs px-1.5 py-0.5 rounded font-medium whitespace-nowrap flex-shrink-0',
          isActive  && 'bg-risk-high-bg text-risk-high',
          isGranted && 'bg-risk-medium-bg text-risk-medium',
          !isActive && !isGranted && 'bg-surface-panel text-ink-muted',
        )}>
          {STATUS_LABEL[work.status] ?? work.status}
        </span>
      </div>
      <p className="text-sm font-medium text-ink leading-tight">{work.streetName}</p>
      <p className="text-xs text-ink-muted">{work.promoter}</p>
      <p className="text-xs text-ink-subtle">
        {formatDate(work.proposedStartDate)} – {formatDate(work.proposedEndDate)}
      </p>
    </div>
  )
}

function SheetBody({ corridor }: { corridor: Corridor }) {
  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header — pr-12 gives clearance for the Sheet close button at right-4 top-4 */}
      <div className="flex-shrink-0 px-4 pt-4 pb-3 pr-12 border-b border-line bg-surface-panel">
        <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider mb-0.5">
          {ROAD_CLASS_LABEL[corridor.roadClassification] ?? corridor.roadClassification}
        </p>
        <h2 className="text-base font-semibold text-ink leading-snug">{corridor.name}</h2>
        {corridor.lastCalculated && (
          <p className="text-xs text-ink-subtle mt-0.5">
            Updated {formatDate(corridor.lastCalculated)}
          </p>
        )}
      </div>

      <ScrollArea className="flex-1 min-h-0">
        <div className="px-4 py-4 space-y-5">
          <RiskSection level={corridor.riskLevel} score={corridor.riskScore} />

          <Separator />

          <RiskFactorsSection factors={corridor.riskFactors} />

          <Separator />

          <div>
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider">
                Concurrent Works
              </p>
              {corridor.concurrentWorks.length > 0 && (
                <span className="text-xs text-ink-muted tabular-nums">
                  {corridor.activeWorksCount} active · {corridor.plannedWorksCount} planned
                </span>
              )}
            </div>
            {corridor.concurrentWorks.length === 0 ? (
              <p className="text-sm text-ink-subtle">No active works within 100 m</p>
            ) : (
              <div className="space-y-3">
                {corridor.concurrentWorks.map((w) => (
                  <WorkCard key={w.permitReference} work={w} />
                ))}
              </div>
            )}
          </div>
        </div>
      </ScrollArea>
    </div>
  )
}

export function CorridorSheet() {
  const { active, corridorId, close } = usePanels()
  const { timeWindow } = useMapStore()
  const isOpen = active === 'corridor'

  const { data: corridor, isLoading, isError } = useCorridor(corridorId, timeWindow)

  return (
    <Sheet open={isOpen} onOpenChange={(open) => { if (!open) close() }}>
      <SheetContent
        side="right"
        className="w-[420px] sm:max-w-[420px] !p-0 !gap-0 flex flex-col"
      >
        <SheetTitle className="sr-only">
          {corridor?.name ?? 'Corridor Detail'}
        </SheetTitle>

        {isLoading && <SheetSkeleton />}

        {isError && !isLoading && (
          <div className="flex flex-col items-center justify-center h-full p-6 text-center">
            <p className="text-sm font-medium text-ink mb-1">Unable to load corridor</p>
            <p className="text-xs text-ink-muted">Check your connection and try again</p>
          </div>
        )}

        {corridor && !isLoading && <SheetBody corridor={corridor} />}
      </SheetContent>
    </Sheet>
  )
}
