import { Header } from '@/components/layout/Header'
import { MapWrapper } from '@/components/map/MapWrapper'
import { RiskLegend } from '@/components/map/RiskLegend'
import { MapStyleControl } from '@/components/map/MapStyleControl'
import { CorridorSheet } from '@/components/map/CorridorSheet'
import { TimeWindowControl } from '@/components/map/TimeWindowControl'
import { CopilotTrigger } from '@/components/copilot/CopilotTrigger'
import { CopilotSheet } from '@/components/copilot/CopilotSheet'
import { PermitSummarySheet } from '@/components/copilot/PermitSummarySheet'

export default function MapPage() {
  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <Header />
      <main className="flex-1 relative min-h-0">
        <MapWrapper />
        {/* Top-left control panel — style switcher, 2D/3D, risk legend */}
        <div className="absolute top-3 left-3 z-10 flex flex-col gap-2">
          <MapStyleControl />
          <RiskLegend />
        </div>
        <TimeWindowControl />
        <CopilotTrigger />
        <CorridorSheet />
        <CopilotSheet />
        <PermitSummarySheet />
      </main>
    </div>
  )
}
