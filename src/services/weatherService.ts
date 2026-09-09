import { OpenMeteoWeatherResponse } from '@/types/openMeteo';

const OPEN_METEO_WEATHER_BASE_URL = 'https://api.open-meteo.com/v1/forecast';

export const DEFAULT_MUMBAI_COORDS = {
  latitude: 19.0760,
  longitude: 72.8777,
};

/**
 * Fetch real weather data from Open-Meteo Forecast API
 * No API key required.
 */
export async function fetchWeatherForecast(
  lat: number = DEFAULT_MUMBAI_COORDS.latitude,
  lon: number = DEFAULT_MUMBAI_COORDS.longitude
): Promise<OpenMeteoWeatherResponse> {
  const params = new URLSearchParams({
    latitude: lat.toString(),
    longitude: lon.toString(),
    current: [
      'temperature_2m',
      'relative_humidity_2m',
      'precipitation',
      'wind_speed_10m',
      'wind_direction_10m',
      'wind_gusts_10m',
    ].join(','),
    hourly: [
      'temperature_2m',
      'relative_humidity_2m',
      'precipitation',
      'wind_speed_10m',
      'wind_direction_10m',
      'wind_gusts_10m',
    ].join(','),
    wind_speed_unit: 'kn',
    timezone: 'Asia/Kolkata',
  });

  const response = await fetch(`${OPEN_METEO_WEATHER_BASE_URL}?${params.toString()}`, {
    // Cache for 10 minutes in Next.js
    next: { revalidate: 600 },
  });

  if (!response.ok) {
    throw new Error(`Open-Meteo Weather API responded with HTTP ${response.status}: ${response.statusText}`);
  }

  return response.json();
}
