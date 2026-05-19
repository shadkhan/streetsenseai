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
import { Hint } from '@/components/ui/Hint'
import { TrendBadge } from './TrendBadge'
import type { PromoterCompliance } from '@/types'
import { cn } from '@/lib/utils'

const COLUMN_HINTS: Record<string, string> = {
  rank:                       'League table position — 1 is the worst offender',
  promoterName:               'Promoter company name and Street Manager licence number',
  region:                     'Highway authority where this promoter operates most',
  totalWorks:                 'Total number of permit records in the dataset for this promoter',
  overrunRate:                'Percentage of completed works that ran past their proposed end date (weight: 40 pts)',
  lateStartRate:              'Percentage of works that started later than their proposed start date (weight: 30 pts)',
  missingReinstatementRate:   'Percentage of works still in-progress after their proposed end date — unreinstated carriageway (weight: 30 pts)',
  complianceScore:            'Overall compliance score 0–100. Higher is better. Calculated as: 100 − (overrun×40) − (late start×30) − (missing reinstatement×30)',
  trend:                      '6-month compliance trend vs the preceding 6 months',
}

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
              {hg.headers.map(header => {
                const hint = COLUMN_HINTS[header.column.id]
                const sorted = header.column.getIsSorted()
                const headContent = (
                  <span className="flex items-center gap-1">
                    {flexRender(header.column.columnDef.header, header.getContext())}
                    {sorted === 'asc' && ' ↑'}
                    {sorted === 'desc' && ' ↓'}
                    {!sorted && header.column.getCanSort() && (
                      <span className="text-ink-subtle opacity-40">↕</span>
                    )}
                  </span>
                )
                return (
                  <TableHead
                    key={header.id}
                    className="text-xs font-medium text-ink-subtle uppercase tracking-wider cursor-pointer select-none"
                    onClick={header.column.getToggleSortingHandler()}
                  >
                    {hint ? (
                      <Hint text={hint} side="top" delayDuration={300}>{headContent}</Hint>
                    ) : headContent}
                  </TableHead>
                )
              })}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows.map(row => (
            <Hint
              key={row.id}
              text={onRowClick ? `Click to view 12-month trend and detailed breakdown for ${row.original.promoterName}` : ''}
              side="left"
              delayDuration={600}
            >
            <TableRow
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
            </Hint>
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
