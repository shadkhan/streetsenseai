/**
 * Returns a stable session ID for the current browser session.
 * Stored in sessionStorage so it resets when the tab closes.
 * Used to correlate audit log entries from the same session.
 */
export function getSessionId(): string {
  if (typeof window === 'undefined') return 'server'
  const key = 'ss-session-id'
  let id = sessionStorage.getItem(key)
  if (!id) {
    id = `s-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    sessionStorage.setItem(key, id)
  }
  return id
}
