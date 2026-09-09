import { OpenMeteoMarineResponse } from '@/types/openMeteo';

const OPEN_METEO_MARINE_BASE_URL = 'https://marine-api.open-meteo.com/v1/marine';

export const DEFAULT_MUMBAI_MARINE_COORDS = {
  latitude: 19.0760,
  longitude: 72.8777,
};

/**
 * Fetch real marine and wave data from Open-Meteo Marine API
 * Uses cell_selection=sea for marine grid alignment.
 * No API key required.
 */
export async function fetchMarineConditions(
  lat: number = DEFAULT_MUMBAI_MARINE_COORDS.latitude,
  lon: number = DEFAULT_MUMBAI_MARINE_COORDS.longitude
): Promise<OpenMeteoMarineResponse> {
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
    // Cache for 10 minutes in Next.js
    next: { revalidate: 600 },
  });

  if (!response.ok) {
    throw new Error(`Open-Meteo Marine API responded with HTTP ${response.status}: ${response.statusText}`);
  }

  return response.json();
}
