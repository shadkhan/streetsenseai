import { RISK_CONFIG } from '@/components/risk/risk-config'
import { cn } from '@/lib/utils'
import type { RiskLevel } from '@/types'

const LEVELS: RiskLevel[] = ['critical', 'high', 'medium', 'low']

export function RiskLegend() {
  return (
    <div className="absolute bottom-8 left-4 z-10 bg-white/90 backdrop-blur-sm rounded-lg shadow-md border border-line p-3">
      <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider mb-2.5">
        Corridor Risk
      </p>
      <div className="space-y-1.5">
        {LEVELS.map((level) => {
          const { label, dot } = RISK_CONFIG[level]
          return (
            <div key={level} className="flex items-center gap-2">
              <span className={cn('w-4 h-1.5 rounded-full flex-shrink-0', dot)} />
              <span className="text-xs text-ink">{label}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
