'use client'

import { useState, useMemo } from 'react'
import { FileSliders, Search } from 'lucide-react'
import { Header } from '@/components/layout/Header'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'
import { useDTROList } from '@/lib/api'
import type { DTROOrder, TROType } from '@/types'

const TRO_TYPE_LABELS: Record<TROType, string> = {
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

// Group TRO types by impact level for token-compliant badge styling
const TRO_TYPE_STYLE: Record<TROType, string> = {
  roadClosure:        'bg-risk-critical-bg text-risk-critical',
  speedLimit:         'bg-risk-high-bg text-risk-high',
  weightRestriction:  'bg-risk-high-bg text-risk-high',
  turningProhibition: 'bg-risk-medium-bg text-risk-medium',
  busLane:            'bg-risk-medium-bg text-risk-medium',
  parkingRestriction: 'bg-risk-medium-bg text-risk-medium',
  cycleLane:          'bg-risk-low-bg text-risk-low',
  oneWay:             'bg-risk-low-bg text-risk-low',
  pedestrianZone:     'bg-risk-low-bg text-risk-low',
}

const ALL_TYPES = Object.keys(TRO_TYPE_LABELS) as TROType[]

type Temporal = 'all' | 'permanent' | 'temporary'

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
  })
}

export default function DTROsPage() {
  const [temporal, setTemporal] = useState<Temporal>('all')
  const [typeFilter, setTypeFilter] = useState<TROType | ''>('')
  const [authoritySearch, setAuthoritySearch] = useState('')

  const { data: orders = [], isLoading } = useDTROList({ limit: 500 })

  const filtered = useMemo(() => {
    return orders.filter((o: DTROOrder) => {
      if (temporal === 'permanent' && o.isTemporary) return false
      if (temporal === 'temporary' && !o.isTemporary) return false
      if (typeFilter && o.troType !== typeFilter) return false
      if (authoritySearch && !o.authority.toLowerCase().includes(authoritySearch.toLowerCase())) return false
      return true
    })
  }, [orders, temporal, typeFilter, authoritySearch])

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <Header />
      <main className="flex-1 min-h-0 overflow-auto bg-surface-page">
        <div className="max-w-7xl mx-auto px-6 py-6">

          {/* Page header */}
          <div className="flex items-start justify-between mb-6">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <FileSliders className="w-5 h-5 text-brand" />
                <h1 className="text-2xl font-semibold text-brand">Traffic Regulation Orders</h1>
              </div>
              <p className="text-sm text-ink-muted">
                Digital Traffic Regulation Orders (D-TRO v4.0.0) — speed limits, closures, parking and zone restrictions
              </p>
            </div>
            {!isLoading && (
              <div className="text-right">
                <p className="text-2xl font-semibold text-ink">{filtered.length}</p>
                <p className="text-xs text-ink-muted">
                  {filtered.length === orders.length ? `of ${orders.length} orders` : `filtered from ${orders.length}`}
                </p>
              </div>
            )}
          </div>

          {/* Filter bar */}
          <div className="flex items-center gap-3 mb-5 flex-wrap">
            {/* Permanent / Temporary toggle */}
            <div className="flex rounded-md border border-line overflow-hidden">
              {(['all', 'permanent', 'temporary'] as Temporal[]).map((t) => (
                <button
                  key={t}
                  onClick={() => setTemporal(t)}
                  className={`px-3 py-1.5 text-xs font-medium transition-colors capitalize ${
                    temporal === t
                      ? 'bg-brand text-ink-inverse'
                      : 'bg-surface-panel text-ink-muted hover:text-ink'
                  }`}
                >
                  {t === 'temporary' ? 'TTRO' : t.charAt(0).toUpperCase() + t.slice(1)}
                </button>
              ))}
            </div>

            {/* TRO type filter */}
            <div className="flex items-center gap-1 flex-wrap">
              <button
                onClick={() => setTypeFilter('')}
                className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                  typeFilter === '' ? 'bg-brand text-ink-inverse' : 'bg-surface-panel text-ink-muted hover:text-ink border border-line'
                }`}
              >
                All types
              </button>
              {ALL_TYPES.map((t) => (
                <button
                  key={t}
                  onClick={() => setTypeFilter(typeFilter === t ? '' : t)}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition-colors border ${
                    typeFilter === t
                      ? `${TRO_TYPE_STYLE[t]} border-transparent`
                      : 'bg-surface-panel text-ink-muted hover:text-ink border-line'
                  }`}
                >
                  {TRO_TYPE_LABELS[t]}
                </button>
              ))}
            </div>

            {/* Authority search */}
            <div className="relative ml-auto">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-ink-subtle pointer-events-none" />
              <Input
                className="pl-8 h-8 text-xs w-52 bg-surface-panel"
                placeholder="Filter by authority…"
                value={authoritySearch}
                onChange={(e) => setAuthoritySearch(e.target.value)}
              />
            </div>
          </div>

          {/* Table */}
          <div className="rounded-lg border border-line overflow-hidden bg-surface-panel">
            <Table>
              <TableHeader>
                <TableRow className="bg-surface-page hover:bg-surface-page">
                  <TableHead className="text-xs font-medium text-ink-subtle uppercase tracking-wider w-48">Reference</TableHead>
                  <TableHead className="text-xs font-medium text-ink-subtle uppercase tracking-wider">Type</TableHead>
                  <TableHead className="text-xs font-medium text-ink-subtle uppercase tracking-wider">Authority</TableHead>
                  <TableHead className="text-xs font-medium text-ink-subtle uppercase tracking-wider w-32">Valid From</TableHead>
                  <TableHead className="text-xs font-medium text-ink-subtle uppercase tracking-wider w-32">Valid To</TableHead>
                  <TableHead className="text-xs font-medium text-ink-subtle uppercase tracking-wider w-28">Source</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading && (
                  Array.from({ length: 8 }).map((_, i) => (
                    <TableRow key={i}>
                      <TableCell><Skeleton className="h-3.5 w-36" /></TableCell>
                      <TableCell><Skeleton className="h-3.5 w-24" /></TableCell>
                      <TableCell><Skeleton className="h-3.5 w-40" /></TableCell>
                      <TableCell><Skeleton className="h-3.5 w-24" /></TableCell>
                      <TableCell><Skeleton className="h-3.5 w-24" /></TableCell>
                      <TableCell><Skeleton className="h-3.5 w-20" /></TableCell>
                    </TableRow>
                  ))
                )}
                {!isLoading && filtered.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-12 text-sm text-ink-muted">
                      No orders match the current filters.
                    </TableCell>
                  </TableRow>
                )}
                {!isLoading && filtered.map((order: DTROOrder) => (
                  <TableRow key={order.id} className="hover:bg-surface-page/50">
                    <TableCell>
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-xs text-ink">{order.referenceNumber}</span>
                        {order.isTemporary && (
                          <Badge className="text-[9px] py-0 px-1 bg-risk-medium-bg text-risk-medium border-0">
                            TTRO
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className={`text-xs border-0 font-normal ${TRO_TYPE_STYLE[order.troType as TROType] ?? 'bg-surface-page text-ink-muted'}`}>
                        {TRO_TYPE_LABELS[order.troType as TROType] ?? order.troType}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-ink">{order.authority}</TableCell>
                    <TableCell className="text-sm text-ink-muted">{formatDate(order.validFrom)}</TableCell>
                    <TableCell className="text-sm text-ink-muted">
                      {order.validTo ? formatDate(order.validTo) : (
                        <span className="text-ink-subtle italic text-xs">Permanent</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {order.dataSource === 'synthetic' ? (
                        <span className="text-xs text-ink-subtle italic">Synthetic</span>
                      ) : (
                        <Badge className="bg-risk-low-bg text-risk-low border-0 text-xs font-normal">
                          Live
                        </Badge>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Footer note */}
          <p className="text-xs text-ink-subtle mt-3">
            D-TRO v4.0.0 · Department for Transport · Digital Traffic Regulation Orders open data
            {orders.some((o: DTROOrder) => o.dataSource === 'synthetic') && (
              <span className="ml-1 text-risk-medium">· Contains synthetic demonstration data</span>
            )}
          </p>
        </div>
      </main>
    </div>
  )
}
