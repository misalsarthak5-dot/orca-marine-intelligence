// ============================================================
// Open-Meteo API Types & Domain Models
// ============================================================

export interface OpenMeteoCurrentWeather {
  time: string;
  interval?: number;
  temperature_2m: number;
  relative_humidity_2m: number;
  precipitation: number;
  wind_speed_10m: number;
  wind_direction_10m: number;
  wind_gusts_10m: number;
}

export interface OpenMeteoHourlyWeather {
  time: string[];
  temperature_2m: number[];
  relative_humidity_2m: number[];
  precipitation: number[];
  wind_speed_10m: number[];
  wind_direction_10m: number[];
  wind_gusts_10m: number[];
}

export interface OpenMeteoWeatherResponse {
  latitude: number;
  longitude: number;
  generationtime_ms: number;
  utc_offset_seconds: number;
  timezone: string;
  elevation: number;
  current_units?: Record<string, string>;
  current: OpenMeteoCurrentWeather;
  hourly_units?: Record<string, string>;
  hourly: OpenMeteoHourlyWeather;
}

export interface OpenMeteoCurrentMarine {
  time: string;
  interval?: number;
  wave_height: number | null;
  wave_direction: number | null;
  wave_period: number | null;
  swell_wave_height: number | null;
  swell_wave_period: number | null;
  sea_surface_temperature: number | null;
}

export interface OpenMeteoHourlyMarine {
  time: string[];
  wave_height: (number | null)[];
  wave_direction: (number | null)[];
  wave_period: (number | null)[];
  swell_wave_height: (number | null)[];
  swell_wave_period: (number | null)[];
  sea_surface_temperature: (number | null)[];
}

export interface OpenMeteoMarineResponse {
  latitude: number;
  longitude: number;
  generationtime_ms: number;
  utc_offset_seconds: number;
  timezone: string;
  elevation: number;
  current_units?: Record<string, string>;
  current: OpenMeteoCurrentMarine;
  hourly_units?: Record<string, string>;
  hourly: OpenMeteoHourlyMarine;
}

/**
 * Combined live marine and weather dataset for ORCA
 */
export interface OrcaLiveMarineData {
  source: 'fastapi' | 'open-meteo' | 'mock-fallback';
  isLive: boolean;
  fetchedAt: string;
  fastapiSafety?: {
    risk_level: string;
    status: string;
    recommendation: string;
    factors: Array<{
      factor: string;
      label: string;
      value: string;
      risk: string;
      status: string;
      threshold: string;
    }>;
  };
  coordinates: {
    lat: number;
    lon: number;
    locationName: string;
  };
  current: {
    temperature: number;
    humidity: number;
    precipitation: number;
    windSpeedKnots: number;
    windDirectionDeg: number;
    windDirectionCompass: string;
    windGustsKnots: number;
    waveHeightMeters: number;
    waveDirectionDeg: number;
    wavePeriodSeconds: number;
    swellWaveHeightMeters: number;
    swellWavePeriodSeconds: number;
    seaSurfaceTemperature: number;
  };
  tomorrowMorning: {
    window: string;
    avgWaveHeight: number;
    avgWindSpeed: number;
    precipitationTotal: number;
    isSafe: boolean;
    reason: string;
  };
}
