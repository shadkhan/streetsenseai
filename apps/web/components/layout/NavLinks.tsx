'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Menu } from 'lucide-react'
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet'
import { Hint } from '@/components/ui/Hint'
import { cn } from '@/lib/utils'

const NAV_ITEMS = [
  { href: '/',           label: 'Map',        hint: 'Interactive corridor risk map — view active roadworks and risk scores' },
  { href: '/scheduling', label: 'Scheduling',  hint: 'Detect overlapping permit schedules before they cause network disruption' },
  { href: '/analytics',  label: 'Analytics',   hint: 'Non-compliance analytics — promoter performance league table, FPN opportunities and AI briefing' },
  { href: '/dtros',      label: 'D-TROs',      hint: 'Browse Digital Traffic Regulation Orders — speed limits, road closures, parking and zone restrictions' },
  { href: '/audit',      label: 'Audit',       hint: 'Review all AI Copilot and permit summary interactions for accountability' },
]

export function NavLinks() {
  const pathname = usePathname()
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <>
      {/* Desktop nav — hidden below md */}
      <nav className="hidden md:flex items-center gap-1 ml-4">
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

      {/* Mobile hamburger button — visible below md, pushed to far right */}
      <div className="md:hidden ml-auto">
        <button
          onClick={() => setMobileOpen(true)}
          aria-label="Open navigation menu"
          className="p-2 rounded text-ink-inverse/75 hover:text-ink-inverse hover:bg-white/10 transition-colors"
        >
          <Menu className="w-5 h-5" />
        </button>
      </div>

      {/* Mobile nav Sheet */}
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="w-64 !p-0 bg-brand border-r border-white/10">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <div className="pt-16 px-3 pb-4 space-y-1">
            <p className="text-[10px] font-medium text-ink-inverse/40 uppercase tracking-wider px-3 pb-3">
              Navigation
            </p>
            {NAV_ITEMS.map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                onClick={() => setMobileOpen(false)}
                className={cn(
                  'flex items-center px-3 py-2.5 rounded text-sm font-medium transition-colors',
                  pathname === href
                    ? 'bg-white/20 text-ink-inverse'
                    : 'text-ink-inverse/75 hover:text-ink-inverse hover:bg-white/10',
                )}
              >
                {label}
              </Link>
            ))}
          </div>
        </SheetContent>
      </Sheet>
    </>
  )
}
