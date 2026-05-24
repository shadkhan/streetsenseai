'use client'

import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import { PermitReference } from '@/components/ui/PermitReference'
import { Hint } from '@/components/ui/Hint'
import { RiskBadge } from '@/components/risk/RiskBadge'
import { usePanels } from '@/lib/stores/panels'
import { useMapStore } from '@/lib/stores/map'
import { useCorridor, useCompositeRisk, useCorridorConflicts, useStrikeRisk } from '@/lib/api'
import type { CompositeRisk, Corridor, RiskFactor, RiskLevel, StreetWork, TROConflict } from '@/types'
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

function ScoreBar({
  label, score, weight, level, hint,
}: {
  label: string
  score: number
  weight: number
  level: RiskLevel
  hint: string
}) {
  const LEVEL_BAR: Record<RiskLevel, string> = {
    low:      'bg-risk-low',
    medium:   'bg-risk-medium',
    high:     'bg-risk-high',
    critical: 'bg-risk-critical',
  }
  return (
    <Hint text={hint} side="left">
      <div className="space-y-1 cursor-default">
        <div className="flex items-center justify-between text-xs">
          <span className="text-ink-muted">{label}</span>
          <span className="tabular-nums font-medium text-ink">
            {Math.round(score)}
            <span className="text-ink-subtle font-normal">/{Math.round(weight * 100)}%</span>
          </span>
        </div>
        <div className="h-1.5 bg-surface-sunken rounded-full overflow-hidden">
          <div
            className={cn('h-full rounded-full transition-all', LEVEL_BAR[level])}
            style={{ width: `${score}%` }}
          />
        </div>
      </div>
    </Hint>
  )
}

function CompositeRiskSection({ corridorId }: { corridorId: string }) {
  const { data, isLoading } = useCompositeRisk(corridorId)

  return (
    <div>
      <Hint
        text="Composite score combines surface disruption risk (60% weight) and underground asset strike risk (40% weight) into a single 0–100 score"
        side="right"
      >
        <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider mb-3 cursor-default w-fit">
          Composite Risk
        </p>
      </Hint>

      {isLoading ? (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <Skeleton className="h-6 w-20 rounded" />
            <Skeleton className="h-8 w-16" />
          </div>
          <Skeleton className="h-10 w-full rounded" />
        </div>
      ) : data ? (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <RiskBadge level={data.compositeLevel} />
            <span className="text-2xl font-semibold text-ink tabular-nums">
              {Math.round(data.compositeScore)}
              <span className="text-sm font-normal text-ink-muted">/100</span>
            </span>
          </div>
          <div className="space-y-2.5 pt-1">
            <ScoreBar
              label="Surface disruption"
              score={data.surfaceScore}
              weight={data.surfaceWeight}
              level={data.surfaceLevel}
              hint={`Surface disruption score ${Math.round(data.surfaceScore)}/100 — based on concurrent works, traffic management type, work category, and road classification. Contributes ${Math.round(data.surfaceWeight * 100)}% to the composite.`}
            />
            <ScoreBar
              label="Underground density"
              score={data.undergroundScore}
              weight={data.undergroundWeight}
              level={data.undergroundLevel}
              hint={
                data.undergroundAssetsInRange > 0
                  ? `Underground asset density score ${Math.round(data.undergroundScore)}/100 — based on ${data.undergroundAssetsInRange} buried assets within 100 m, weighted by utility type danger (gas > electric > water > telecoms). Contributes ${Math.round(data.undergroundWeight * 100)}% to the composite.`
                  : `No underground assets found within 100 m of this corridor. Underground score is 0 — composite is driven entirely by surface risk. Seed NUAR data via POST /nuar/admin/seed to populate.`
              }
            />
          </div>
          {data.undergroundAssetsInRange === 0 && (
            <p className="text-xs text-ink-subtle italic">
              No underground assets within 100 m — seed NUAR data to enable full composite scoring
            </p>
          )}
        </div>
      ) : (
        <p className="text-sm text-ink-subtle">Composite score unavailable</p>
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

const ASSET_TYPE_LABEL: Record<string, string> = {
  gas: 'Gas',
  electric: 'Electric',
  water: 'Water',
  telecoms: 'Telecoms',
  other: 'Other',
}

function StrikeRiskRow({ permitRef }: { permitRef: string }) {
  const { data, isLoading } = useStrikeRisk(permitRef)

  if (isLoading) {
    return (
      <div className="flex items-center gap-1.5 mt-1.5 pt-1.5 border-t border-line">
        <Skeleton className="h-3 w-24 rounded" />
        <Skeleton className="h-4 w-14 rounded" />
      </div>
    )
  }
  if (!data) return null

  const topTypes = Object.entries(data.assetsByType)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 3)
    .map(([type]) => ASSET_TYPE_LABEL[type] ?? type)

  return (
    <div className="flex items-center gap-1.5 mt-1.5 pt-1.5 border-t border-line">
      <span className="text-[10px] font-medium text-ink-subtle uppercase tracking-wider flex-shrink-0">
        Underground
      </span>
      <RiskBadge
        level={data.overallRisk}
        showDot
        className="py-0 h-[18px] text-[10px] leading-none"
      />
      {data.assetCount > 0 ? (
        <span className="ml-auto text-[10px] text-ink-subtle truncate">
          {topTypes.join(' · ')}
        </span>
      ) : (
        <span className="ml-auto text-[10px] text-ink-subtle">No assets in zone</span>
      )}
    </div>
  )
}

function WorkCard({ work }: { work: StreetWork }) {
  const { openPermit } = usePanels()
  const isActive = work.status === 'in_progress'
  const isGranted = work.status === 'granted'

  return (
    <div className="p-3 rounded-lg border border-line bg-surface-raised space-y-1.5">
      <div className="flex items-start justify-between gap-2">
        <PermitReference
          reference={work.permitReference}
          onClick={() => openPermit(work.permitReference)}
        />
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
      <StrikeRiskRow permitRef={work.permitReference} />
    </div>
  )
}

const TRO_TYPE_LABEL: Record<string, string> = {
  speedLimit: 'Speed Limit',
  parkingRestriction: 'Parking',
  roadClosure: 'Road Closure',
  busLane: 'Bus Lane',
  cycleLane: 'Cycle Lane',
  weightRestriction: 'Weight Limit',
  oneWay: 'One-Way',
  turningProhibition: 'Turn Prohibition',
  pedestrianZone: 'Pedestrian Zone',
}

const CONFLICT_TYPE_LABEL: Record<string, string> = {
  both: 'Spatial + Temporal',
  spatial_overlap: 'Spatial',
  temporal_overlap: 'Temporal',
}

const SEVERITY_CHIP: Record<RiskLevel, string> = {
  low:      'bg-risk-low-bg text-risk-low',
  medium:   'bg-risk-medium-bg text-risk-medium',
  high:     'bg-risk-high-bg text-risk-high',
  critical: 'bg-risk-critical-bg text-risk-critical',
}

function ConflictCard({ conflict }: { conflict: TROConflict }) {
  return (
    <div className="p-3 rounded-lg border border-line bg-surface-raised space-y-1.5">
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs px-1.5 py-0.5 rounded font-medium bg-[#E0F2FE] text-[#0369A1]">
          {TRO_TYPE_LABEL[conflict.troType] ?? conflict.troType}
        </span>
        <span className={cn('text-xs px-1.5 py-0.5 rounded font-medium whitespace-nowrap', SEVERITY_CHIP[conflict.severity as RiskLevel])}>
          {conflict.severity.charAt(0).toUpperCase() + conflict.severity.slice(1)}
        </span>
      </div>
      <p className="text-xs font-mono text-ink-muted">{conflict.troReferenceNumber}</p>
      <p className="text-sm text-ink leading-snug">{conflict.description}</p>
      <div className="flex items-center gap-2 text-[10px] text-ink-subtle">
        <span>{CONFLICT_TYPE_LABEL[conflict.conflictType] ?? conflict.conflictType} overlap</span>
        {conflict.troValidTo && (
          <span>· Expires {formatDate(conflict.troValidTo)}</span>
        )}
      </div>
    </div>
  )
}

function ConflictsSection({ corridorId }: { corridorId: string }) {
  const { data, isLoading } = useCorridorConflicts(corridorId)

  return (
    <div>
      <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider mb-3">
        TRO Conflicts
      </p>
      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-16 w-full rounded-lg" />
          <Skeleton className="h-16 w-full rounded-lg" />
        </div>
      ) : data && data.conflictCount > 0 ? (
        <div className="space-y-2">
          {data.conflicts.map((c, i) => (
            <ConflictCard key={`${c.dtroId}-${c.permitReference}-${i}`} conflict={c} />
          ))}
        </div>
      ) : (
        <p className="text-sm text-ink-subtle">No TRO conflicts detected in this corridor</p>
      )}
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
          <CompositeRiskSection corridorId={corridor.id} />

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

          <Separator />

          <ConflictsSection corridorId={corridor.id} />
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
        className="w-full sm:w-[420px] sm:max-w-[420px] !p-0 !gap-0 flex flex-col"
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
