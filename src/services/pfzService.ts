/**
 * ORCA — Potential Fishing Zone (PFZ) Frontend Service
 * 
 * Communicates with ORCA FastAPI backend to retrieve verified official INCOIS
 * Potential Fishing Zones (PFZ), Landing Centre Advisories, and Satellite PFZ Lines.
 * 
 * Implements Live-First Caching & Graceful Low-Connectivity Fallback.
 * 
 * Provenance: Indian National Centre for Ocean Information Services (INCOIS)
 * Ministry of Earth Sciences, Government of India.
 */

import { FASTAPI_BASE_URL } from '../config/api';
import { cacheService, getLocationKey } from './cacheService';
import { connectivityService } from './connectivityService';
import { evaluateFreshness, type FreshnessEvaluation } from '../utils/freshness';

export interface PFZCoordinates {
  latitude: number;
  longitude: number;
}

export interface PFZAdvisory {
  id: string;
  landing_center: string;
  district?: string;
  sector?: string;
  lc_coordinates: PFZCoordinates;
  distance_from_query_km: number;
  advisory_distance_from_km?: number | null;
  advisory_distance_to_km?: number | null;
  direction?: string;
  bearing_degrees?: number | null;
  depth_from_m?: number | null;
  depth_to_m?: number | null;
  target_dms?: {
    latitude: string;
    longitude: string;
  };
  forecast_date?: string | null;
  validity_date?: string | null;
  validity_formatted?: string | null;
  is_currently_valid?: boolean;
  validity_status?: string;
  updated_date?: string | null;
  dataset_updated?: string;
  forecast_issue_id?: string | number | null;
  status: string;
  source: string;
}

export interface PFZLineFeature {
  uid: string;
  state_name?: string;
  category?: string;
  julian_day?: number | null;
  year?: number | null;
  length_km?: number | null;
  distance_km: number;
  geometry: {
    type: 'MultiLineString' | 'LineString';
    coordinates: number[][][] | number[][];
  };
  source: string;
}

export interface PFZAssessmentResponse {
  available: boolean;
  advisory_available?: boolean;
  advisory_message?: string;
  is_currently_valid: boolean;
  source: string;
  source_type: string;
  query_coordinates: PFZCoordinates;
  search_radius_km: number;
  nearest_advisory: PFZAdvisory | null;
  total_active_advisories_found: number;
  active_advisories: PFZAdvisory[];
  total_pfz_lines_found: number;
  pfz_lines: PFZLineFeature[];
  regional_pfz_lines?: PFZLineFeature[];
  total_regional_lines?: number;
  nationwide_pfz_lines?: PFZLineFeature[];
  total_nationwide_lines?: number;
  advisory_metadata: {
    authority: string;
    ministry: string;
    service_type: string;
    dataset_updated?: string;
    dataset_layer?: string;
    is_currently_valid?: boolean;
    localized_advisory_status?: string;
    regional_vectors_status?: string;
    validity_date?: string | null;
    validity_formatted?: string | null;
    validity_status?: string;
    pfz_lines_run?: string | null;
  };
  provenance_note: string;
  is_cached?: boolean;
  cache_timestamp?: number;
  freshness?: FreshnessEvaluation;
}

/**
 * Fetches real INCOIS Potential Fishing Zones (PFZ) assessment from the ORCA backend.
 * Uses Live-First Fallback with local IndexedDB cache.
 */
export async function fetchFastAPIPFZ(
  lat: number,
  lon: number,
  radiusKm: number = 250,
  options?: { skipLive?: boolean }
): Promise<PFZAssessmentResponse> {
  const locationKey = getLocationKey(lat, lon);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 6000);

  if (!options?.skipLive) {
    // 1. Live Fetch Attempt
    try {
      const res = await fetch(
        `${FASTAPI_BASE_URL}/api/pfz?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}&radius_km=${encodeURIComponent(radiusKm)}`,
        {
          headers: { 'Accept': 'application/json' },
          cache: 'no-store',
          signal: controller.signal,
        }
      );
      clearTimeout(timer);

      if (!res.ok) {
        throw new Error(`PFZ service HTTP ${res.status}: ${res.statusText}`);
      }

      const data: PFZAssessmentResponse = await res.json();
      const nowMs = Date.now();
      const freshness = evaluateFreshness(true, nowMs);

      const liveResult: PFZAssessmentResponse = {
        ...data,
        is_cached: false,
        cache_timestamp: nowMs,
        freshness,
      };

      // Save to verified local cache & notify connectivity
      if (liveResult.available) {
        await cacheService.set('pfz', locationKey, liveResult, 'INCOIS GeoServer WFS');
      }
      connectivityService.recordSuccess('pfz_service');

      return liveResult;
    } catch (err) {
      clearTimeout(timer);
      console.warn('[PFZ Service] Unable to reach backend PFZ endpoint, checking cache:', err);
      connectivityService.recordFailure('pfz_service', err);
    }
  }

  // 2. Cache Fallback
  let cached = await cacheService.get<any>('pfz', locationKey);
  if (!cached) {
    cached = await cacheService.get<any>('incois_pfz', locationKey);
  }

  if (cached && cached.data) {
    const cachedData = cached.data;
    const freshness = evaluateFreshness(false, cached.timestamp);
    const timeStr = cached.formattedTime || 'earlier';

    return {
      available: true,
      advisory_available: Boolean(cachedData.advisories_count || cachedData.advisories?.length),
      is_currently_valid: true,
      source: 'INCOIS GeoServer WFS (Cached)',
      source_type: 'Official PFZ Advisory',
      query_coordinates: { latitude: lat, longitude: lon },
      search_radius_km: radiusKm,
      nearest_advisory: cachedData.nearest_advisory || cachedData.advisories?.[0] || null,
      total_active_advisories_found: cachedData.total_active_advisories_found ?? cachedData.advisories_count ?? (cachedData.advisories?.length || 0),
      active_advisories: cachedData.active_advisories || cachedData.advisories || [],
      total_pfz_lines_found: cachedData.total_pfz_lines_found ?? cachedData.regional_features_count ?? 0,
      pfz_lines: cachedData.pfz_lines || cachedData.regional_features || [],
      regional_pfz_lines: cachedData.regional_pfz_lines || cachedData.regional_features || [],
      total_regional_lines: cachedData.total_regional_lines ?? cachedData.regional_features_count ?? 0,
      advisory_metadata: cachedData.advisory_metadata || {
        authority: 'INCOIS',
        ministry: 'MoES',
        service_type: 'PFZ Advisory',
        validity_status: 'CACHED',
      },
      ...cachedData,
      is_cached: true,
      cache_timestamp: cached.timestamp,
      freshness,
      advisory_message: `CACHED INCOIS PFZ: Showing verified advisory from ${timeStr}. Live data may differ; reconnect to refresh.`,
      provenance_note: `Cached from official INCOIS GeoServer WFS records at ${timeStr}.`,
    };
  }

  // 3. Unavailable State
  const unavailableFreshness = evaluateFreshness(false, null);
  return {
    available: false,
    advisory_available: false,
    advisory_message: 'INCOIS PFZ data currently unavailable offline.',
    is_currently_valid: false,
    source: 'INCOIS',
    source_type: 'Official PFZ Advisory',
    query_coordinates: { latitude: lat, longitude: lon },
    search_radius_km: radiusKm,
    nearest_advisory: null,
    total_active_advisories_found: 0,
    active_advisories: [],
    total_pfz_lines_found: 0,
    pfz_lines: [],
    nationwide_pfz_lines: [],
    total_nationwide_lines: 0,
    advisory_metadata: {
      authority: 'Indian National Centre for Ocean Information Services (INCOIS)',
      ministry: 'Ministry of Earth Sciences, Govt. of India',
      service_type: 'Multi-Mission Satellite Ocean Color & SST Thermal Fronts',
      dataset_updated: 'Unavailable',
      is_currently_valid: false,
      validity_formatted: 'Connection Unavailable',
      validity_status: 'UNAVAILABLE',
    },
    provenance_note: 'PFZ service currently unreachable and no verified cache on record. Connect to internet to retrieve official INCOIS bulletins.',
    is_cached: false,
    freshness: unavailableFreshness,
  };
}

/**
 * Retrieve verified PFZ data with live-first caching and fallback.
 */
export async function getVerifiedPFZData(
  lat: number,
  lon: number,
  options?: { skipLive?: boolean; radiusKm?: number }
): Promise<{ data: any; freshness: FreshnessEvaluation }> {
  const res = await fetchFastAPIPFZ(lat, lon, options?.radiusKm || 250, options);
  return {
    data: (res.available || res.is_cached) ? res : null,
    freshness: res.freshness || evaluateFreshness(false, null),
  };
}
