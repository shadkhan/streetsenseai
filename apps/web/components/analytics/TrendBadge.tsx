import { cn } from '@/lib/utils'
import { Hint } from '@/components/ui/Hint'

interface TrendBadgeProps {
  trend: 'improving' | 'stable' | 'deteriorating'
  className?: string
}

const CONFIG = {
  improving:     { label: 'Improving',     arrow: '↑', cls: 'bg-risk-low-bg text-risk-low',    hint: 'Compliance score improved by more than 5 points over the last 6 months' },
  stable:        { label: 'Stable',        arrow: '→', cls: 'bg-brand-light text-brand-muted', hint: 'Compliance score remained within ±5 points over the last 6 months'       },
  deteriorating: { label: 'Deteriorating', arrow: '↓', cls: 'bg-risk-high-bg text-risk-high',  hint: 'Compliance score declined by more than 5 points over the last 6 months'  },
} as const

export function TrendBadge({ trend, className }: TrendBadgeProps) {
  const { label, arrow, cls, hint } = CONFIG[trend]
  return (
    <Hint text={hint} side="top">
      <span className={cn(
        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium cursor-default',
        cls,
        className,
      )}>
        <span>{arrow}</span>
        {label}
      </span>
    </Hint>
  )
}
