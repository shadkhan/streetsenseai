'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Hint } from '@/components/ui/Hint'
import { cn } from '@/lib/utils'

const NAV_ITEMS = [
  { href: '/',           label: 'Map',        hint: 'Interactive corridor risk map — view active roadworks and risk scores' },
  { href: '/scheduling', label: 'Scheduling',  hint: 'Detect overlapping permit schedules before they cause network disruption' },
  { href: '/audit',      label: 'Audit',       hint: 'Review all AI Copilot and permit summary interactions for accountability' },
]

export function NavLinks() {
  const pathname = usePathname()
  return (
    <nav className="flex items-center gap-1 ml-4">
      {NAV_ITEMS.map(({ href, label, hint }) => (
        <Hint key={href} text={hint} side="bottom" delayDuration={600}>
          <Link
            href={href}
            className={cn(
              'px-3 py-1.5 rounded text-sm font-medium transition-colors',
              pathname === href
                ? 'bg-white/20 text-ink-inverse'
                : 'text-ink-inverse/75 hover:text-ink-inverse hover:bg-white/10',
            )}
          >
            {label}
          </Link>
        </Hint>
      ))}
    </nav>
  )
}
