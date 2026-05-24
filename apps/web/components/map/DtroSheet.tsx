'use client'

import { FileSliders, Calendar, Building2, Tag, Hash } from 'lucide-react'
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { usePanels } from '@/lib/stores/panels'
import { useDTROOrder } from '@/lib/api'

const TRO_TYPE_LABELS: Record<string, string> = {
  speedLimit:         'Speed Limit',
  parkingRestriction: 'Parking Restriction',
  roadClosure:        'Road Closure',
  busLane:            'Bus Lane',
  cycleLane:          'Cycle Lane',
  weightRestriction:  'Weight Restriction',
  oneWay:             'One Way',
  turningProhibition: 'Turning Prohibition',
  pedestrianZone:     'Pedestrian Zone',
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
  })
}

export function DtroSheet() {
  const { active, dtroId, close } = usePanels()
  const isOpen = active === 'dtro'
  const { data: order, isLoading, isError } = useDTROOrder(isOpen ? dtroId : null)

  return (
    <Sheet open={isOpen} onOpenChange={(open) => { if (!open) close() }}>
      <SheetContent
        side="right"
        className="w-full sm:w-[420px] sm:max-w-[420px] !p-0 !gap-0 flex flex-col"
      >
        <SheetTitle className="sr-only">Traffic Regulation Order</SheetTitle>

        {/* Header */}
        <div className="flex-shrink-0 px-4 pt-4 pb-3 pr-12 border-b border-line bg-surface-panel">
          <div className="flex items-center gap-1.5 mb-1.5">
            <FileSliders className="w-3.5 h-3.5 text-ink-subtle" />
            <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider">
              Traffic Regulation Order
            </p>
          </div>
          {isLoading && <Skeleton className="h-4 w-48" />}
          {order && (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-xs text-ink">{order.referenceNumber}</span>
              {order.isTemporary && (
                <Badge className="text-[10px] py-0 px-1.5 bg-risk-medium-bg text-risk-medium border-0">
                  TTRO
                </Badge>
              )}
            </div>
          )}
        </div>

        <ScrollArea className="flex-1 min-h-0">
          <div className="px-4 py-4 space-y-4">
            {isLoading && (
              <div className="space-y-3">
                <Skeleton className="h-6 w-28" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-full" />
              </div>
            )}

            {isError && (
              <p className="text-sm text-ink-muted">
                Failed to load order details. Try closing and re-clicking the feature.
              </p>
            )}

            {order && (
              <>
                {/* Data source badge */}
                <div className="flex items-center gap-2">
                  {order.dataSource === 'synthetic' ? (
                    <Badge className="bg-risk-medium-bg text-risk-medium border-0 text-xs font-normal">
                      Synthetic data — not a real TRO
                    </Badge>
                  ) : order.dataSource === 'integration' ? (
                    <Badge className="bg-risk-low-bg text-risk-low border-0 text-xs font-normal">
                      D-TRO integration environment
                    </Badge>
                  ) : (
                    <Badge className="bg-risk-low-bg text-risk-low border-0 text-xs font-normal">
                      Live D-TRO data
                    </Badge>
                  )}
                </div>

                {/* Type + Authority */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <div className="flex items-center gap-1 mb-1">
                      <Tag className="w-3 h-3 text-ink-subtle" />
                      <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider">Type</p>
                    </div>
                    <p className="text-sm text-ink font-medium">
                      {TRO_TYPE_LABELS[order.troType] ?? order.troType}
                    </p>
                  </div>
                  <div>
                    <div className="flex items-center gap-1 mb-1">
                      <Building2 className="w-3 h-3 text-ink-subtle" />
                      <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider">Authority</p>
                    </div>
                    <p className="text-sm text-ink">{order.authority}</p>
                  </div>
                </div>

                <Separator />

                {/* Description */}
                <div>
                  <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider mb-1.5">
                    Description
                  </p>
                  <p className="text-sm text-ink leading-relaxed">{order.description}</p>
                </div>

                <Separator />

                {/* Validity */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <div className="flex items-center gap-1 mb-1">
                      <Calendar className="w-3 h-3 text-ink-subtle" />
                      <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider">Valid From</p>
                    </div>
                    <p className="text-sm text-ink">{formatDate(order.validFrom)}</p>
                  </div>
                  <div>
                    <div className="flex items-center gap-1 mb-1">
                      <Calendar className="w-3 h-3 text-ink-subtle" />
                      <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider">Valid To</p>
                    </div>
                    <p className="text-sm text-ink">
                      {order.validTo ? formatDate(order.validTo) : (
                        <span className="text-ink-muted italic">Permanent</span>
                      )}
                    </p>
                  </div>
                </div>

                <Separator />

                {/* D-TRO ID */}
                <div>
                  <div className="flex items-center gap-1 mb-1.5">
                    <Hash className="w-3 h-3 text-ink-subtle" />
                    <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider">D-TRO ID</p>
                  </div>
                  <p className="font-mono text-xs text-ink-muted break-all">{order.dtroId}</p>
                </div>
              </>
            )}
          </div>
        </ScrollArea>

        <div className="flex-shrink-0 border-t border-line px-4 py-2.5 bg-surface-panel">
          <p className="text-xs text-ink-subtle">
            D-TRO v4.0.0 · Department for Transport — Digital Traffic Regulation Orders
          </p>
        </div>
      </SheetContent>
    </Sheet>
  )
}
