'use client'

import { useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Button } from '@/components/ui/button'

function LoginForm() {
  const router = useRouter()
  const params = useSearchParams()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch('/api/admin/auth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      const data = await res.json() as { ok: boolean; error?: string }
      if (data.ok) {
        router.push(params.get('from') ?? '/admin')
      } else {
        setError(data.error ?? 'Invalid credentials')
      }
    } catch {
      setError('Network error — check the dev server is running')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-ink-subtle uppercase tracking-wider">Username</label>
        <input
          type="text"
          value={username}
          onChange={e => setUsername(e.target.value)}
          autoComplete="username"
          required
          className="w-full h-9 px-3 rounded-md border border-line bg-surface-panel text-sm text-ink outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand"
        />
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-ink-subtle uppercase tracking-wider">Password</label>
        <input
          type="password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          autoComplete="current-password"
          required
          className="w-full h-9 px-3 rounded-md border border-line bg-surface-panel text-sm text-ink outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand"
        />
      </div>

      {error && (
        <p className="text-xs text-risk-critical bg-risk-critical-bg px-3 py-2 rounded-md">{error}</p>
      )}

      <Button
        type="submit"
        disabled={loading}
        className="w-full bg-brand text-ink-inverse hover:bg-brand/90"
      >
        {loading ? 'Signing in…' : 'Sign in'}
      </Button>
    </form>
  )
}

export default function AdminLoginPage() {
  return (
    <div className="min-h-screen bg-surface-page flex items-center justify-center">
      <div className="w-full max-w-sm">
        <div className="bg-surface-raised rounded-xl border border-line shadow-lg p-8 space-y-6">
          <div className="text-center space-y-1">
            <h1 className="text-xl font-semibold text-brand">StreetSense AI</h1>
            <p className="text-sm text-ink-muted">Admin Console</p>
          </div>

          <Suspense fallback={<div className="h-32 animate-pulse rounded-md bg-surface-panel" />}>
            <LoginForm />
          </Suspense>

          <p className="text-center text-[10px] text-ink-subtle">
            Development access only · Credentials stored in .env.local
          </p>
        </div>
      </div>
    </div>
  )
}
