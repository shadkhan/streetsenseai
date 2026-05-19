'use client'

import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from '@tanstack/react-table'
import { useState } from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'
import { TrendBadge } from './TrendBadge'
import type { PromoterCompliance } from '@/types'
import { cn } from '@/lib/utils'

interface ComplianceTableProps {
  data: PromoterCompliance[]
  isLoading?: boolean
  onRowClick?: (promoter: PromoterCompliance) => void
}

const col = createColumnHelper<PromoterCompliance>()

function ScoreCell({ score }: { score: number }) {
  const colour =
    score >= 80 ? 'text-risk-low'
    : score >= 60 ? 'text-risk-medium'
    : score >= 40 ? 'text-risk-high'
    : 'text-risk-critical'
  return <span className={cn('font-semibold tabular-nums', colour)}>{score.toFixed(1)}</span>
}

function RateCell({ rate }: { rate: number }) {
  return <span className="tabular-nums text-ink-muted">{(rate * 100).toFixed(0)}%</span>
}

const columns = [
  col.display({
    id: 'rank',
    header: '#',
    cell: ({ row }) => (
      <span className="text-xs text-ink-subtle tabular-nums font-mono">{row.index + 1}</span>
    ),
  }),
  col.accessor('promoterName', {
    header: 'Promoter',
    cell: info => (
      <div>
        <p className="font-medium text-ink text-sm">{info.getValue()}</p>
        <p className="font-mono text-xs text-ink-subtle">{info.row.original.promoterLicenceNumber}</p>
      </div>
    ),
  }),
  col.accessor('region', {
    header: 'Region',
    cell: info => <span className="text-sm text-ink-muted">{info.getValue()}</span>,
  }),
  col.accessor('totalWorks', {
    header: 'Works',
    cell: info => <span className="tabular-nums text-sm text-ink-muted">{info.getValue()}</span>,
  }),
  col.accessor('overrunRate', {
    header: 'Overrun',
    cell: info => <RateCell rate={info.getValue()} />,
  }),
  col.accessor('lateStartRate', {
    header: 'Late Start',
    cell: info => <RateCell rate={info.getValue()} />,
  }),
  col.accessor('missingReinstatementRate', {
    header: 'Missing Reinst.',
    cell: info => <RateCell rate={info.getValue()} />,
  }),
  col.accessor('complianceScore', {
    header: 'Score',
    cell: info => <ScoreCell score={info.getValue()} />,
  }),
  col.accessor('trend', {
    header: 'Trend',
    cell: info => <TrendBadge trend={info.getValue()} />,
  }),
]

export function ComplianceTable({ data, isLoading, onRowClick }: ComplianceTableProps) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'complianceScore', desc: false },
  ])

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full rounded" />
        ))}
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-line overflow-hidden">
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map(hg => (
            <TableRow key={hg.id} className="bg-surface-panel">
              {hg.headers.map(header => (
                <TableHead
                  key={header.id}
                  className="text-xs font-medium text-ink-subtle uppercase tracking-wider cursor-pointer select-none"
                  onClick={header.column.getToggleSortingHandler()}
                >
                  <span className="flex items-center gap-1">
                    {flexRender(header.column.columnDef.header, header.getContext())}
                    {header.column.getIsSorted() === 'asc' && ' ↑'}
                    {header.column.getIsSorted() === 'desc' && ' ↓'}
                  </span>
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows.map(row => (
            <TableRow
              key={row.id}
              className={cn(
                'border-b border-line last:border-0',
                onRowClick && 'cursor-pointer hover:bg-brand-light/40',
              )}
              onClick={() => onRowClick?.(row.original)}
            >
              {row.getVisibleCells().map(cell => (
                <TableCell key={cell.id} className="py-3">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </TableCell>
              ))}
            </TableRow>
          ))}
          {table.getRowModel().rows.length === 0 && (
            <TableRow>
              <TableCell colSpan={columns.length} className="text-center text-sm text-ink-muted py-10">
                No compliance data available.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  )
}
