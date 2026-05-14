'use client'

import { cn } from '@/lib/utils'
import { RISK_CONFIG } from '@/components/risk/risk-config'
import { PermitReference } from '@/components/ui/PermitReference'
import { usePanels } from '@/lib/stores/panels'
import type { SchedulingConflict } from '@/types'

function fmtDate(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

function fmtTrafficMgmt(raw: string): string {
  return raw
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

interface Props {
  conflict: SchedulingConflict
}

export function ConflictCard({ conflict }: Props) {
  const { openPermit } = usePanels()
  const { bg, text, label } = RISK_CONFIG[conflict.severity]

  return (
    <div className="bg-white border border-line rounded-lg overflow-hidden">
      {/* Card header */}
      <div className="px-4 py-3 flex items-center justify-between border-b border-line bg-surface-panel">
        <div className="flex items-center gap-2.5">
          <span className={cn('text-xs font-semibold px-2 py-0.5 rounded-full', bg, text)}>
            {label}
          </span>
          <span className="text-sm font-semibold text-ink">{conflict.corridorName}</span>
        </div>
        <span className="text-xs text-ink-muted truncate max-w-[200px]">{conflict.streetName}</span>
      </div>

      {/* Permit comparison */}
      <div className="px-4 py-3 grid grid-cols-[1fr_24px_1fr] gap-3 items-start">
        <div className="space-y-0.5">
          <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider mb-1">Permit A</p>
          <PermitReference
            reference={conflict.permitA}
            onClick={() => openPermit(conflict.permitA)}
          />
          <p className="text-xs text-ink mt-1">{conflict.promoterA}</p>
          <p className="text-xs text-ink-muted">{fmtTrafficMgmt(conflict.trafficManagementA)}</p>
        </div>

        <div className="flex items-center justify-center pt-6 text-ink-subtle text-sm select-none">
          ↔
        </div>

        <div className="space-y-0.5 text-right">
          <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider mb-1">Permit B</p>
          <div className="flex justify-end">
            <PermitReference
              reference={conflict.permitB}
              onClick={() => openPermit(conflict.permitB)}
            />
          </div>
          <p className="text-xs text-ink mt-1">{conflict.promoterB}</p>
          <p className="text-xs text-ink-muted">{fmtTrafficMgmt(conflict.trafficManagementB)}</p>
        </div>
      </div>

      {/* Overlap summary + recommendation */}
      <div className="px-4 py-3 border-t border-line bg-surface-panel space-y-1.5">
        <p className="text-xs text-ink-muted">
          <span className="font-semibold text-ink">{conflict.overlapDays}-day overlap</span>
          {' · '}
          {fmtDate(conflict.overlapStart)} – {fmtDate(conflict.overlapEnd)}
        </p>
        <p className="text-xs text-ink-muted">
          <span className="font-medium text-ink">Recommendation:</span>{' '}
          {conflict.recommendation}
        </p>
      </div>
    </div>
  )
}
