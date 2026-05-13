'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'

const NAV_ITEMS = [
  { href: '/', label: 'Map' },
  { href: '/scheduling', label: 'Scheduling' },
]

export function NavLinks() {
  const pathname = usePathname()
  return (
    <nav className="flex items-center gap-1 ml-4">
      {NAV_ITEMS.map(({ href, label }) => (
        <Link
          key={href}
          href={href}
          className={cn(
            'px-3 py-1.5 rounded text-sm font-medium transition-colors',
            pathname === href
              ? 'bg-white/20 text-ink-inverse'
              : 'text-ink-inverse/60 hover:text-ink-inverse hover:bg-white/10',
          )}
        >
          {label}
        </Link>
      ))}
    </nav>
  )
}
