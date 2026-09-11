/**
 * ORCA — Chlorophyll-a Service (Frontend)
 *
 * Provides the architecture for real-time ocean-color chlorophyll-a data.
 *
 * Data Source (when connected): NASA Ocean Color / MODIS-Aqua / VIIRS-SNPP
 * Connection Status: NOT CONNECTED
 *
 * This service is intentionally designed to clearly return an unavailable state
 * until a real NASA Earthdata / INCOIS ocean-color API is integrated.
 * DO NOT fabricate chlorophyll values.
 */

import { FASTAPI_BASE_URL } from '@/config/api';

export interface ChlorophyllResult {
  available: boolean;
  value: number | null;
  unit: string;
  source: string;
  provider: string;
  status: string;
  message: string;
  coordinates?: { latitude: number; longitude: number };
  timestamp?: string;
}

/**
 * Fetch chlorophyll-a data for a given coordinate from the ORCA backend.
 *
 * When the satellite data source is not connected, the backend returns
 * `available: false` and a null value — this is the intended behavior.
 *
 * Returns a client-side unavailable result if the backend is unreachable.
 */
export async function fetchChlorophyll(lat: number, lon: number): Promise<ChlorophyllResult> {
  try {
    const response = await fetch(
      `${FASTAPI_BASE_URL}/api/chlorophyll?latitude=${lat}&longitude=${lon}`,
      { cache: 'no-store' }
    );
    if (response.ok) {
      return await response.json();
    }
  } catch {
    // Backend offline — return unavailable result
  }

  // Client-side fallback: always unavailable, never fabricated
  return {
    available: false,
    value: null,
    unit: 'mg/m³',
    source: 'NASA Ocean Color / MODIS-Aqua',
    provider: 'NASA Earthdata',
    status: 'not_connected',
    message: 'Chlorophyll-a satellite data source not connected. NASA Ocean Color / INCOIS integration pending.',
    coordinates: { latitude: lat, longitude: lon },
    timestamp: new Date().toISOString(),
  };
}
