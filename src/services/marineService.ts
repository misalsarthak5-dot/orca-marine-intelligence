import { OpenMeteoMarineResponse } from '@/types/openMeteo';
import { FASTAPI_BASE_URL } from '@/config/api';

const OPEN_METEO_MARINE_BASE_URL = 'https://marine-api.open-meteo.com/v1/marine';


/**
 * Fetch marine data from ORCA FastAPI backend (http://localhost:8000/api/marine)
 */
export async function fetchFastAPIMarine(lat: number, lon: number) {
  if (typeof lat !== 'number' || typeof lon !== 'number' || isNaN(lat) || isNaN(lon)) {
    throw new Error(`Invalid coordinates passed to fetchFastAPIMarine: lat=${lat}, lon=${lon}`);
  }
  const response = await fetch(`${FASTAPI_BASE_URL}/api/marine?latitude=${lat}&longitude=${lon}`, {
    cache: 'no-store',
  });
  if (!response.ok) {
    throw new Error(`FastAPI /api/marine returned HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * Validate whether a coordinate is in the marine/ocean area.
 * Returns is_marine: false if clicked on land.
 */
export async function validateMarinePoint(lat: number, lon: number): Promise<{ is_marine: boolean; wave_height: number | null }> {
  try {
    const response = await fetch(`${FASTAPI_BASE_URL}/api/validate-marine?latitude=${lat}&longitude=${lon}`);
    if (response.ok) {
      return await response.json();
    }
  } catch {
    // Fall back to direct Open-Meteo Marine API
  }

  try {
    const res = await fetch(
      `https://marine-api.open-meteo.com/v1/marine?latitude=${lat}&longitude=${lon}&cell_selection=sea&current=wave_height`
    );
    if (res.ok) {
      const data = await res.json();
      const waveH = data.current?.wave_height;
      return {
        is_marine: waveH !== null && waveH !== undefined,
        wave_height: waveH ?? null,
      };
    }
  } catch {
    // Return true if network check is unreachable to avoid blocking legitimate points
  }
  return { is_marine: true, wave_height: null };
}

/**
 * Fetch real marine and wave data from Open-Meteo Marine API
 * Uses cell_selection=sea for marine grid alignment.
 * No API key required.
 */
export async function fetchMarineConditions(lat: number, lon: number): Promise<OpenMeteoMarineResponse> {
  if (typeof lat !== 'number' || typeof lon !== 'number' || isNaN(lat) || isNaN(lon)) {
    throw new Error(`Invalid coordinates passed to fetchMarineConditions: lat=${lat}, lon=${lon}`);
  }
  const params = new URLSearchParams({
    latitude: lat.toString(),
    longitude: lon.toString(),
    cell_selection: 'sea',
    current: [
      'wave_height',
      'wave_direction',
      'wave_period',
      'swell_wave_height',
      'swell_wave_period',
      'sea_surface_temperature',
    ].join(','),
    hourly: [
      'wave_height',
      'wave_direction',
      'wave_period',
      'swell_wave_height',
      'swell_wave_period',
      'sea_surface_temperature',
    ].join(','),
    timezone: 'Asia/Kolkata',
  });

  const response = await fetch(`${OPEN_METEO_MARINE_BASE_URL}?${params.toString()}`, {
    cache: 'no-store',
  });

  if (!response.ok) {
    throw new Error(`Open-Meteo Marine API responded with HTTP ${response.status}: ${response.statusText}`);
  }

  return response.json();
}
