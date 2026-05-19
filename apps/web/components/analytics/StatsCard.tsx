import { cn } from '@/lib/utils'

interface StatsCardProps {
  label: string
  value: string | number
  sub?: string
  accent?: 'default' | 'risk' | 'good'
  className?: string
}

export function StatsCard({ label, value, sub, accent = 'default', className }: StatsCardProps) {
  return (
    <div className={cn('bg-surface-raised rounded-lg border border-line px-5 py-4 shadow-sm', className)}>
      <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider">{label}</p>
      <p className={cn(
        'mt-1 text-2xl font-semibold tabular-nums',
        accent === 'risk'  && 'text-risk-high',
        accent === 'good'  && 'text-risk-low',
        accent === 'default' && 'text-ink',
      )}>
        {value}
      </p>
      {sub && <p className="mt-0.5 text-xs text-ink-muted">{sub}</p>}
    </div>
  )
}
