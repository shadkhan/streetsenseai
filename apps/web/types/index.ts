// ── Geometry primitives (no external dependency) ──────────────
export type Position = [number, number]                    // [lng, lat]
export interface PointGeometry      { type: 'Point';      coordinates: Position }
export interface LineStringGeometry { type: 'LineString'; coordinates: Position[] }
export type WorksGeometry = PointGeometry | LineStringGeometry
export type CorridorGeometry = LineStringGeometry          // Corridors are linear ONLY

// ── Risk ──────────────────────────────────────────────────────
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical'

// ── Street Manager Permit ─────────────────────────────────────
export interface StreetWork {
  permitReference: string          // e.g. "WG7/2025/04001234"
  usrn: string                     // e.g. "41507223"
  streetName: string
  authority: string
  promoter: string
  promoterLicenceNumber: string
  workType: string
  trafficManagementType: string
  restrictionType: string
  proposedStartDate: string        // ISO 8601
  proposedEndDate: string          // ISO 8601
  actualStartDate?: string
  actualEndDate?: string
  status: StreetWorkStatus
  geometry: WorksGeometry
  riskScore?: RiskLevel
}

export type StreetWorkStatus =
  | 'submitted'
  | 'granted'
  | 'permit_modification_request'
  | 'refused'
  | 'revoked'
  | 'in_progress'
  | 'completed'
  | 'closed'

// ── Corridor (always a LineString) ────────────────────────────
export interface Corridor {
  id: string
  name: string                     // e.g. "A38 — Birmingham City Centre"
  roadClassification: 'A' | 'B' | 'C' | 'unclassified'
  geometry: CorridorGeometry       // Always LineString — never Point
  riskLevel: RiskLevel | null      // null until CR-003/CR-004 scores the corridor
  riskScore: number | null         // 0–100; null until scored
  riskFactors: RiskFactor[]
  concurrentWorks: StreetWork[]
  activeWorksCount: number
  plannedWorksCount: number
  lastCalculated: string | null    // ISO 8601; null until scored
}

export interface RiskFactor {
  factor: string
  weight: number
  contribution: number
  description: string
}

// ── Road Info (SM-004) ───────────────────────────────────────
export interface RoadInfo {
  roadClassification: string         // "A Road", "B Road", "Motorway", "Unclassified"
  roadFunction?: string
  roadName?: string                  // "A38", "B4140", etc.
  formOfWay?: string                 // "Single Carriageway", "Dual Carriageway", etc.
  isPrimaryRoute: boolean            // true for Motorway or A Road
}

// ── NUAR (never persisted — query on demand only) ─────────────
export interface NUARAsset {
  assetId: string
  assetType: 'gas' | 'electric' | 'water' | 'telecoms' | 'other'
  depth?: number                   // metres
  pressureTier?: string
  voltageLevel?: string
  operatorName: string
  geometry: WorksGeometry
  // ⚠ NEVER store this in the database. In-memory cache 1h max.
}

export interface StrikeRisk {
  permitReference: string
  overallRisk: RiskLevel
  assetCount: number
  assetsByType: Record<string, number>
  highestRiskAsset?: {
    type: string
    operator: string
    risk: string
  }
  calculatedAt: string
}

// ── Promoter Compliance ───────────────────────────────────────
export interface PromoterCompliance {
  promoterLicenceNumber: string
  promoterName: string
  totalWorks: number
  overrunRate: number              // 0–1 percentage
  lateStartRate: number
  missingReinstatementRate: number
  complianceScore: number          // 0–100, higher is better
  trend: 'improving' | 'stable' | 'deteriorating'
  region: string
  lastUpdated: string
}

// ── Copilot ───────────────────────────────────────────────────
export interface CopilotMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations: PermitCitation[]
  suggestedQuestions?: string[]
  dataTimestamp: string
  createdAt: string
}

export interface PermitCitation {
  permitReference: string
  streetName: string
  promoter: string
  relevance: string
}

// ── Audit Trail (AI-007) ─────────────────────────────
export interface AuditLogEntry {
  id: string
  interactionType: 'copilot' | 'permit_summary'
  query: string
  response: string
  citations: PermitCitation[] | null
  sessionId: string | null
  createdAt: string  // ISO 8601
}

// ── NUAR Asset Density (UN-002) ───────────────────────────────────────────────
export interface AssetDensity {
  corridorId: string
  totalAssets: number
  assetsByType: Record<string, number>  // { gas: 23, electric: 21, ... }
  weightedScore: number                  // pre-normalised weighted sum
  densityScore: number                   // 0–100
  densityLevel: RiskLevel
  calculatedAt: string                   // ISO 8601
}

// ── Composite Risk (UN-006) ───────────────────────────────────
export interface CompositeRisk {
  corridorId: string
  surfaceScore: number          // 0–100 from CR-003
  surfaceLevel: RiskLevel
  undergroundScore: number      // 0–100 from UN-002 (0 if no assets in range)
  undergroundLevel: RiskLevel
  compositeScore: number        // 0–100 weighted combination
  compositeLevel: RiskLevel
  surfaceWeight: number         // 0.60
  undergroundWeight: number     // 0.40
  undergroundAssetsInRange: number
  calculatedAt: string
}

// ── Non-Compliance Analytics (NC-001 – NC-006) ───────────────
export interface FPNOpportunity {
  permitReference: string
  promoter: string
  promoterLicenceNumber: string
  streetName: string
  authority: string
  proposedEndDate: string
  actualEndDate: string
  overrunDays: number
}

export interface ComplianceSummary {
  totalPromoters: number
  avgComplianceScore: number
  worstOffender: PromoterCompliance | null
  bestPerformer: PromoterCompliance | null
  totalFpnOpportunities: number
  calculatedAt: string
}

export interface MonthlyTrend {
  month: string              // "2026-01"
  complianceScore: number    // 0–100
  totalWorks: number
  overruns: number
}

// ── Scheduling (AI-005) ───────────────────────────────
export interface SchedulingConflict {
  corridorId: string
  corridorName: string
  permitA: string
  permitB: string
  streetName: string
  overlapStart: string   // ISO 8601 date
  overlapEnd: string     // ISO 8601 date
  overlapDays: number
  severity: RiskLevel
  severityScore: number  // 0–100
  promoterA: string
  promoterB: string
  trafficManagementA: string
  trafficManagementB: string
  recommendation: string
}
