'use client'

import { useEffect, useRef, useState } from 'react'
import { Bot, Send } from 'lucide-react'
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Hint } from '@/components/ui/Hint'
import { CopilotMessage } from './CopilotMessage'
import { usePanels } from '@/lib/stores/panels'
import { logInteraction } from '@/lib/api'
import { getSessionId } from '@/lib/session'
import type { CopilotMessage as CopilotMessageType, PermitCitation } from '@/types'
import { cn } from '@/lib/utils'

// ── Seed questions shown in the empty state ────────────────────────────────────

const SEED_QUESTIONS = [
  "What's the current risk level on the A38 corridors?",
  'Are there any scheduling conflicts in Birmingham this week?',
  'Which promoter has the most active works right now?',
]

// ── Streaming state ─────────────────────────────────────────────────────────

type StreamChunk =
  | { type: 'text'; content: string }
  | { type: 'meta'; citations: PermitCitation[]; suggestedQuestions: string[]; dataTimestamp: string }
  | { type: 'done' }

// ── Component ──────────────────────────────────────────────────────────────────

export function CopilotSheet() {
  const { active, close, openPermit } = usePanels()
  const isOpen = active === 'copilot'

  const [messages, setMessages] = useState<CopilotMessageType[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingId, setStreamingId] = useState<string | null>(null)

  const scrollRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll to bottom when messages update
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages])

  // Focus input when sheet opens
  useEffect(() => {
    if (isOpen) setTimeout(() => textareaRef.current?.focus(), 300)
  }, [isOpen])

  const submit = async (question: string) => {
    const q = question.trim()
    if (!q || isStreaming) return

    const now = new Date().toISOString()
    const userId = `u-${Date.now()}`
    const assistantId = `a-${Date.now()}`

    setMessages((prev) => [
      ...prev,
      { id: userId, role: 'user', content: q, citations: [], dataTimestamp: now, createdAt: now },
      { id: assistantId, role: 'assistant', content: '', citations: [], dataTimestamp: now, createdAt: now },
    ])
    setInput('')
    setIsStreaming(true)
    setStreamingId(assistantId)

    let fullText = ''
    let fullCitations: PermitCitation[] = []

    try {
      const res = await fetch('/api/copilot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q }),
      })

      if (!res.ok || !res.body) throw new Error('Stream unavailable')

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.trim()) continue
          let chunk: StreamChunk
          try {
            chunk = JSON.parse(line) as StreamChunk
          } catch {
            continue
          }

          if (chunk.type === 'text') {
            fullText += chunk.content
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, content: m.content + chunk.content } : m
              )
            )
          } else if (chunk.type === 'meta') {
            fullCitations = chunk.citations
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? {
                      ...m,
                      citations: chunk.citations,
                      suggestedQuestions: chunk.suggestedQuestions,
                      dataTimestamp: chunk.dataTimestamp,
                    }
                  : m
              )
            )
          }
        }
      }

      if (fullText) {
        void logInteraction({
          interactionType: 'copilot',
          query: q,
          response: fullText,
          citations: fullCitations.length > 0 ? fullCitations : null,
          sessionId: getSessionId(),
        })
      }
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: 'Unable to get a response. Please try again.' }
            : m
        )
      )
    } finally {
      setIsStreaming(false)
      setStreamingId(null)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void submit(input)
    }
  }

  const handleSuggestedQuestion = (q: string) => {
    setInput(q)
    void submit(q)
  }

  return (
    <Sheet open={isOpen} onOpenChange={(open) => { if (!open) close() }}>
      <SheetContent
        side="right"
        className="w-[480px] sm:max-w-[480px] !p-0 !gap-0 flex flex-col"
      >
        <SheetTitle className="sr-only">StreetSense Copilot</SheetTitle>

        {/* Header */}
        <div className="flex-shrink-0 flex items-center gap-2.5 px-4 h-12 pr-12 bg-brand border-b border-brand/30">
          <Bot className="w-4 h-4 text-ink-inverse opacity-80" />
          <span className="text-sm font-semibold text-ink-inverse">StreetSense Copilot</span>
          <span className="ml-auto text-xs text-ink-inverse opacity-40 font-mono">AI-001</span>
        </div>

        {/* Messages */}
        <ScrollArea className="flex-1 min-h-0">
          <div className="px-4 py-4 space-y-5" ref={scrollRef}>
            {messages.length === 0 ? (
              // Empty state with seed questions
              <div className="flex flex-col items-center text-center pt-8 pb-4 gap-4">
                <div className="w-10 h-10 rounded-full bg-brand-light flex items-center justify-center">
                  <Bot className="w-5 h-5 text-brand-muted" />
                </div>
                <div>
                  <p className="text-sm font-medium text-ink mb-1">
                    Ask about roadworks, permits, or risk
                  </p>
                  <p className="text-xs text-ink-muted">
                    Across Birmingham City Centre corridors
                  </p>
                </div>
                <Separator className="w-full" />
                <div className="w-full space-y-2">
                  <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider">
                    Suggested
                  </p>
                  {SEED_QUESTIONS.map((q) => (
                    <Hint key={q} text="Click to ask this question" side="left">
                      <button
                        onClick={() => handleSuggestedQuestion(q)}
                        aria-label={`Ask: ${q}`}
                        className="w-full text-left text-xs text-brand border border-brand/30 bg-brand-light
                                   rounded px-3 py-2 hover:bg-brand hover:text-ink-inverse transition-colors"
                      >
                        {q}
                      </button>
                    </Hint>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg) => (
                <CopilotMessage
                  key={msg.id}
                  message={msg}
                  isStreaming={isStreaming && msg.id === streamingId}
                  onSuggestedQuestion={handleSuggestedQuestion}
                  onPermitClick={openPermit}
                />
              ))
            )}
          </div>
        </ScrollArea>

        {/* Input area */}
        <div className="flex-shrink-0 border-t border-line bg-surface-raised p-3">
          <div className={cn(
            'flex items-end gap-2 rounded-lg border bg-white px-3 py-2 transition-colors',
            'border-line focus-within:border-brand focus-within:ring-1 focus-within:ring-brand/20',
          )}>
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isStreaming}
              placeholder="Ask about roadworks, permits, risk..."
              rows={1}
              className="flex-1 resize-none bg-transparent text-sm text-ink placeholder:text-ink-subtle
                         focus:outline-none disabled:opacity-50 leading-relaxed
                         max-h-24 overflow-y-auto"
              style={{ fieldSizing: 'content' } as React.CSSProperties}
            />
            <Hint text="Send message (Enter)" side="left">
              <button
                onClick={() => void submit(input)}
                disabled={!input.trim() || isStreaming}
                aria-label="Send message"
                className={cn(
                  'flex-shrink-0 w-7 h-7 rounded flex items-center justify-center transition-colors',
                  input.trim() && !isStreaming
                    ? 'bg-brand text-ink-inverse hover:bg-brand/90'
                    : 'bg-surface-panel text-ink-subtle',
                )}
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </Hint>
          </div>
          <p className="text-xs text-ink-subtle mt-1.5 text-center">
            Shift + Enter for new line · Enter to send
          </p>
        </div>
      </SheetContent>
    </Sheet>
  )
}
