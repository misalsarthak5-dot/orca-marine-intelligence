/**
 * ORCA — Geofencing & Restricted Maritime Zones Frontend Service
 * 
 * Fetches authoritative restriction zones, marine sanctuaries, and avoidance areas
 * from the ORCA backend. Gracefully handles unavailable states without fabricating data.
 */

import { FASTAPI_BASE_URL } from '@/config/api';
import { GeofenceResponse } from '@/types';

export async function fetchFastAPIGeofences(
  lat: number,
  lon: number,
  radiusKm: number = 250
): Promise<GeofenceResponse> {
  try {
    const res = await fetch(
      `${FASTAPI_BASE_URL}/api/geofences?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}&radius_km=${encodeURIComponent(radiusKm)}`,
      {
        headers: { 'Accept': 'application/json' },
        cache: 'no-store',
      }
    );

    if (!res.ok) {
      throw new Error(`Geofence service HTTP ${res.status}: ${res.statusText}`);
    }

    const data: GeofenceResponse = await res.json();
    return data;
  } catch (err) {
    console.warn('[Geofence Service] Unable to reach backend geofence endpoint:', err);
    return {
      status: 'UNAVAILABLE',
      source: null,
      query_coordinates: { latitude: lat, longitude: lon },
      search_radius_km: radiusKm,
      total_zones_found: 0,
      zones: [],
      message: 'Authoritative restriction-zone geometry is currently unavailable.',
      disclaimer: 'Verify official maritime notices and local authority guidance.',
    };
  }
}
