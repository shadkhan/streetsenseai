// Layer 1 — Input gate: length limit, injection deny-list, off-topic patterns
// Layer 2 — Topic classifier stub (always passes; swap for Haiku call when API key present)
// Layer 4 — Output audit: flag suspicious response content without suppressing it
// Layer 5 — Rate limiter: 10 requests per 60 s per sessionId (module-level sliding window)
//
// See AI_GUARDRAILS.md for the full threat model and upgrade paths.

export const MAX_QUERY_CHARS = 600

// ── Injection deny-list ────────────────────────────────────────────────────────

const INJECTION_PATTERNS: RegExp[] = [
  /ignore\s+(all\s+)?(previous|prior|above)\s+instructions/i,
  /reveal\s+(your\s+)?(system\s+)?(prompt|instructions|context)/i,
  /\bDAN\b/,
  /jailbreak/i,
  /pretend\s+(you\s+are|to\s+be)\s+(a\s+)?(?!road|highway|traffic|permit|authority|works)/i,
  /act\s+as\s+(a\s+)?(?!road|highway|traffic|permit|authority|works|street)/i,
  /bypass\s+(your\s+)?(restrictions|guidelines|rules|filters|safety)/i,
  /you\s+are\s+now\s+(?!analysing|monitoring|checking|reviewing|assessing)/i,
  /override\s+(safety|guard|filter|instruction|system)/i,
  /forget\s+(all\s+)?(previous|prior)\s+(instructions|context|training)/i,
  /new\s+persona[:\s]/i,
  /disregard\s+(all\s+)?(previous|prior|above)/i,
]

// ── Off-topic explicit deny-list ──────────────────────────────────────────────
// Catches common misuse patterns by verb+subject. NOT the primary defence —
// the domain keyword allow-list below is the main off-topic gate.

const OFF_TOPIC_PATTERNS: RegExp[] = [
  /\b(write|compose|draft|create)\s+(a\s+)?(poem|essay|story|song|letter|email|blog\s+post|novel)/i,
  /\b(help\s+me\s+)?(code|program|debug|fix\s+my\s+code|write\s+code|build\s+a\s+website)/i,
  /\b(what\s+is\s+the\s+(meaning|purpose)\s+of\s+life)\b/i,
  /\b(stock|crypto|bitcoin|ethereum|investment|financial\s+advice|share\s+price)/i,
  /\b(recipe|how\s+to\s+cook|cooking\s+tip|ingredient)/i,
  /\b(translate\s+(this\s+)?to|how\s+do\s+you\s+say\s+.+\s+in\s+\w+)\b/i,
  /\bChatGPT\b|\bGPT-4\b|\bGemini\b|\bLlama\b|\bMistral\b/i,
  /\b(write\s+me\s+a|can\s+you\s+write)\s+(cover\s+letter|cv|resume|resignation)/i,
]

// ── Domain keyword allow-list ──────────────────────────────────────────────────
// Any query ≥ 15 characters that contains ZERO of these roadworks-domain terms
// is rejected as off-topic. This catches "tell me about Vet Medicine", "who won
// the World Cup", etc. without needing to enumerate every possible off-topic topic.
//
// Short queries (< 15 chars) are exempt — they may be navigation commands like
// "help", "hello", or single road names that don't need full context.

// City names are intentionally excluded — "AI engineer in Birmingham" must not pass.
// Any legitimate roadworks query contains a roadworks term alongside the city name.
const DOMAIN_KEYWORD = /\b(road|street|works?|permit|corridor|traffic|lane|closure|junction|carriageway|footway|usrn|tro|ttro|d-?tro|risk|disruption|conflicts?|clash|overlap\w*|schedul\w*|compliance|overrun\w*|promoter|authority|highway|utility|gas|water|electric|telecoms|broadband|nuar|underground|asset|strike|depth|cable|pipe|duct|fpn|section\s*5[89]|tma\s*2004|nrswa|lane\s*rental|a\d{1,3}|b\d{3,4})\b/i

// ── Rate limiter (Layer 5) ─────────────────────────────────────────────────────

const RATE_LIMIT_MAX = 10
const RATE_LIMIT_WINDOW_MS = 60_000

// Module-level store — per-process. Replace Map with Redis for multi-process deployments.
const rateLimitStore = new Map<string, number[]>()

// ── Types ──────────────────────────────────────────────────────────────────────

export type GuardStatus = 'ok' | 'too_long' | 'injection' | 'off_topic' | 'rate_limited'

export interface GuardResult {
  allowed: boolean
  status: GuardStatus
  flagged: boolean
  flagReason: string | null
  message?: string
}

// ── guardInput ─────────────────────────────────────────────────────────────────

/**
 * Runs Layers 1 and 5 against the incoming query.
 * Rate limit is checked first so injection attempts are also rate-counted.
 */
export function guardInput(query: string, sessionId: string): GuardResult {
  // Layer 5: sliding window rate limit
  const now = Date.now()
  const existing = rateLimitStore.get(sessionId) ?? []
  const window = existing.filter((t) => now - t < RATE_LIMIT_WINDOW_MS)
  if (window.length >= RATE_LIMIT_MAX) {
    return {
      allowed: false,
      status: 'rate_limited',
      flagged: true,
      flagReason: 'rate_limited',
      message: 'Too many requests — please wait a moment before trying again.',
    }
  }
  window.push(now)
  rateLimitStore.set(sessionId, window)

  // Layer 1a: length gate
  if (query.length > MAX_QUERY_CHARS) {
    return {
      allowed: false,
      status: 'too_long',
      flagged: false,
      flagReason: null,
      message: `Query must be ${MAX_QUERY_CHARS} characters or fewer (yours: ${query.length}).`,
    }
  }

  // Layer 1b: injection deny-list
  for (const pattern of INJECTION_PATTERNS) {
    if (pattern.test(query)) {
      return {
        allowed: false,
        status: 'injection',
        flagged: true,
        flagReason: 'injection_attempt',
        message:
          'That query cannot be processed. Please ask about roadworks, permits, or traffic management.',
      }
    }
  }

  // Layer 1c: explicit off-topic deny-list
  for (const pattern of OFF_TOPIC_PATTERNS) {
    if (pattern.test(query)) {
      return {
        allowed: false,
        status: 'off_topic',
        flagged: false,
        flagReason: null,
        message:
          'I can only assist with UK roadworks intelligence, permits, and corridor risk. Please ask a related question.',
      }
    }
  }

  // Layer 1d: domain keyword allow-list
  // Substantive queries (≥ 15 chars) must reference at least one roadworks concept.
  if (query.trim().length >= 15 && !DOMAIN_KEYWORD.test(query)) {
    return {
      allowed: false,
      status: 'off_topic',
      flagged: false,
      flagReason: null,
      message:
        'I can only assist with UK roadworks intelligence, permits, and corridor risk. Please ask a related question.',
    }
  }

  return { allowed: true, status: 'ok', flagged: false, flagReason: null }
}

// ── classifyTopic (Layer 2 stub) ───────────────────────────────────────────────

/**
 * Stub topic classifier — always returns allowed in mock mode.
 * Replace body with a Claude Haiku single-turn call when ANTHROPIC_API_KEY is active.
 */
export function classifyTopic(_query: string): GuardResult {
  return { allowed: true, status: 'ok', flagged: false, flagReason: null }
}

// ── checkOutput (Layer 4) ──────────────────────────────────────────────────────

const OUTPUT_FLAG_PATTERNS: [RegExp, string][] = [
  [/my\s+system\s+prompt\s+(is|says|reads|states)/i, 'system_prompt_leak'],
  [/i\s+(am\s+not\s+bound\s+by|have\s+no\s+restrictions|can\s+ignore\s+my)/i, 'guardrail_bypass'],
  [/\b(national\s+insurance\s+number|nino|ni\s+number)\b/i, 'pii_nino'],
  [/\b(password|secret[_\s]key|api[_\s]key|bearer\s+token)\s*[:=]\s*\S+/i, 'credential_leak'],
]

/**
 * Scans the assembled AI response for output policy violations.
 * Returns a flag reason string if a violation is detected, or null if clean.
 * Does NOT suppress the response — caller decides whether to show it.
 */
export function checkOutput(response: string): string | null {
  for (const [pattern, reason] of OUTPUT_FLAG_PATTERNS) {
    if (pattern.test(response)) return reason
  }
  return null
}
