import { HazardAssessment } from '@/types';
import { FASTAPI_BASE_URL } from '@/config/api';
import { cacheService, getLocationKey } from './cacheService';
import { connectivityService } from './connectivityService';
import { evaluateFreshness } from '@/utils/freshness';

export async function fetchFastAPIHazards(lat: number, lon: number): Promise<HazardAssessment> {
  if (lat === undefined || lon === undefined || isNaN(lat) || isNaN(lon)) {
    throw new Error('Coordinates (latitude, longitude) must be explicitly provided.');
  }

  const locationKey = getLocationKey(lat, lon);
  const endpoint = `${FASTAPI_BASE_URL}/api/hazards?latitude=${lat}&longitude=${lon}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 5000);

  // 1. Live Fetch
  try {
    const res = await fetch(endpoint, {
      cache: 'no-store',
      headers: {
        'Accept': 'application/json',
      },
      signal: controller.signal,
    });
    clearTimeout(timer);

    if (res.ok) {
      const data = await res.json() as HazardAssessment;
      const nowMs = Date.now();
      const freshness = evaluateFreshness(true, nowMs);

      const liveResult: HazardAssessment = {
        ...data,
        is_cached: false,
        cache_timestamp: nowMs,
        freshness,
      };

      await cacheService.set('hazards', locationKey, liveResult, 'Open-Meteo & Marine Hazard Engine');
      connectivityService.recordSuccess('hazard_service');

      return liveResult;
    }
  } catch (err) {
    clearTimeout(timer);
    console.warn(`[hazardService] FastAPI /api/hazards unreachable (${err}). Checking cache fallback.`);
    connectivityService.recordFailure('hazard_service', err);
  }

  // 2. Cache Fallback
  const cached = await cacheService.get<HazardAssessment>('hazards', locationKey);
  if (cached && cached.data) {
    const cachedData = cached.data;
    const freshness = evaluateFreshness(false, cached.timestamp);
    const timeStr = cached.formattedTime || 'earlier';

    return {
      ...cachedData,
      headline: `Previous Hazard Assessment (${timeStr}): ${cachedData.headline}`,
      is_cached: true,
      cache_timestamp: cached.timestamp,
      freshness,
      disclaimer: `Cached hazard telemetry recorded at ${timeStr}. Live marine conditions may differ. Reconnect before departure.`,
    };
  }

  // 3. Honest unavailable state when neither live nor cached data is available
  const unavailableFreshness = evaluateFreshness(false, null);
  return {
    coordinates: { latitude: lat, longitude: lon },
    overall_state: 'CAUTION',
    overall_code: 'caution',
    headline: 'Live hazard telemetry temporarily unavailable',
    active_conditions_count: 0,
    active_alerts: [],
    conditions: [
      {
        id: 'waves',
        name: 'Wave Conditions',
        icon: 'waves',
        value: '--',
        unit: 'm',
        status: 'Data unavailable',
        severity: 'unavailable',
        is_active: false,
        threshold: 'Normal: ≤1.8m | Elevated: 1.8–2.5m | High: >2.5m',
        explanation: 'Live wave telemetry unavailable offline.',
      },
      {
        id: 'wind',
        name: 'Wind & Gusts',
        icon: 'wind',
        value: '--',
        unit: 'kts',
        status: 'Data unavailable',
        severity: 'unavailable',
        is_active: false,
        threshold: 'Normal: ≤15 kts | Caution: 15–22 kts | High: >22 kts',
        explanation: 'Live wind telemetry unavailable offline.',
      },
      {
        id: 'precipitation',
        name: 'Precipitation & Visibility',
        icon: 'rain',
        value: '--',
        unit: 'mm',
        status: 'Data unavailable',
        severity: 'unavailable',
        is_active: false,
        threshold: 'Clear: ≤1.0mm | Elevated: 1.0–5.0mm | Heavy: >5.0mm',
        explanation: 'Live precipitation telemetry unavailable offline.',
      },
      {
        id: 'lightning',
        name: 'Lightning Activity',
        icon: 'lightning',
        value: 'Unavailable',
        unit: '',
        status: 'Data unavailable',
        severity: 'unavailable',
        is_active: false,
        threshold: 'IMD Radar Nowcast',
        explanation: 'Lightning detection telemetry offline. Verify local radar nowcasts before departure.',
      },
      {
        id: 'cyclone',
        name: 'Cyclone & Severe Storm',
        icon: 'cyclone',
        value: 'Unavailable',
        unit: '',
        status: 'Data unavailable',
        severity: 'unavailable',
        is_active: false,
        threshold: 'IMD / RSMC Bulletins',
        explanation: 'Regional cyclone bulletin feed disconnected. Verify official IMD warnings.',
      },
    ],
    disclaimer: 'ORCA provides AI-assisted decision support based on available environmental data. Always check official marine weather warnings and local authority advisories before venturing to sea.',
    is_cached: false,
    freshness: unavailableFreshness,
  };
}
