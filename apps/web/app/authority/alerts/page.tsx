import { auth } from '@clerk/nextjs/server'
import { UserButton } from '@clerk/nextjs'

export default async function AuthorityAlertsPage() {
  await auth.protect()

  return (
    <div className="min-h-screen bg-surface-page">
      <header className="border-b border-line bg-white px-6 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-brand">StreetSense AI</h1>
          <p className="text-xs text-ink-muted">Authority Portal — Alerts</p>
        </div>
        <UserButton />
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        <div>
          <h2 className="text-2xl font-semibold text-brand">Active Alerts</h2>
          <p className="text-sm text-ink-muted mt-1">
            TRO conflicts and high-risk corridor notifications for your authority
          </p>
        </div>

        <div className="rounded-lg border border-line bg-white p-6 text-center">
          <p className="text-sm text-ink-muted">
            No alerts configured yet. Alerts will be delivered here when TRO conflicts
            are detected against active permits in your authority area.
          </p>
        </div>
      </main>
    </div>
  )
}
