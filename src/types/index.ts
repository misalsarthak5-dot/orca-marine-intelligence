// ============================================================
// ORCA — Domain Types
// ============================================================

export type Language = 'en' | 'hi' | 'mr';

export type RiskLevel = 'low' | 'moderate' | 'high';

export type AgentStatusType = 'ready' | 'processing' | 'complete';

export type MapLayerType =
  | 'pfz'
  | 'weather'
  | 'sst'
  | 'chlorophyll'
  | 'risk'
  | 'geofence'
  | 'route';

// ── Marine Conditions ───────────────────────────────────────

export interface MarineCondition {
  id: string;
  label: string;
  value: string;
  unit: string;
  delta?: string;
  deltaDirection?: 'up' | 'down' | 'stable';
  status: string;
  statusColor: 'green' | 'amber' | 'red' | 'blue' | 'gray';
  icon: string;
  detail?: string;
  source?: string;
}

// ── Safety Assessment ───────────────────────────────────────

export interface SafetyFactor {
  id: string;
  label: string;
  value: string;
  status: string;
  statusColor: 'green' | 'amber' | 'red';
  icon: string;
}

export interface SafetyAssessment {
  riskLevel: RiskLevel;
  riskScore: number;
  maxScore: number;
  area: string;
  validityPeriod: string;
  verdictTitle: string;
  verdictSubtitle: string;
  description: string;
  factors: SafetyFactor[];
  reasoning: string[];
  recommendation: string;
  disclaimer: string;
}

// ── PFZ Zones ───────────────────────────────────────────────

export type PFZProbability = 'high' | 'medium' | 'low';

export interface PFZZone {
  id: string;
  name: string;
  coordinates: [number, number]; // [lat, lng]
  boundary: [number, number][]; // polygon points
  distance: string;
  sst: string;
  sstStatus: string;
  chlorophyll: string;
  chlorophyllStatus: string;
  marineRisk: RiskLevel;
  probability: PFZProbability;
  recommendation: string;
}

// ── Marine Alerts ───────────────────────────────────────────

export type AlertSeverity = 'critical' | 'warning' | 'info';

export interface MarineAlert {
  id: string;
  type: string;
  severity: AlertSeverity;
  title: string;
  description: string;
  location: string;
  distance?: string;
  validUntil: string;
  source: string;
  coordinates?: [number, number];
}

// ── Route Recommendations ───────────────────────────────────

export interface RouteWaypoint {
  id: string;
  label: string;
  coordinates: [number, number];
  type: 'start' | 'waypoint' | 'destination';
}

export interface AvoidZone {
  id: string;
  label: string;
  reason: string;
  boundary: [number, number][];
  severity: AlertSeverity;
}

export interface RouteRecommendation {
  id: string;
  name: string;
  description: string;
  waypoints: RouteWaypoint[];
  avoidZones: AvoidZone[];
  safeCorridorPath: [number, number][];
  estimatedRisk: RiskLevel;
  estimatedDistance: string;
  estimatedTime: string;
}

// ── Evidence ────────────────────────────────────────────────

export interface EvidenceSource {
  id: string;
  name: string;
  type: 'ocean' | 'weather' | 'advisory' | 'satellite' | 'geospatial';
  provider: string;
  timestamp: string;
  description?: string;
}

// ── Chat / Ask ORCA ─────────────────────────────────────────

export interface ChatAttachment {
  type: 'safety' | 'map' | 'chart' | 'pfz' | 'route';
  label: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'orca';
  content: string;
  timestamp: string;
  riskLevel?: RiskLevel;
  verdictTitle?: string;
  factors?: SafetyFactor[];
  recommendation?: string;
  attachments?: ChatAttachment[];
  pfz?: PFZZone;
  avoidanceZones?: { label: string; reason: string }[];
  trendData?: TrendDataPoint[];
  trendNarrative?: string;
}

export interface SuggestionChip {
  id: string;
  label: string;
  query: string;
  icon?: string;
}

// ── Agent Network ───────────────────────────────────────────

export interface AgentInfo {
  id: string;
  name: string;
  shortName: string;
  status: AgentStatusType;
  icon: string;
  latency?: string;
}

// ── Trend / Productivity ────────────────────────────────────

export interface TrendDataPoint {
  month: string;
  sst: number;
  chlorophyll: number;
}

// ── Translations ────────────────────────────────────────────

export interface TranslationStrings {
  // Navigation
  nav_dashboard: string;
  nav_liveMap: string;
  nav_askOrca: string;
  nav_fleet: string;
  nav_alerts: string;
  nav_intelligence: string;
  nav_history: string;
  nav_settings: string;
  nav_support: string;

  // Header
  header_greeting: string;
  header_subtitle: string;
  header_lastUpdated: string;
  header_fishingSafety: string;
  header_conditionsSuitable: string;
  header_conditionsCaution: string;
  header_conditionsNotRecommended: string;
  header_validTomorrow: string;

  // Marine Metrics
  metric_sst: string;
  metric_chlorophyll: string;
  metric_wind: string;
  metric_waves: string;
  metric_precipitation: string;
  metric_tide: string;

  // Safety Assessment
  safety_title: string;
  safety_lowRisk: string;
  safety_moderateRisk: string;
  safety_highRisk: string;
  safety_conditionsSuitable: string;
  safety_conditionsCaution: string;
  safety_conditionsNotRecommended: string;
  safety_quickFactors: string;
  safety_whyTitle: string;
  safety_verifiedEvidence: string;
  safety_viewEvidence: string;
  safety_viewRiskMap: string;
  safety_exploreReasoning: string;
  safety_disclaimer: string;
  safety_area: string;
  safety_assessment: string;
  safety_risk: string;

  // Map
  map_title: string;
  map_subtitle: string;
  map_searchPlaceholder: string;
  map_assessedArea: string;

  // Ask ORCA
  ask_title: string;
  ask_subtitle: string;
  ask_placeholder: string;
  ask_query: string;
  ask_suggestion1: string;
  ask_suggestion2: string;
  ask_suggestion3: string;
  ask_suggestion4: string;
  ask_suggestion5: string;
  ask_suggestedFor: string;

  // Pipeline
  pipeline_ask: string;
  pipeline_plan: string;
  pipeline_retrieve: string;
  pipeline_reason: string;
  pipeline_recommend: string;
  pipeline_explain: string;

  // Alerts
  alerts_title: string;
  alerts_active: string;
  alerts_noAlerts: string;
  alerts_viewOnMap: string;

  // Agent Network
  agents_title: string;
  agents_latency: string;
  agents_freshness: string;

  // ORCA Intelligence
  intel_title: string;
  intel_actionSuggested: string;
  intel_routeRecommendation: string;
  intel_reviewRoute: string;
  intel_simulate: string;
  intel_whyTitle: string;
  intel_suggestedSupport: string;
  intel_sendWaypoint: string;

  // Evidence
  evidence_title: string;

  // Common
  common_recommendation: string;
  common_viewOnMap: string;
  common_verdict: string;
  common_connected: string;
  common_lastSynced: string;
  common_dataConnection: string;

  // Factors
  factor_waves: string;
  factor_wind: string;
  factor_lightning: string;
  factor_cyclone: string;
  factor_rain: string;
  factor_geofence: string;

  // Categories
  cat_marineIntelligence: string;
  cat_pfzDiscovery: string;
  cat_safetyAssessment: string;
  cat_routeIntelligence: string;
}

export type Translations = Record<Language, TranslationStrings>;
