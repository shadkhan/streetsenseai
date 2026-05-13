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
