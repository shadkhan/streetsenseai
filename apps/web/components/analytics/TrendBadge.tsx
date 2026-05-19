import { cn } from '@/lib/utils'

interface TrendBadgeProps {
  trend: 'improving' | 'stable' | 'deteriorating'
  className?: string
}

const CONFIG = {
  improving:     { label: 'Improving',     arrow: '↑', cls: 'bg-risk-low-bg text-risk-low'       },
  stable:        { label: 'Stable',        arrow: '→', cls: 'bg-brand-light text-brand-muted'    },
  deteriorating: { label: 'Deteriorating', arrow: '↓', cls: 'bg-risk-high-bg text-risk-high'     },
} as const

export function TrendBadge({ trend, className }: TrendBadgeProps) {
  const { label, arrow, cls } = CONFIG[trend]
  return (
    <span className={cn(
      'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
      cls,
      className,
    )}>
      <span>{arrow}</span>
      {label}
    </span>
  )
}
