import { Header } from '@/components/layout/Header'
import { MapWrapper } from '@/components/map/MapWrapper'
import { CorridorSheet } from '@/components/map/CorridorSheet'
import { TimeWindowControl } from '@/components/map/TimeWindowControl'

export default function MapPage() {
  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <Header />
      <main className="flex-1 relative min-h-0">
        <MapWrapper />
        <TimeWindowControl />
        <CorridorSheet />
      </main>
    </div>
  )
}
