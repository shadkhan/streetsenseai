import { auth } from '@clerk/nextjs/server'
import { UserButton } from '@clerk/nextjs'

export default async function AuthorityDashboardPage() {
  const { userId, orgId } = await auth()

  return (
    <div className="min-h-screen bg-surface-page">
      <header className="border-b border-line bg-white px-6 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-brand">StreetSense AI</h1>
          <p className="text-xs text-ink-muted">Authority Portal</p>
        </div>
        <UserButton />
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        <div>
          <h2 className="text-2xl font-semibold text-brand">Authority Dashboard</h2>
          <p className="text-sm text-ink-muted mt-1">
            Corridor risk overview and active works for your authority area
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="rounded-lg border border-line bg-white p-4 space-y-1">
            <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider">Organisation</p>
            <p className="text-sm text-ink font-mono">{orgId ?? userId ?? '—'}</p>
          </div>
          <div className="rounded-lg border border-line bg-white p-4 space-y-1">
            <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider">Active Corridors</p>
            <p className="text-2xl font-semibold text-ink">—</p>
          </div>
          <div className="rounded-lg border border-line bg-white p-4 space-y-1">
            <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider">Open Conflicts</p>
            <p className="text-2xl font-semibold text-risk-high">—</p>
          </div>
        </div>

        <p className="text-sm text-ink-muted italic">
          Full authority analytics are available in the{' '}
          <a href="/analytics" className="text-brand underline underline-offset-2">
            compliance dashboard
          </a>
          . This portal will be expanded in Phase 6 post-launch.
        </p>
      </main>
    </div>
  )
}
