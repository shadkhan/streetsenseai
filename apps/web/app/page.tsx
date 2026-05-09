import { RiskBadge } from '@/components/risk/RiskBadge'
import { PermitReference } from '@/components/ui/PermitReference'

export default function Home() {
  return (
    <div className="bg-surface-page min-h-screen px-6 py-10">
      <div className="max-w-2xl mx-auto space-y-10">

        {/* Header */}
        <div>
          <h1 className="text-2xl font-semibold text-brand mb-1">
            StreetSense AI
          </h1>
          <p className="text-sm text-ink-muted">
            Cross-Authority Roadworks Intelligence Platform — design token verification
          </p>
        </div>

        {/* Risk badge tokens */}
        <section className="space-y-3">
          <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider">
            Risk Level Tokens
          </p>
          <div className="bg-surface-raised border border-line rounded-lg p-4 flex flex-wrap gap-3">
            <RiskBadge level="low" />
            <RiskBadge level="medium" />
            <RiskBadge level="high" />
            <RiskBadge level="critical" />
          </div>
          <div className="bg-surface-raised border border-line rounded-lg p-4 flex flex-wrap gap-3">
            <RiskBadge level="low" showDot={false} />
            <RiskBadge level="medium" showDot={false} />
            <RiskBadge level="high" showDot={false} />
            <RiskBadge level="critical" showDot={false} />
          </div>
        </section>

        {/* Permit reference */}
        <section className="space-y-3">
          <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider">
            Permit Reference Component
          </p>
          <div className="bg-surface-raised border border-line rounded-lg p-4">
            <p className="text-sm text-ink mb-2">
              Active permit on A38 southbound:{' '}
              <PermitReference reference="WG7/2025/04001234" />
            </p>
            <p className="text-sm text-ink-muted">
              USRN: <span className="font-mono text-xs">41507223</span>
            </p>
          </div>
        </section>

        {/* Brand colour tokens */}
        <section className="space-y-3">
          <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider">
            Brand &amp; Surface Tokens
          </p>
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-brand rounded-lg p-3 text-center">
              <p className="text-xs text-ink-inverse font-medium">brand</p>
              <p className="text-xs text-ink-inverse opacity-70">#1E3A5F</p>
            </div>
            <div className="bg-brand-light border border-line rounded-lg p-3 text-center">
              <p className="text-xs text-brand font-medium">brand-light</p>
              <p className="text-xs text-brand-muted">#E8EEF5</p>
            </div>
            <div className="bg-surface-panel border border-line rounded-lg p-3 text-center">
              <p className="text-xs text-ink font-medium">surface-panel</p>
              <p className="text-xs text-ink-muted">#F4F4F5</p>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="border-t border-line pt-6">
          <p className="text-xs text-ink-subtle">
            Phase 1 — Foundation. Map and copilot coming soon.
          </p>
        </footer>

      </div>
    </div>
  )
}
