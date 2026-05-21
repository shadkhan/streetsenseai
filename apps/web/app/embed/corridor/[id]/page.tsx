import type { Corridor } from '@/types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function getCorridor(id: string): Promise<Corridor | null> {
  try {
    const res = await fetch(`${API_BASE}/embed/corridor/${id}`, {
      next: { revalidate: 60 },
    })
    if (!res.ok) return null
    return res.json() as Promise<Corridor>
  } catch {
    return null
  }
}


interface Props {
  params: Promise<{ id: string }>
  searchParams: Promise<{ theme?: string }>
}

export default async function EmbedCorridorPage({ params, searchParams }: Props) {
  const { id } = await params
  const { theme } = await searchParams
  const isDark = theme === 'dark'

  const corridor = await getCorridor(id)

  const containerClass = isDark
    ? 'bg-[#1A1F2E] text-white border-[#2D3448]'
    : 'bg-white text-ink border-line'

  if (!corridor) {
    return (
      <div className={`rounded-xl border p-4 font-sans text-sm ${containerClass}`}>
        <p className="text-ink-muted">Corridor not found</p>
        <p className="text-xs text-ink-subtle mt-1 font-mono">{id}</p>
      </div>
    )
  }

  const level = corridor.riskLevel ?? 'low'
  const score = Math.round(corridor.riskScore ?? 0)

  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>{corridor.name} — StreetSense AI</title>
        <meta name="robots" content="noindex" />
        <style>{`
          * { box-sizing: border-box; margin: 0; padding: 0; }
          body { font-family: system-ui, sans-serif; background: transparent; }
        `}</style>
      </head>
      <body>
        <div
          style={{
            borderRadius: '12px',
            border: '1px solid',
            borderColor: isDark ? '#2D3448' : '#E2E8F0',
            background: isDark ? '#1A1F2E' : '#FFFFFF',
            color: isDark ? '#F1F5F9' : '#1E293B',
            padding: '16px',
            fontFamily: 'system-ui, -apple-system, sans-serif',
            maxWidth: '360px',
          }}
        >
          <div style={{ marginBottom: '12px' }}>
            <p style={{ fontSize: '10px', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: isDark ? '#94A3B8' : '#64748B', marginBottom: '2px' }}>
              {corridor.roadClassification === 'A' ? 'A Road' : corridor.roadClassification === 'B' ? 'B Road' : corridor.roadClassification === 'C' ? 'C Road' : 'Road Corridor'}
            </p>
            <p style={{ fontSize: '15px', fontWeight: 600, lineHeight: 1.3 }}>
              {corridor.name}
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
            <span style={{
              fontSize: '11px', fontWeight: 600, padding: '3px 8px', borderRadius: '9999px',
              background: level === 'critical' ? '#FEE2E2' : level === 'high' ? '#FFEDD5' : level === 'medium' ? '#FEF9C3' : '#DCFCE7',
              color: level === 'critical' ? '#991B1B' : level === 'high' ? '#9A3412' : level === 'medium' ? '#854D0E' : '#166534',
            }}>
              {level.charAt(0).toUpperCase() + level.slice(1)} risk
            </span>
            <span style={{
              fontSize: '22px', fontWeight: 700,
              color: level === 'critical' ? '#BE2222' : level === 'high' ? '#CC470D' : level === 'medium' ? '#B5680A' : '#1A9E62',
            }}>
              {score}<span style={{ fontSize: '13px', fontWeight: 400, color: isDark ? '#64748B' : '#94A3B8' }}>/100</span>
            </span>
          </div>

          <div style={{ display: 'flex', gap: '16px', fontSize: '12px', color: isDark ? '#94A3B8' : '#64748B' }}>
            <span>{corridor.activeWorksCount} active works</span>
            <span>{corridor.plannedWorksCount} planned</span>
          </div>

          <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: `1px solid ${isDark ? '#2D3448' : '#E2E8F0'}`, fontSize: '10px', color: isDark ? '#475569' : '#94A3B8' }}>
            StreetSense AI · Street Manager data
          </div>
        </div>
      </body>
    </html>
  )
}
