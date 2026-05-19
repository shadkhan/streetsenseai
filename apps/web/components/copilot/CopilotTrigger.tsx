'use client'

import { MessageSquare } from 'lucide-react'
import { usePanels } from '@/lib/stores/panels'
import { Hint } from '@/components/ui/Hint'
import { cn } from '@/lib/utils'

interface CopilotTriggerProps {
  className?: string
}

export function CopilotTrigger({ className }: CopilotTriggerProps) {
  const { openCopilot } = usePanels()

  return (
    <Hint text="Ask StreetSense AI about permits, risk scores, and roadworks" side="left">
      <button
        onClick={openCopilot}
        aria-label="Open StreetSense AI Copilot"
        className={cn(
          'absolute bottom-8 right-4 z-10',
          'flex items-center gap-2 px-4 h-10 rounded-full',
          'bg-brand text-ink-inverse text-xs font-medium',
          'shadow-lg hover:bg-brand/90 transition-colors',
          className,
        )}
      >
        <MessageSquare className="w-3.5 h-3.5" />
        Ask AI
      </button>
    </Hint>
  )
}
