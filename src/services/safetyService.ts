import { SafetyAssessment, RiskLevel } from '@/types';
import { FASTAPI_BASE_URL } from '@/config/api';

/**
 * Fetch computed safety assessment from ORCA FastAPI backend (/api/safety)
 */
export async function fetchFastAPISafety(lat: number, lon: number, timeWindow: string = 'now') {
  if (typeof lat !== 'number' || typeof lon !== 'number' || isNaN(lat) || isNaN(lon)) {
    throw new Error(`Invalid coordinates passed to fetchFastAPISafety: lat=${lat}, lon=${lon}`);
  }
  const url = timeWindow && timeWindow !== 'now'
    ? `${FASTAPI_BASE_URL}/api/safety?latitude=${lat}&longitude=${lon}&time_window=${timeWindow}`
    : `${FASTAPI_BASE_URL}/api/safety?latitude=${lat}&longitude=${lon}`;
  const response = await fetch(url, {
    cache: 'no-store',
  });
  if (!response.ok) {
    throw new Error(`FastAPI /api/safety returned HTTP ${response.status}`);
  }
  return response.json();
}

export function getSafetyAssessment(locName: string = 'Coastal Sector'): SafetyAssessment {
  return {
    riskLevel: 'low',
    riskScore: 0,
    maxScore: 100,
    area: locName,
    validityPeriod: 'Real-Time Telemetry',
    verdictTitle: `ASSESSMENT INITIALIZING (${locName.toUpperCase()})`,
    verdictSubtitle: 'FETCHING REAL-TIME MARINE TELEMETRY',
    description: `Connecting to Open-Meteo & ORCA Safety Engine for ${locName}...`,
    factors: [
      { id: 'waves', label: 'factor_waves', value: '--', status: 'Connecting...', statusColor: 'green', icon: 'waves' },
      { id: 'wind', label: 'factor_wind', value: '--', status: 'Connecting...', statusColor: 'green', icon: 'wind' },
      { id: 'lightning', label: 'factor_lightning', value: 'Clear', status: 'No alert detected', statusColor: 'green', icon: 'zap' },
      { id: 'cyclone', label: 'factor_cyclone', value: 'Clear', status: 'No depression', statusColor: 'green', icon: 'tornado' },
      { id: 'rain', label: 'factor_rain', value: '--', status: 'Connecting...', statusColor: 'green', icon: 'cloudRain' },
      { id: 'geofence', label: 'factor_geofence', value: 'Clear', status: 'Safe boundary', statusColor: 'green', icon: 'shield' },
    ],
    reasoning: [`Retrieving live environmental telemetry for ${locName}...`],
    recommendation: `Retrieving live environmental telemetry for ${locName}.`,
    disclaimer: 'AI assessment based on real-time environmental data. Verify official marine advisories before departure.',
  };
}

export function getSafetyAssessmentByLevel(level: RiskLevel, locName: string = 'Coastal Sector'): SafetyAssessment {
  const base = getSafetyAssessment(locName);
  base.riskLevel = level;
  base.riskScore = level === 'high' ? 78 : level === 'moderate' ? 48 : 18;
  return base;
}
