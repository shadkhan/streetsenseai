import { cn } from '@/lib/utils'

interface PermitReferenceProps {
  reference: string
  className?: string
  onClick?: () => void
}

export function PermitReference({ reference, className, onClick }: PermitReferenceProps) {
  const base = cn(
    'font-mono text-xs bg-brand-light text-brand px-1.5 py-0.5 rounded whitespace-nowrap',
    className,
  )

  if (onClick) {
    return (
      <button
        onClick={onClick}
        className={cn(base, 'hover:bg-brand hover:text-ink-inverse transition-colors cursor-pointer')}
      >
        {reference}
      </button>
    )
  }

  return <code className={base}>{reference}</code>
}
