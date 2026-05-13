'use client'

import dynamic from 'next/dynamic'
import { MapSkeleton } from './MapSkeleton'

// next/dynamic with ssr:false must live in a Client Component (Next.js 15 rule)
const MapCanvas = dynamic(
  () => import('./MapCanvas').then((m) => m.MapCanvas),
  { ssr: false, loading: () => <MapSkeleton /> },
)

export function MapWrapper() {
  return <MapCanvas />
}
