'use client'

import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import type { FPNOpportunity } from '@/types'
import { cn } from '@/lib/utils'

interface FPNListProps {
  data: FPNOpportunity[]
  isLoading?: boolean
  className?: string
}

function severityClass(days: number): string {
  if (days >= 14) return 'bg-risk-critical-bg text-risk-critical'
  if (days >= 7)  return 'bg-risk-high-bg text-risk-high'
  if (days >= 3)  return 'bg-risk-medium-bg text-risk-medium'
  return 'bg-risk-low-bg text-risk-low'
}

export function FPNList({ data, isLoading, className }: FPNListProps) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full rounded-lg" />
        ))}
      </div>
    )
  }

  if (!data.length) {
    return (
      <div className="rounded-lg border border-line bg-surface-panel px-6 py-10 text-center">
        <p className="text-sm text-ink-muted">No FPN opportunities detected in the current dataset.</p>
      </div>
    )
  }

  return (
    <div className={cn('space-y-2', className)}>
      {data.map(fpn => (
        <div
          key={fpn.permitReference}
          className="flex items-start gap-4 rounded-lg border border-line bg-surface-raised px-4 py-3 shadow-sm"
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-xs text-ink-muted">{fpn.permitReference}</span>
              <Badge variant="outline" className="text-xs px-1.5 py-0 font-normal border-line">
                {fpn.authority}
              </Badge>
            </div>
            <p className="mt-0.5 text-sm font-medium text-ink truncate">{fpn.streetName}</p>
            <p className="text-xs text-ink-muted mt-0.5">
              {fpn.promoter} · Proposed end: {fpn.proposedEndDate} · Actual end: {fpn.actualEndDate}
            </p>
          </div>
          <div className="shrink-0 text-right">
            <span className={cn(
              'inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold',
              severityClass(fpn.overrunDays),
            )}>
              +{fpn.overrunDays}d overrun
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}
