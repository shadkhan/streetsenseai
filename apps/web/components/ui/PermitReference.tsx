import { cn } from '@/lib/utils'

interface PermitReferenceProps {
  reference: string
  className?: string
}

export function PermitReference({ reference, className }: PermitReferenceProps) {
  return (
    <code className={cn(
      'font-mono text-xs bg-brand-light text-brand px-1.5 py-0.5 rounded',
      'whitespace-nowrap',
      className
    )}>
      {reference}
    </code>
  )
}
