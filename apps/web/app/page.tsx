import { Header } from '@/components/layout/Header'
import { MapWrapper } from '@/components/map/MapWrapper'
import { RiskLegend } from '@/components/map/RiskLegend'
import { CorridorSheet } from '@/components/map/CorridorSheet'
import { TimeWindowControl } from '@/components/map/TimeWindowControl'
import { CopilotTrigger } from '@/components/copilot/CopilotTrigger'
import { CopilotSheet } from '@/components/copilot/CopilotSheet'

export default function MapPage() {
  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <Header />
      <main className="flex-1 relative min-h-0">
        <MapWrapper />
        <RiskLegend />
        <TimeWindowControl />
        <CopilotTrigger />
        <CorridorSheet />
        <CopilotSheet />
      </main>
    </div>
  )
}
