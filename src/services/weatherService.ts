import { OpenMeteoWeatherResponse } from '@/types/openMeteo';
import { FASTAPI_BASE_URL } from '@/config/api';

const OPEN_METEO_WEATHER_BASE_URL = 'https://api.open-meteo.com/v1/forecast';


/**
 * Fetch weather from ORCA FastAPI backend (http://localhost:8000/api/weather)
 */
export async function fetchFastAPIWeather(lat: number, lon: number) {
  if (typeof lat !== 'number' || typeof lon !== 'number' || isNaN(lat) || isNaN(lon)) {
    throw new Error(`Invalid coordinates passed to fetchFastAPIWeather: lat=${lat}, lon=${lon}`);
  }
  const response = await fetch(`${FASTAPI_BASE_URL}/api/weather?latitude=${lat}&longitude=${lon}`, {
    cache: 'no-store',
  });
  if (!response.ok) {
    throw new Error(`FastAPI /api/weather returned HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * Fetch real weather data from Open-Meteo Forecast API
 * No API key required.
 */
export async function fetchWeatherForecast(lat: number, lon: number): Promise<OpenMeteoWeatherResponse> {
  if (typeof lat !== 'number' || typeof lon !== 'number' || isNaN(lat) || isNaN(lon)) {
    throw new Error(`Invalid coordinates passed to fetchWeatherForecast: lat=${lat}, lon=${lon}`);
  }
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
    cache: 'no-store',
  });

  if (!response.ok) {
    throw new Error(`Open-Meteo Weather API responded with HTTP ${response.status}: ${response.statusText}`);
  }

  return response.json();
}
