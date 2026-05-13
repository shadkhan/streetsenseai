import type { ReactNode } from 'react'

interface HeaderProps {
  actions?: ReactNode
}

export function Header({ actions }: HeaderProps) {
  return (
    <header className="h-14 bg-brand flex items-center px-4 gap-3 shrink-0">
      <div className="flex items-center gap-2.5">
        <span className="text-sm font-semibold text-ink-inverse tracking-tight">
          StreetSense AI
        </span>
        <span className="hidden md:inline text-xs text-ink-inverse opacity-40 font-normal">
          Corridor Risk Intelligence
        </span>
      </div>
      {actions && (
        <div className="ml-auto flex items-center gap-2">{actions}</div>
      )}
    </header>
  )
}
