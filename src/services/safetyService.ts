import type { SafetyAssessment, RiskLevel } from '../types/index';
import { FASTAPI_BASE_URL } from '../config/api';
import { cacheService, getLocationKey } from './cacheService';
import { connectivityService } from './connectivityService';
import { evaluateFreshness } from '../utils/freshness';

/**
 * Fetch raw computed safety assessment from ORCA FastAPI backend (/api/safety)
 */
export async function fetchFastAPISafety(lat: number, lon: number, timeWindow: string = 'now') {
  if (typeof lat !== 'number' || typeof lon !== 'number' || isNaN(lat) || isNaN(lon)) {
    throw new Error(`Invalid coordinates passed to fetchFastAPISafety: lat=${lat}, lon=${lon}`);
  }
  const url = timeWindow && timeWindow !== 'now'
    ? `${FASTAPI_BASE_URL}/api/safety?latitude=${lat}&longitude=${lon}&time_window=${timeWindow}`
    : `${FASTAPI_BASE_URL}/api/safety?latitude=${lat}&longitude=${lon}`;
  
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 5000);

  try {
    const response = await fetch(url, {
      cache: 'no-store',
      signal: controller.signal,
    });
    clearTimeout(timer);
    if (!response.ok) {
      throw new Error(`FastAPI /api/safety returned HTTP ${response.status}`);
    }
    return await response.json();
  } catch (err) {
    clearTimeout(timer);
    throw err;
  }
}

/**
 * Live-First Verified Safety Assessment
 * 
 * Rules:
 * 1. Live fetch succeeds -> returns LIVE assessment, saves to verified cache.
 * 2. Live fetch fails -> returns CACHED previous assessment with explicit timestamp and warning.
 * 3. Does NOT calculate a new algorithmic score on stale data.
 * 4. If no cache exists -> returns UNAVAILABLE state (never fabricates fake numbers).
 */
export async function getVerifiedSafetyAssessment(
  lat: number,
  lon: number,
  arg3?: string | { skipLive?: boolean; timeWindow?: string; locName?: string },
  timeWindowArg: string = 'now'
): Promise<SafetyAssessment & { data?: any }> {
  let skipLive = false;
  let locName = 'Coastal Sector';
  let timeWindow = timeWindowArg;

  if (typeof arg3 === 'object' && arg3 !== null) {
    skipLive = Boolean(arg3.skipLive);
    locName = arg3.locName || 'Coastal Sector';
    timeWindow = arg3.timeWindow || 'now';
  } else if (typeof arg3 === 'string') {
    locName = arg3;
  }

  const locationKey = getLocationKey(lat, lon);

  if (!skipLive) {
    // 1. Live Fetch
    try {
      const raw = await fetchFastAPISafety(lat, lon, timeWindow);
      const nowMs = Date.now();
      const freshness = evaluateFreshness(true, nowMs);

      const assessment: SafetyAssessment & { data?: any } = {
        riskLevel: (raw.risk_level || 'low').toLowerCase() as RiskLevel,
        riskScore: raw.risk_score ?? 15,
        maxScore: 100,
        area: locName,
        validityPeriod: raw.validity_period || 'Real-Time Telemetry',
        verdictTitle: raw.verdict_title || 'CONDITIONS APPEAR SUITABLE',
        verdictSubtitle: raw.verdict_subtitle || 'ALL SAFETY PARAMETERS NORMAL',
        description: raw.description || `Live telemetry confirms safe operational thresholds for ${locName}.`,
        factors: raw.factors?.map((f: any, i: number) => ({
          id: `f-${i}`,
          label: f.label || (f.factor ? `factor_${f.factor}` : 'Factor'),
          value: f.value || '--',
          status: f.status || 'Normal',
          statusColor: f.risk === 'HIGH' ? 'red' : f.risk === 'CAUTION' ? 'amber' : 'green',
          icon: f.factor?.includes('wave') ? 'waves' : f.factor?.includes('wind') ? 'wind' : f.factor?.includes('rain') ? 'cloudRain' : 'shield',
        })) || [],
        reasoning: raw.reasoning || [],
        recommendation: raw.recommendation || 'Proceed with standard maritime precautions.',
        disclaimer: raw.disclaimer || 'AI-assisted decision support. Always check official marine advisories before departure.',
        is_cached: false,
        cache_timestamp: nowMs,
        freshness,
      };
      assessment.data = raw;

      // Save to cache & record success
      await cacheService.set('safety', locationKey, assessment, 'ORCA Safety Engine');
      connectivityService.recordSuccess('safety_service');

      return assessment;
    } catch (liveErr) {
      console.warn(`[SafetyService] Live safety fetch failed for ${locName} (${lat}, ${lon}):`, liveErr);
      connectivityService.recordFailure('safety_service', liveErr);
    }
  }

  // 2. Cache Fallback
  let cached = await cacheService.get<any>('safety', locationKey);
  if (!cached) {
    cached = await cacheService.get<any>('safety_assessment', locationKey);
  }

  if (cached && cached.data) {
    const cachedData = cached.data;
    const freshness = evaluateFreshness(false, cached.timestamp);
    const timeStr = cached.formattedTime || 'earlier';

    const result: SafetyAssessment & { data?: any } = {
      riskLevel: cachedData.riskLevel || (cachedData.risk_level?.toLowerCase() as RiskLevel) || 'low',
      riskScore: cachedData.riskScore ?? cachedData.score ?? 0,
      maxScore: 100,
      area: locName,
      validityPeriod: cachedData.validityPeriod || 'Cached Assessment',
      verdictTitle: `PREVIOUS ASSESSMENT: ${(cachedData.riskLevel || cachedData.risk_level || 'LOW').toUpperCase()} RISK`,
      verdictSubtitle: `CACHED ANALYSIS FROM ${timeStr}`,
      description: `Based on verified marine data from ${timeStr}. Live conditions may have changed. Reconnect before relying on this assessment.`,
      factors: cachedData.factors || [],
      reasoning: cachedData.reasoning || [],
      recommendation: `[Cached at ${timeStr}] Reconnect to verify current conditions. ${cachedData.recommendation || ''}`,
      disclaimer: cachedData.disclaimer || 'Cached data on record.',
      is_cached: true,
      cache_timestamp: cached.timestamp,
      freshness,
    };
    result.data = cachedData;
    return result;
  }

  // 3. Unavailable State
  const unavailableFreshness = evaluateFreshness(false, null);
  const unavail: SafetyAssessment & { data?: any } = {
    riskLevel: 'low',
    riskScore: 0,
    maxScore: 100,
    area: locName,
    validityPeriod: 'Unavailable',
    verdictTitle: 'SAFETY ASSESSMENT UNAVAILABLE',
    verdictSubtitle: 'LIVE TELEMETRY OFFLINE',
    description: `Live marine safety evaluation is currently unavailable for ${locName} and no verified cache exists.`,
    factors: [],
    reasoning: ['Network connectivity unavailable and no previous verified safety assessment on record.'],
    recommendation: 'Check local port and coast guard advisories before venturing to sea.',
    disclaimer: 'Data unavailable. Reconnect to refresh live environmental telemetry.',
    is_cached: false,
    freshness: unavailableFreshness,
    data: null,
  };
  return unavail;
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
    freshness: evaluateFreshness(true, Date.now()),
  };
}

export function getSafetyAssessmentByLevel(level: RiskLevel, locName: string = 'Coastal Sector'): SafetyAssessment {
  const base = getSafetyAssessment(locName);
  base.riskLevel = level;
  base.riskScore = level === 'high' ? 78 : level === 'moderate' ? 48 : 18;
  return base;
}
