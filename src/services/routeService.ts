import type { RouteAnalysisResponse } from '../types/index';
import { FASTAPI_BASE_URL } from '../config/api';
import { cacheService } from './cacheService';
import { connectivityService } from './connectivityService';
import { evaluateFreshness, type FreshnessEvaluation } from '../utils/freshness';

export interface AnalyzeRoutesParams {
  origin_lat: number;
  origin_lon: number;
  destination_lat: number;
  destination_lon: number;
  destination_name?: string;
  time_window?: string;
  options?: { skipLive?: boolean };
}

export function getRouteCacheKey(
  origin_lat: number,
  origin_lon: number,
  destination_lat: number,
  destination_lon: number
): string {
  return `${origin_lat.toFixed(4)}_${origin_lon.toFixed(4)}_${destination_lat.toFixed(4)}_${destination_lon.toFixed(4)}`;
}

export async function fetchRouteAnalysis(
  params: AnalyzeRoutesParams,
  optionsArg?: { skipLive?: boolean }
): Promise<RouteAnalysisResponse> {
  const {
    origin_lat,
    origin_lon,
    destination_lat,
    destination_lon,
    destination_name,
    time_window,
  } = params;

  const skipLive = Boolean(params.options?.skipLive || optionsArg?.skipLive);

  if (
    origin_lat === undefined ||
    origin_lon === undefined ||
    destination_lat === undefined ||
    destination_lon === undefined ||
    isNaN(origin_lat) ||
    isNaN(origin_lon) ||
    isNaN(destination_lat) ||
    isNaN(destination_lon)
  ) {
    throw new Error('Both origin and destination coordinates are required for route analysis.');
  }

  const routeKey = getRouteCacheKey(origin_lat, origin_lon, destination_lat, destination_lon);
  const endpoint = `${FASTAPI_BASE_URL}/api/routes/analyze`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 6000);

  if (!skipLive) {
    // 1. Live Route Analysis Attempt
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({
          origin_lat,
          origin_lon,
          destination_lat,
          destination_lon,
          destination_name: destination_name || 'Designated Marine Target',
          time_window: time_window || 'tomorrow_morning',
        }),
        cache: 'no-store',
        signal: controller.signal,
      });
      clearTimeout(timer);

      if (res.ok) {
        const data = await res.json() as RouteAnalysisResponse;
        const nowMs = Date.now();
        const freshness = evaluateFreshness(true, nowMs);

        const liveResult: RouteAnalysisResponse = {
          ...data,
          is_cached: false,
          cache_timestamp: nowMs,
          freshness,
        };

        if (liveResult.available) {
          await cacheService.set('route', routeKey, liveResult, 'ORCA Route Intelligence Engine');
        }
        connectivityService.recordSuccess('route_service');

        return liveResult;
      }
    } catch (err) {
      clearTimeout(timer);
      console.warn(`[routeService] FastAPI /api/routes/analyze unreachable (${err}). Checking cache fallback.`);
      connectivityService.recordFailure('route_service', err);
    }
  }

  // 2. Verified Local Cache Fallback
  let cached = await cacheService.get<any>('route', routeKey);
  if (!cached) {
    cached = await cacheService.get<any>('route_intelligence', routeKey);
  }

  if (cached && cached.data) {
    const cachedData = cached.data;
    const freshness = evaluateFreshness(false, cached.timestamp);
    const timeStr = cached.formattedTime || 'earlier';

    return {
      available: true,
      origin: cachedData.origin || { latitude: origin_lat, longitude: origin_lon },
      destination: cachedData.destination || { name: destination_name, latitude: destination_lat, longitude: destination_lon, linear_distance_km: 0 },
      time_window: time_window || 'tomorrow_morning',
      routes: cachedData.routes || [],
      recommended_route_id: cachedData.recommended_route_id || '',
      recommendation_reason: `Previous Route Analysis (Cached from ${timeStr}): ${cachedData.recommendation_reason || ''} [Live marine conditions along corridors may have changed]`,
      data_sources: cachedData.data_sources || ['ORCA Cache'],
      disclaimer: `Cached route analysis recorded at ${timeStr}. Current marine conditions may differ. Reconnect before relying on this corridor.`,
      ...cachedData,
      is_cached: true,
      cache_timestamp: cached.timestamp,
      freshness,
    };
  }

  // 3. Unavailable State
  const unavailableFreshness = evaluateFreshness(false, null);
  return {
    available: false,
    origin: {
      latitude: origin_lat,
      longitude: origin_lon,
    },
    destination: {
      name: destination_name || 'Designated Marine Target',
      latitude: destination_lat,
      longitude: destination_lon,
      linear_distance_km: 0,
    },
    time_window: time_window || 'tomorrow_morning',
    routes: [],
    recommended_route_id: '',
    recommendation_reason: 'Live route analysis unavailable. Reconnect to calculate real-time environmental corridors.',
    data_sources: ['Open-Meteo', 'INCOIS GeoServer WFS', 'ORCA Decision Support Engine'],
    disclaimer: 'ORCA decision-support route analysis unavailable offline.',
    is_cached: false,
    freshness: unavailableFreshness,
  };
}

export const analyzeMarineRoutes = fetchRouteAnalysis;

/**
 * Retrieve verified Route Analysis with live-first caching and fallback.
 */
export async function getVerifiedRouteAnalysis(
  origin: { name?: string; latitude: number; longitude: number },
  destination: { name?: string; latitude: number; longitude: number },
  options?: { skipLive?: boolean; time_window?: string }
): Promise<{ data: any; freshness: FreshnessEvaluation }> {
  const res = await fetchRouteAnalysis({
    origin_lat: origin.latitude,
    origin_lon: origin.longitude,
    destination_lat: destination.latitude,
    destination_lon: destination.longitude,
    destination_name: destination.name,
    time_window: options?.time_window,
    options,
  });

  return {
    data: (res.available || res.is_cached) ? res : null,
    freshness: res.freshness || evaluateFreshness(false, null),
  };
}
