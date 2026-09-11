import { RouteAnalysisResponse } from '@/types';
import { FASTAPI_BASE_URL } from '@/config/api';

export interface AnalyzeRoutesParams {
  origin_lat: number;
  origin_lon: number;
  destination_lat: number;
  destination_lon: number;
  destination_name?: string;
  time_window?: string;
}

export async function fetchRouteAnalysis(params: AnalyzeRoutesParams): Promise<RouteAnalysisResponse> {
  const { origin_lat, origin_lon, destination_lat, destination_lon, destination_name, time_window } = params;

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

  const endpoint = `${FASTAPI_BASE_URL}/api/routes/analyze`;

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
    });

    if (res.ok) {
      const data = await res.json();
      return data as RouteAnalysisResponse;
    } else {
      const errDetail = await res.text();
      console.warn(`[routeService] Route analysis server responded with ${res.status}:`, errDetail);
    }
  } catch (err) {
    console.warn(`[routeService] FastAPI /api/routes/analyze unreachable:`, err);
  }

  // Unavailable fallback response
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
    recommendation_reason: 'Route analysis telemetry service is temporarily unavailable. Please retry shortly.',
    data_sources: ['Open-Meteo', 'INCOIS GeoServer WFS', 'ORCA Decision Support Engine'],
    disclaimer:
      'ORCA provides decision-support recommendations based on available marine and weather data. Route suggestions are not authoritative navigation instructions and do not guarantee safety.',
  };
}

export const analyzeMarineRoutes = fetchRouteAnalysis;
