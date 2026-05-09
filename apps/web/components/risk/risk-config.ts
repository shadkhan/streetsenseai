import type { RiskLevel } from '@/types'

export const RISK_CONFIG: Record<RiskLevel, {
  label: string
  dot: string
  bg: string
  text: string
}> = {
  low:      { label: 'Low',      dot: 'bg-risk-low',      bg: 'bg-risk-low-bg',      text: 'text-risk-low'      },
  medium:   { label: 'Medium',   dot: 'bg-risk-medium',   bg: 'bg-risk-medium-bg',   text: 'text-risk-medium'   },
  high:     { label: 'High',     dot: 'bg-risk-high',     bg: 'bg-risk-high-bg',     text: 'text-risk-high'     },
  critical: { label: 'Critical', dot: 'bg-risk-critical', bg: 'bg-risk-critical-bg', text: 'text-risk-critical' },
} as const
