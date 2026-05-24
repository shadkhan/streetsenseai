'use client'

import { useMapStore } from '@/lib/stores/map'
import type { TimeWindow } from '@/lib/stores/map'
import { Hint } from '@/components/ui/Hint'
import { cn } from '@/lib/utils'

interface Preset {
  label: string
  window: TimeWindow | null
}

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10)
}

const PRESET_HINTS: Record<string, string> = {
  'All Active':    'Show all currently active and upcoming works on the network',
  'Today':         'Show only works that are active or starting today',
  'Next 7 Days':   'Show works active within the next 7 days',
  'Next 30 Days':  'Show works active within the next 30 days',
}

function buildPresets(): Preset[] {
  const today = new Date()
  const d7 = new Date(today); d7.setDate(today.getDate() + 6)
  const d30 = new Date(today); d30.setDate(today.getDate() + 29)
  const todayStr = isoDate(today)
  return [
    { label: 'All Active', window: null },
    { label: 'Today',        window: { label: 'Today',        startDate: todayStr,         endDate: todayStr               } },
    { label: 'Next 7 Days',  window: { label: 'Next 7 Days',  startDate: todayStr,         endDate: isoDate(d7)            } },
    { label: 'Next 30 Days', window: { label: 'Next 30 Days', startDate: todayStr,         endDate: isoDate(d30)           } },
  ]
}

function formatDateShort(iso: string): string {
  return new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' }).format(new Date(iso))
}

export function TimeWindowControl() {
  const { timeWindow, setTimeWindow } = useMapStore()
  const presets = buildPresets()
  const activeLabel = timeWindow?.label ?? 'All Active'

  return (
    <div className="absolute bottom-20 sm:bottom-8 left-1/2 -translate-x-1/2 z-10 flex flex-col items-center gap-1">
      {timeWindow && (
        <p className="text-xs text-ink bg-white/90 backdrop-blur-sm px-2 py-0.5 rounded-full border border-line shadow-sm tabular-nums">
          {formatDateShort(timeWindow.startDate)}
          {timeWindow.startDate !== timeWindow.endDate && (
            <> – {formatDateShort(timeWindow.endDate)}</>
          )}
        </p>
      )}
      <div className="bg-white/90 backdrop-blur-sm rounded-lg shadow-md border border-line p-1 flex items-center gap-0.5">
        {presets.map((preset) => (
          <Hint key={preset.label} text={PRESET_HINTS[preset.label] ?? preset.label} side="top">
            <button
              onClick={() => setTimeWindow(preset.window)}
              aria-label={PRESET_HINTS[preset.label]}
              className={cn(
                'px-2 py-1 sm:px-3 sm:py-1.5 rounded text-xs font-medium transition-colors whitespace-nowrap',
                activeLabel === preset.label
                  ? 'bg-brand text-ink-inverse'
                  : 'text-ink-muted hover:text-ink hover:bg-surface-panel',
              )}
            >
              {preset.label}
            </button>
          </Hint>
        ))}
      </div>
    </div>
  )
}
