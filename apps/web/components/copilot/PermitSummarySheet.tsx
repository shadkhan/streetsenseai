'use client'

import { useEffect, useRef, useState } from 'react'
import { FileText } from 'lucide-react'
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet'
import { ScrollArea } from '@/components/ui/scroll-area'
import { PermitReference } from '@/components/ui/PermitReference'
import { usePanels } from '@/lib/stores/panels'
import { logInteraction } from '@/lib/api'
import { getSessionId } from '@/lib/session'

type StreamChunk = { type: 'text'; content: string } | { type: 'done' }

export function PermitSummarySheet() {
  const { active, permitRef, close } = usePanels()
  const isOpen = active === 'permit'

  const [summary, setSummary] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const lastFetchedRef = useRef<string | null>(null)

  // Start streaming when the sheet opens with a new permit reference
  useEffect(() => {
    if (!isOpen || !permitRef) return
    if (permitRef === lastFetchedRef.current) return

    lastFetchedRef.current = permitRef
    setSummary('')
    setIsStreaming(true)

    let cancelled = false

    async function stream() {
      let fullSummary = ''
      try {
        const res = await fetch(
          `/api/permit-summary?ref=${encodeURIComponent(permitRef!)}`,
        )
        if (!res.ok || !res.body) throw new Error('Stream unavailable')

        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (!cancelled) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''

          for (const line of lines) {
            if (!line.trim()) continue
            try {
              const chunk = JSON.parse(line) as StreamChunk
              if (chunk.type === 'text' && !cancelled) {
                fullSummary += chunk.content
                setSummary((prev) => prev + chunk.content)
              }
            } catch { /* skip malformed */ }
          }
        }

        if (fullSummary && !cancelled) {
          void logInteraction({
            interactionType: 'permit_summary',
            query: permitRef!,
            response: fullSummary,
            citations: null,
            sessionId: getSessionId(),
          })
        }
      } catch {
        if (!cancelled) {
          setSummary('Unable to load permit summary. Please check your connection and try again.')
        }
      } finally {
        if (!cancelled) setIsStreaming(false)
      }
    }

    void stream()
    return () => { cancelled = true }
  }, [isOpen, permitRef])

  // Clear content when sheet closes so the next open starts fresh
  useEffect(() => {
    if (!isOpen) {
      setSummary('')
      lastFetchedRef.current = null
    }
  }, [isOpen])

  const paragraphs = summary.split(/\n{2,}/)

  return (
    <Sheet open={isOpen} onOpenChange={(open) => { if (!open) close() }}>
      <SheetContent
        side="right"
        className="w-full sm:w-[420px] sm:max-w-[420px] !p-0 !gap-0 flex flex-col"
      >
        <SheetTitle className="sr-only">Permit Summary</SheetTitle>

        {/* Header */}
        <div className="flex-shrink-0 px-4 pt-4 pb-3 pr-12 border-b border-line bg-surface-panel">
          <div className="flex items-center gap-1.5 mb-1.5">
            <FileText className="w-3.5 h-3.5 text-ink-subtle" />
            <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider">
              Permit Summary
            </p>
          </div>
          {permitRef && <PermitReference reference={permitRef} />}
        </div>

        {/* Streaming body */}
        <ScrollArea className="flex-1 min-h-0">
          <div className="px-4 py-4 text-sm text-ink leading-relaxed space-y-3">
            {summary === '' && isStreaming && (
              <span className="inline-block w-0.5 h-3.5 bg-brand animate-pulse" />
            )}
            {paragraphs.map((para, i) => (
              <p key={i}>
                {para.replace(/\n/g, ' ')}
                {isStreaming && i === paragraphs.length - 1 && summary !== '' && (
                  <span className="inline-block w-0.5 h-3.5 bg-brand ml-0.5 align-middle animate-pulse" />
                )}
              </p>
            ))}
          </div>
        </ScrollArea>

        {/* Footer */}
        <div className="flex-shrink-0 border-t border-line px-4 py-2.5 bg-surface-panel">
          <p className="text-xs text-ink-subtle">
            Based on Street Manager data · AI-006 plain-English summary
          </p>
        </div>
      </SheetContent>
    </Sheet>
  )
}
