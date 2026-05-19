import { Tooltip, TooltipContent, TooltipTrigger } from './tooltip'

interface HintProps {
  text: string
  children: React.ReactNode
  side?: 'top' | 'right' | 'bottom' | 'left'
  delayDuration?: number
}

/**
 * Lightweight tooltip wrapper. Wraps any element with a hover tooltip.
 * Requires TooltipProvider in the tree (added to app/providers.tsx).
 *
 * Usage:
 *   <Hint text="Send message (Enter)">
 *     <button>...</button>
 *   </Hint>
 */
export function Hint({ text, children, side = 'top', delayDuration = 400 }: HintProps) {
  return (
    <Tooltip delayDuration={delayDuration}>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent side={side} className="max-w-xs text-xs leading-snug">
        <p>{text}</p>
      </TooltipContent>
    </Tooltip>
  )
}
