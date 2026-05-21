import type { ReactNode } from 'react'
import Link from 'next/link'
import { NavLinks } from './NavLinks'

interface HeaderProps {
  actions?: ReactNode
}

export function Header({ actions }: HeaderProps) {
  return (
    <header className="h-14 bg-brand flex items-center px-4 shrink-0">
      <Link href="/" className="flex items-center gap-2.5 group shrink-0">
        {/* StreetSense AI logo mark */}
        <svg
          viewBox="0 0 32 32"
          className="w-7 h-7 shrink-0"
          fill="none"
          aria-hidden="true"
        >
          <rect width="32" height="32" rx="6" fill="white" fillOpacity="0.15" />
          <path
            d="M 7 25 L 7 13 Q 7 9 11 9 L 25 9"
            stroke="white"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <circle cx="25" cy="9" r="3.5" fill="white" />
          <circle cx="25" cy="9" r="6" stroke="white" strokeWidth="1" strokeOpacity="0.35" />
        </svg>

        <div className="flex items-baseline gap-1.5">
          <span className="text-sm font-semibold text-ink-inverse tracking-tight group-hover:text-ink-inverse/90 transition-colors">
            StreetSense AI
          </span>
          <span className="hidden md:inline text-xs text-ink-inverse/55 font-normal tracking-wide">
            Corridor Risk Intelligence
          </span>
        </div>
      </Link>

      <NavLinks />

      {actions && (
        <div className="ml-auto flex items-center gap-2">{actions}</div>
      )}
    </header>
  )
}
