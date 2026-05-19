'use client'

import type { MonthlyTrend } from '@/types'

interface TrendSparklineProps {
  data: MonthlyTrend[]
  width?: number
  height?: number
  className?: string
}

export function TrendSparkline({ data, width = 120, height = 32, className }: TrendSparklineProps) {
  if (!data.length) return null

  const scores = data.map(d => d.complianceScore)
  const min = Math.min(...scores)
  const max = Math.max(...scores)
  const range = max - min || 1

  const points = scores.map((score, i) => {
    const x = (i / (scores.length - 1)) * width
    const y = height - ((score - min) / range) * (height - 4) - 2
    return `${x},${y}`
  })

  const polyline = points.join(' ')
  const lastScore = scores[scores.length - 1]
  const firstScore = scores[0]
  const strokeColor = lastScore >= firstScore ? '#059669' : '#EA580C'

  return (
    <svg
      width={width}
      height={height}
      className={className}
      aria-label="12-month compliance trend"
    >
      <polyline
        points={polyline}
        fill="none"
        stroke={strokeColor}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  )
}
