import { cn } from '@/lib/utils'
import type { RiskLevel } from '@/types'
import { RISK_CONFIG } from './risk-config'

interface RiskBadgeProps {
  level: RiskLevel
  showDot?: boolean
  className?: string
}

export function RiskBadge({ level, showDot = true, className }: RiskBadgeProps) {
  const { label, dot, bg, text } = RISK_CONFIG[level]
  return (
    <span className={cn(
      'inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium',
      bg, text, className
    )}>
      {showDot && <span className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0', dot)} />}
      {label}
    </span>
  )
}
