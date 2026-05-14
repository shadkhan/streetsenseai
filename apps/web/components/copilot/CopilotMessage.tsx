'use client'

import { formatDistanceToNow } from 'date-fns'
import { PermitReference } from '@/components/ui/PermitReference'
import type { CopilotMessage as CopilotMessageType } from '@/types'

interface Props {
  message: CopilotMessageType
  isStreaming?: boolean
  onSuggestedQuestion?: (q: string) => void
  onPermitClick?: (ref: string) => void
}

function renderInline(
  text: string,
  keyPrefix: string,
  onPermitClick?: (ref: string) => void,
) {
  const parts = text.split(/([A-Z0-9]+\/\d{4}\/\d+)/)
  const permitTest = /^[A-Z0-9]+\/\d{4}\/\d+$/
  return parts.map((part, i) =>
    permitTest.test(part) ? (
      <PermitReference
        key={`${keyPrefix}-${i}`}
        reference={part}
        className="mx-0.5"
        onClick={onPermitClick ? () => onPermitClick(part) : undefined}
      />
    ) : (
      <span key={`${keyPrefix}-${i}`}>{part}</span>
    ),
  )
}

function renderContent(
  content: string,
  isStreaming: boolean,
  onPermitClick?: (ref: string) => void,
) {
  const paragraphs = content.split(/\n{2,}/)
  return (
    <>
      {paragraphs.map((para, pi) => (
        <p key={pi} className={pi > 0 ? 'mt-2' : ''}>
          {renderInline(para.replace(/\n/g, ' '), String(pi), onPermitClick)}
          {isStreaming && pi === paragraphs.length - 1 && (
            <span className="inline-block w-0.5 h-3.5 bg-brand ml-0.5 align-middle animate-pulse" />
          )}
        </p>
      ))}
    </>
  )
}

export function CopilotMessage({
  message,
  isStreaming = false,
  onSuggestedQuestion,
  onPermitClick,
}: Props) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="bg-surface-panel rounded-lg px-3 py-2 max-w-[85%]">
          <p className="text-sm text-ink">{message.content}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-2.5">
      {/* Response text */}
      <div className="text-sm text-ink leading-relaxed">
        {message.content
          ? renderContent(message.content, isStreaming, onPermitClick)
          : isStreaming && (
              <span className="inline-block w-0.5 h-3.5 bg-brand animate-pulse" />
            )}
      </div>

      {/* Citations — shown only when streaming is done */}
      {!isStreaming && message.citations.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {message.citations.map((c) => (
            <PermitReference
              key={c.permitReference}
              reference={c.permitReference}
              onClick={onPermitClick ? () => onPermitClick(c.permitReference) : undefined}
            />
          ))}
        </div>
      )}

      {/* Suggested follow-ups — only after response completes */}
      {!isStreaming && message.suggestedQuestions && message.suggestedQuestions.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {message.suggestedQuestions.map((q) => (
            <button
              key={q}
              onClick={() => onSuggestedQuestion?.(q)}
              className="text-xs text-brand border border-brand/30 bg-brand-light
                         rounded px-2 py-1 hover:bg-brand hover:text-ink-inverse
                         transition-colors text-left"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Data source footer */}
      <p className="text-xs text-ink-subtle pt-1 border-t border-line">
        Based on Street Manager data
        {message.dataTimestamp && (
          <> · Updated {formatDistanceToNow(new Date(message.dataTimestamp))} ago</>
        )}
      </p>
    </div>
  )
}
