'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

// ── Types ─────────────────────────────────────────────────────────────────────

interface ServiceResult {
  status: 'ok' | 'error' | 'not_configured'
  status_code?: number
  response_time_ms?: number
  response?: unknown
  error?: string
  message?: string
  usage?: { input_tokens: number; output_tokens: number }
  cost?: Record<string, string | number>
}

interface ApiHealth {
  anthropic: ServiceResult
  street_manager: ServiceResult
  os_datahub: ServiceResult
  mapbox: ServiceResult
  nuar: ServiceResult
}

interface DataSourceConfig {
  street_works: string
  road_classification: string
  usrn_resolution: string
  underground_assets: string
  ai_copilot: string
}

interface AdminStats {
  street_works: { total: number; active: number; by_status: Record<string, number> }
  corridors: { total: number; scored: number }
  nuar_assets: { total: number }
  audit_logs: { total: number }
  redis: Record<string, unknown>
  data_source_config: DataSourceConfig
  environment: string
  phase: number
  api_keys_configured: Record<string, boolean>
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={cn(
      'inline-flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded-full',
      status === 'ok'             && 'bg-risk-low-bg text-risk-low',
      status === 'error'          && 'bg-risk-critical-bg text-risk-critical',
      status === 'not_configured' && 'bg-surface-panel text-ink-muted',
    )}>
      <span className={cn(
        'w-1.5 h-1.5 rounded-full',
        status === 'ok'             && 'bg-risk-low',
        status === 'error'          && 'bg-risk-critical',
        status === 'not_configured' && 'bg-ink-subtle',
      )} />
      {status === 'ok' ? 'Online' : status === 'error' ? 'Error' : 'Not configured'}
    </span>
  )
}

function JsonViewer({ data }: { data: unknown }) {
  return (
    <pre className="text-[11px] bg-surface-sunken rounded-md p-3 overflow-auto max-h-56 text-ink-muted leading-relaxed font-mono">
      {JSON.stringify(data, null, 2)}
    </pre>
  )
}

// ── API Services Tab ─────────────────────────────────────────────────────────

const SERVICE_META: Record<string, { label: string; description: string; docsUrl?: string }> = {
  anthropic:      { label: 'Anthropic Claude',   description: 'AI Copilot (Sonnet 4) and permit summaries (Haiku 4.5)' },
  street_manager: { label: 'Street Manager v7',  description: 'UK roadworks permit data — free government open data' },
  os_datahub:     { label: 'OS Data Hub',         description: 'USRN resolver (NSG) and road classification (Open Roads) — free tier 1M calls/month' },
  mapbox:         { label: 'Mapbox GL',           description: 'Map tiles, geocoding and location search — free tier 50k loads/month' },
  nuar:           { label: 'NUAR',                description: 'Underground asset register — restricted access, synthetic data active for Phase 4' },
}

function ServiceCard({
  serviceKey,
  initial,
}: {
  serviceKey: string
  initial?: ServiceResult
}) {
  const meta = SERVICE_META[serviceKey]!
  const [result, setResult] = useState<ServiceResult | undefined>(initial)
  const [expanded, setExpanded] = useState(false)
  const [testing, setTesting] = useState(false)

  async function runTest() {
    setTesting(true)
    setExpanded(true)
    try {
      const res = await fetch(`${API_BASE}/admin/api-test/${serviceKey}`, { method: 'POST' })
      setResult(await res.json() as ServiceResult)
    } catch (e) {
      setResult({ status: 'error', error: String(e) })
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="rounded-lg border border-line bg-surface-raised overflow-hidden">
      <div className="flex items-start justify-between gap-4 px-4 py-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-sm font-medium text-ink">{meta.label}</span>
            {result && <StatusBadge status={result.status} />}
          </div>
          <p className="text-xs text-ink-muted">{meta.description}</p>
          {result?.message && (
            <p className="text-xs text-ink-subtle mt-1 italic">{result.message}</p>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {result && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs text-ink-muted hover:text-ink transition-colors"
            >
              {expanded ? 'Hide' : 'Details'}
            </button>
          )}
          <Button
            size="sm"
            onClick={runTest}
            disabled={testing}
            className="h-7 text-xs bg-brand text-ink-inverse hover:bg-brand/90"
          >
            {testing ? 'Testing…' : 'Test'}
          </Button>
        </div>
      </div>

      {expanded && result && (
        <div className="border-t border-line px-4 py-3 space-y-3 bg-surface-page">
          <div className="flex flex-wrap gap-4 text-xs">
            {result.status_code != null && (
              <span>
                <span className="text-ink-subtle">HTTP </span>
                <span className={cn('font-mono font-medium', result.status_code < 300 ? 'text-risk-low' : 'text-risk-critical')}>
                  {result.status_code}
                </span>
              </span>
            )}
            {result.response_time_ms != null && (
              <span>
                <span className="text-ink-subtle">Latency </span>
                <span className="font-mono font-medium text-ink">{result.response_time_ms} ms</span>
              </span>
            )}
            {result.usage && (
              <span>
                <span className="text-ink-subtle">Tokens </span>
                <span className="font-mono font-medium text-ink">
                  {result.usage.input_tokens}&#8593; {result.usage.output_tokens}&#8595;
                </span>
              </span>
            )}
          </div>

          {result.cost && Object.keys(result.cost).length > 0 && (
            <div className="rounded-md bg-brand-light border border-brand/20 px-3 py-2 space-y-0.5">
              <p className="text-[10px] font-medium text-brand uppercase tracking-wider mb-1">Cost / Subscription</p>
              {Object.entries(result.cost).map(([k, v]) => (
                <div key={k} className="flex gap-2 text-xs">
                  <span className="text-ink-subtle capitalize min-w-0 shrink-0">{k.replace(/_/g, ' ')}:</span>
                  <span className="text-ink font-medium">{String(v)}</span>
                </div>
              ))}
            </div>
          )}

          {result.error && (
            <p className="text-xs text-risk-critical font-mono bg-risk-critical-bg px-3 py-2 rounded-md">
              {result.error}
            </p>
          )}

          {result.response != null && (
            <div>
              <p className="text-[10px] text-ink-subtle uppercase tracking-wider mb-1">Response</p>
              <JsonViewer data={result.response} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function ApiServicesTab() {
  const [health, setHealth] = useState<ApiHealth | null>(null)
  const [loading, setLoading] = useState(true)
  const [debugLog, setDebugLog] = useState<string[]>([])

  useEffect(() => {
    setLoading(true)
    setDebugLog(prev => [...prev, `[${new Date().toISOString()}] GET /admin/api-health`])
    fetch(`${API_BASE}/admin/api-health`)
      .then(r => r.json())
      .then(data => {
        setHealth(data as ApiHealth)
        setDebugLog(prev => [...prev, `[${new Date().toISOString()}] Health check complete`])
      })
      .catch(e => setDebugLog(prev => [...prev, `[${new Date().toISOString()}] ERROR: ${e}`]))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-ink-muted">
          Click <strong>Test</strong> on any service to run a live API call and inspect the response, latency, and cost.
        </p>
        <Button
          size="sm"
          variant="outline"
          onClick={() => {
            setLoading(true)
            fetch(`${API_BASE}/admin/api-health`)
              .then(r => r.json())
              .then(data => setHealth(data as ApiHealth))
              .finally(() => setLoading(false))
          }}
          className="h-7 text-xs border-line text-ink-muted hover:text-ink"
        >
          Refresh All
        </Button>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[0, 1, 2, 3, 4].map(i => <Skeleton key={i} className="h-16 rounded-lg" />)}
        </div>
      ) : (
        <div className="space-y-3">
          {Object.entries(SERVICE_META).map(([key]) => (
            <ServiceCard
              key={key}
              serviceKey={key}
              initial={health ? (health as unknown as Record<string, ServiceResult>)[key] : undefined}
            />
          ))}
        </div>
      )}

      {debugLog.length > 0 && (
        <div>
          <p className="text-[10px] text-ink-subtle uppercase tracking-wider mb-1">Debug Log</p>
          <pre className="text-[11px] font-mono bg-surface-sunken rounded-md p-3 max-h-32 overflow-y-auto text-ink-muted leading-relaxed">
            {debugLog.join('\n')}
          </pre>
        </div>
      )}
    </div>
  )
}

// ── Data Sources Tab ──────────────────────────────────────────────────────────

const DOMAINS: Array<{ key: keyof DataSourceConfig; label: string; description: string }> = [
  { key: 'street_works',       label: 'Street Works',        description: 'Permit data from Street Manager API or seeded synthetic fixture' },
  { key: 'road_classification',label: 'Road Classification', description: 'OS Open Roads API or hardcoded synthetic road classes' },
  { key: 'usrn_resolution',    label: 'USRN Resolution',     description: 'OS NSG API for live lookups or synthetic USRN mappings' },
  { key: 'underground_assets', label: 'Underground Assets',  description: 'NUAR live data (restricted) or synthetic UN-008 generator' },
  { key: 'ai_copilot',         label: 'AI Copilot',          description: 'Anthropic Claude API or mocked word-by-word stream responses' },
]

const MODE_DESCRIPTIONS: Record<string, string> = {
  synthetic: 'Always use seeded fixture data — no external API calls',
  api:       'Always call the real external API — fails if unreachable',
  auto:      'Try real API first, silently fall back to synthetic on error',
}

function DataSourcesTab() {
  const [config, setConfig] = useState<DataSourceConfig | null>(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_BASE}/admin/data-source`)
      .then(r => r.json())
      .then(data => setConfig(data as DataSourceConfig))
      .finally(() => setLoading(false))
  }, [])

  async function save() {
    if (!config) return
    setSaving(true)
    try {
      await fetch(`${API_BASE}/admin/data-source`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <Skeleton className="h-64 rounded-lg" />

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-line p-4 bg-brand-light">
        <p className="text-xs text-brand font-medium mb-1">What this controls</p>
        <p className="text-xs text-ink-muted">
          Each domain can independently run against real external APIs, fixture synthetic data, or both (Auto = try API first, fall back to synthetic).
          Changes are stored in Redis and take effect immediately — no restart required.
        </p>
      </div>

      <div className="space-y-4">
        {DOMAINS.map(({ key, label, description }) => (
          <div key={key} className="rounded-lg border border-line p-4 space-y-3">
            <div>
              <p className="text-sm font-medium text-ink">{label}</p>
              <p className="text-xs text-ink-muted">{description}</p>
            </div>
            <div className="flex gap-2">
              {(['synthetic', 'api', 'auto'] as const).map(mode => (
                <button
                  key={mode}
                  onClick={() => setConfig(c => c ? { ...c, [key]: mode } : c)}
                  title={MODE_DESCRIPTIONS[mode]}
                  className={cn(
                    'flex-1 py-1.5 rounded-md text-xs font-medium border transition-colors capitalize',
                    config?.[key] === mode
                      ? 'bg-brand text-ink-inverse border-brand'
                      : 'border-line text-ink-muted hover:border-brand/40 hover:text-ink bg-surface-panel',
                  )}
                >
                  {mode}
                </button>
              ))}
            </div>
            <p className="text-[10px] text-ink-subtle italic">
              {config ? MODE_DESCRIPTIONS[config[key]] : ''}
            </p>
          </div>
        ))}
      </div>

      <Button
        onClick={save}
        disabled={saving || !config}
        className="bg-brand text-ink-inverse hover:bg-brand/90"
      >
        {saved ? 'Saved' : saving ? 'Saving…' : 'Save Configuration'}
      </Button>
    </div>
  )
}

// ── Loaded Data Tab ───────────────────────────────────────────────────────────

function LoadedDataTab() {
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [seeding, setSeeding] = useState<string | null>(null)
  const [seedMsg, setSeedMsg] = useState<Record<string, string>>({})

  const refresh = useCallback(() => {
    setLoading(true)
    fetch(`${API_BASE}/admin/stats`)
      .then(r => r.json())
      .then(data => setStats(data as AdminStats))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { refresh() }, [refresh])

  async function reseed(domain: string, endpoint: string) {
    setSeeding(domain)
    setSeedMsg(m => ({ ...m, [domain]: 'Seeding…' }))
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, { method: 'POST' })
      const data = await res.json() as Record<string, unknown>
      setSeedMsg(m => ({ ...m, [domain]: `Done — ${JSON.stringify(data).slice(0, 80)}` }))
      refresh()
    } catch (e) {
      setSeedMsg(m => ({ ...m, [domain]: `Error: ${e}` }))
    } finally {
      setSeeding(null)
    }
  }

  if (loading) return <Skeleton className="h-64 rounded-lg" />

  const sw = stats?.street_works
  const cr = stats?.corridors
  const nu = stats?.nuar_assets
  const al = stats?.audit_logs

  return (
    <div className="space-y-5">
      {/* Street Works */}
      <div className="rounded-lg border border-line overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-line bg-surface-panel">
          <div>
            <p className="text-sm font-medium text-ink">Street Works (Street Manager)</p>
            <p className="text-xs text-ink-muted">{sw?.total ?? '—'} total · {sw?.active ?? '—'} active</p>
          </div>
          <Button
            size="sm"
            variant="outline"
            disabled={seeding === 'works'}
            onClick={() => reseed('works', '/works/admin/seed')}
            className="h-7 text-xs border-line text-ink-muted hover:text-ink"
          >
            {seeding === 'works' ? 'Seeding…' : 'Reseed Synthetic'}
          </Button>
        </div>
        <div className="px-4 py-3 grid grid-cols-4 gap-3">
          {sw ? Object.entries(sw.by_status).map(([status, count]) => (
            <div key={status} className="text-center">
              <p className="text-lg font-semibold text-ink tabular-nums">{count}</p>
              <p className="text-[10px] text-ink-subtle capitalize">{status.replace(/_/g, ' ')}</p>
            </div>
          )) : null}
        </div>
        {seedMsg.works && <p className="px-4 pb-2 text-xs text-ink-subtle font-mono">{seedMsg.works}</p>}
      </div>

      {/* Corridors */}
      <div className="rounded-lg border border-line overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-line bg-surface-panel">
          <div>
            <p className="text-sm font-medium text-ink">Corridors (Risk Engine)</p>
            <p className="text-xs text-ink-muted">{cr?.total ?? '—'} total · {cr?.scored ?? '—'} scored</p>
          </div>
          <Button
            size="sm"
            variant="outline"
            disabled={seeding === 'corridors'}
            onClick={() => reseed('corridors', '/corridors/admin/score')}
            className="h-7 text-xs border-line text-ink-muted hover:text-ink"
          >
            {seeding === 'corridors' ? 'Scoring…' : 'Rescore All'}
          </Button>
        </div>
        <div className="px-4 py-3 flex gap-6">
          <div>
            <p className="text-2xl font-semibold text-ink tabular-nums">{cr?.total ?? '—'}</p>
            <p className="text-xs text-ink-subtle">Corridors defined</p>
          </div>
          <div>
            <p className="text-2xl font-semibold text-ink tabular-nums">{cr?.scored ?? '—'}</p>
            <p className="text-xs text-ink-subtle">Risk scored</p>
          </div>
        </div>
      </div>

      {/* NUAR */}
      <div className="rounded-lg border border-line overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-line bg-surface-panel">
          <div>
            <p className="text-sm font-medium text-ink">NUAR Underground Assets</p>
            <p className="text-xs text-ink-muted">{nu?.total ?? '—'} assets seeded (synthetic)</p>
          </div>
          <Button
            size="sm"
            variant="outline"
            disabled={seeding === 'nuar'}
            onClick={() => reseed('nuar', '/nuar/admin/seed')}
            className="h-7 text-xs border-line text-ink-muted hover:text-ink"
          >
            {seeding === 'nuar' ? 'Seeding…' : 'Reseed Synthetic'}
          </Button>
        </div>
        <div className="px-4 py-3">
          <p className="text-2xl font-semibold text-ink tabular-nums">{nu?.total ?? 0}</p>
          <p className="text-xs text-ink-subtle">Synthetic underground assets (gas · electric · water · telecoms)</p>
        </div>
      </div>

      {/* Audit */}
      <div className="rounded-lg border border-line px-4 py-3 flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-ink">AI Audit Log</p>
          <p className="text-xs text-ink-muted">{al?.total ?? '—'} interaction records</p>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={refresh}
          className="h-7 text-xs border-line text-ink-muted hover:text-ink"
        >
          Refresh
        </Button>
      </div>
    </div>
  )
}

// ── System Tab ────────────────────────────────────────────────────────────────

function SystemTab() {
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_BASE}/admin/stats`)
      .then(r => r.json())
      .then(data => setStats(data as AdminStats))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Skeleton className="h-64 rounded-lg" />

  const keys = stats?.api_keys_configured ?? {}

  return (
    <div className="space-y-5">
      {/* API keys */}
      <div className="rounded-lg border border-line overflow-hidden">
        <div className="px-4 py-3 border-b border-line bg-surface-panel">
          <p className="text-sm font-medium text-ink">API Keys Configured</p>
          <p className="text-xs text-ink-muted">Values are never shown — only whether each key is present</p>
        </div>
        <div className="divide-y divide-line">
          {Object.entries(keys).map(([service, configured]) => (
            <div key={service} className="flex items-center justify-between px-4 py-2.5">
              <span className="text-sm text-ink capitalize">{service.replace(/_/g, ' ')}</span>
              <span className={cn(
                'text-xs font-medium px-2 py-0.5 rounded-full',
                configured ? 'bg-risk-low-bg text-risk-low' : 'bg-surface-sunken text-ink-subtle',
              )}>
                {configured ? 'Configured' : 'Not set'}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Runtime */}
      <div className="rounded-lg border border-line overflow-hidden">
        <div className="px-4 py-3 border-b border-line bg-surface-panel">
          <p className="text-sm font-medium text-ink">Runtime</p>
        </div>
        <div className="divide-y divide-line">
          {[
            ['Phase', stats?.phase ?? '—'],
            ['Environment', stats?.environment ?? '—'],
            ['Redis memory', String((stats?.redis as Record<string, unknown>)?.used_memory_human ?? '—')],
            ['Redis clients', String((stats?.redis as Record<string, unknown>)?.connected_clients ?? '—')],
          ].map(([k, v]) => (
            <div key={String(k)} className="flex items-center justify-between px-4 py-2.5">
              <span className="text-sm text-ink-muted">{k}</span>
              <span className="text-sm font-medium text-ink font-mono">{String(v)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AdminPage() {
  const router = useRouter()

  async function logout() {
    await fetch('/api/admin/logout', { method: 'POST' })
    router.push('/admin/login')
  }

  return (
    <div className="min-h-screen bg-surface-page">
      {/* Admin header */}
      <header className="h-14 bg-brand flex items-center px-6 gap-4">
        <span className="text-sm font-semibold text-ink-inverse">StreetSense AI</span>
        <span className="text-xs text-ink-inverse/60 font-normal">Admin Console</span>
        <div className="ml-auto flex items-center gap-3">
          <span className="text-xs text-ink-inverse/50">Development mode</span>
          <button
            onClick={logout}
            className="text-xs text-ink-inverse/70 hover:text-ink-inverse transition-colors"
          >
            Sign out
          </button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-brand">Admin Console</h1>
          <p className="text-sm text-ink-muted mt-1">
            API health, data source configuration, and system diagnostics
          </p>
        </div>

        <Tabs defaultValue="apis">
          <TabsList className="mb-6 bg-surface-panel border border-line">
            <TabsTrigger value="apis"   className="text-sm">API Services</TabsTrigger>
            <TabsTrigger value="data"   className="text-sm">Data Sources</TabsTrigger>
            <TabsTrigger value="loaded" className="text-sm">Loaded Data</TabsTrigger>
            <TabsTrigger value="system" className="text-sm">System</TabsTrigger>
          </TabsList>

          <TabsContent value="apis">   <ApiServicesTab />   </TabsContent>
          <TabsContent value="data">   <DataSourcesTab />   </TabsContent>
          <TabsContent value="loaded"> <LoadedDataTab />    </TabsContent>
          <TabsContent value="system"> <SystemTab />        </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}
