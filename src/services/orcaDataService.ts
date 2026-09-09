import { fetchWeatherForecast, DEFAULT_MUMBAI_COORDS } from './weatherService';
import { fetchMarineConditions, DEFAULT_MUMBAI_MARINE_COORDS } from './marineService';
import { marineConditions as fallbackMarineConditions } from '@/data/mockMarineData';
import { MarineCondition } from '@/types';
import { OrcaLiveMarineData } from '@/types/openMeteo';

/**
 * Convert degree angle (0-360) to 8-point compass bearing
 */
export function degreesToCompass(deg: number): string {
  const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
  const idx = Math.round(((deg % 360) + 360) % 360 / 45) % 8;
  return directions[idx];
}

/**
 * Fetch and assemble real-time weather and marine conditions from Open-Meteo
 * with automatic fallback to mock data on error.
 */
export async function getLiveOrcaMarineData(
  lat: number = DEFAULT_MUMBAI_COORDS.latitude,
  lon: number = DEFAULT_MUMBAI_COORDS.longitude
): Promise<OrcaLiveMarineData> {
  try {
    const [weatherRes, marineRes] = await Promise.all([
      fetchWeatherForecast(lat, lon),
      fetchMarineConditions(lat, lon),
    ]);

    const currentWeather = weatherRes.current;
    const currentMarine = marineRes.current;

    // Analyze tomorrow morning forecast (approx. index +24h to +30h or matching date/hour)
    let tomorrowMorningWave = currentMarine.wave_height ?? 1.2;
    let tomorrowMorningWind = currentWeather.wind_speed_10m ?? 12;
    let tomorrowMorningRain = 0;

    const hourlyTimes = weatherRes.hourly.time;
    if (hourlyTimes && hourlyTimes.length > 0) {
      // Find tomorrow's morning entries (06:00 to 11:00)
      const morningIndices: number[] = [];
      const now = new Date();
      const tomorrow = new Date(now);
      tomorrow.setDate(tomorrow.getDate() + 1);
      const tomorrowStr = tomorrow.toISOString().split('T')[0];

      hourlyTimes.forEach((tStr, i) => {
        if (tStr.startsWith(tomorrowStr)) {
          const hour = parseInt(tStr.split('T')[1].split(':')[0], 10);
          if (hour >= 6 && hour <= 11) {
            morningIndices.push(i);
          }
        }
      });

      if (morningIndices.length > 0) {
        const waves = morningIndices.map(i => marineRes.hourly.wave_height[i] ?? 1.0);
        const winds = morningIndices.map(i => weatherRes.hourly.wind_speed_10m[i] ?? 10);
        const rains = morningIndices.map(i => weatherRes.hourly.precipitation[i] ?? 0);

        tomorrowMorningWave = waves.reduce((a, b) => a + b, 0) / waves.length;
        tomorrowMorningWind = winds.reduce((a, b) => a + b, 0) / winds.length;
        tomorrowMorningRain = rains.reduce((a, b) => a + b, 0);
      }
    }

    const isTomorrowSafe = tomorrowMorningWave < 2.0 && tomorrowMorningWind < 18 && tomorrowMorningRain < 10;

    return {
      source: 'open-meteo',
      isLive: true,
      fetchedAt: new Date().toISOString(),
      coordinates: {
        lat,
        lon,
        locationName: 'Mumbai Coastal Sector (Arabian Sea)',
      },
      current: {
        temperature: currentWeather.temperature_2m,
        humidity: currentWeather.relative_humidity_2m,
        precipitation: currentWeather.precipitation,
        windSpeedKnots: currentWeather.wind_speed_10m,
        windDirectionDeg: currentWeather.wind_direction_10m,
        windDirectionCompass: degreesToCompass(currentWeather.wind_direction_10m),
        windGustsKnots: currentWeather.wind_gusts_10m,
        waveHeightMeters: currentMarine.wave_height ?? 1.1,
        waveDirectionDeg: currentMarine.wave_direction ?? 260,
        wavePeriodSeconds: currentMarine.wave_period ?? 6.5,
        swellWaveHeightMeters: currentMarine.swell_wave_height ?? 0.8,
        swellWavePeriodSeconds: currentMarine.swell_wave_period ?? 5.4,
        seaSurfaceTemperature: currentMarine.sea_surface_temperature ?? 28.5,
      },
      tomorrowMorning: {
        window: 'Tomorrow 06:00–11:00 IST',
        avgWaveHeight: parseFloat(tomorrowMorningWave.toFixed(1)),
        avgWindSpeed: parseFloat(tomorrowMorningWind.toFixed(1)),
        precipitationTotal: parseFloat(tomorrowMorningRain.toFixed(1)),
        isSafe: isTomorrowSafe,
        reason: isTomorrowSafe
          ? `Waves avg ${tomorrowMorningWave.toFixed(1)}m, wind ${tomorrowMorningWind.toFixed(1)} kts within safe thresholds.`
          : `Marginal conditions: swell or wind gusts approaching advisory limits.`,
      },
    };
  } catch (error) {
    console.warn('[ORCA Data Service] Open-Meteo live fetch failed, using fallback mock data:', error);
    return {
      source: 'mock-fallback',
      isLive: false,
      fetchedAt: new Date().toISOString(),
      coordinates: {
        lat,
        lon,
        locationName: 'Mumbai Coastal Sector (Fallback Mock)',
      },
      current: {
        temperature: 28.4,
        humidity: 78,
        precipitation: 0,
        windSpeedKnots: 14.0,
        windDirectionDeg: 225,
        windDirectionCompass: 'SW',
        windGustsKnots: 18.0,
        waveHeightMeters: 1.8,
        waveDirectionDeg: 235,
        wavePeriodSeconds: 6.8,
        swellWaveHeightMeters: 1.4,
        swellWavePeriodSeconds: 5.5,
        seaSurfaceTemperature: 28.4,
      },
      tomorrowMorning: {
        window: 'Tomorrow 05:00–11:00 IST',
        avgWaveHeight: 1.8,
        avgWindSpeed: 14.0,
        precipitationTotal: 0,
        isSafe: true,
        reason: 'Simulated baseline conditions suitable for mechanized operations.',
      },
    };
  }
}

/**
 * Transform live Open-Meteo data into the standard ORCA MarineCondition[] array
 * used by dashboard condition cards.
 */
export function mapToMarineConditions(liveData: OrcaLiveMarineData): MarineCondition[] {
  const isReal = liveData.source === 'open-meteo';
  const c = liveData.current;

  // Wave condition status & color
  let waveStatus = 'Acceptable';
  let waveColor: 'green' | 'amber' | 'red' = 'green';
  if (c.waveHeightMeters > 2.5) {
    waveStatus = 'Rough (Caution)';
    waveColor = 'red';
  } else if (c.waveHeightMeters > 1.8) {
    waveStatus = 'Moderate Swell';
    waveColor = 'amber';
  } else {
    waveStatus = 'Calm / Favorable';
    waveColor = 'green';
  }

  // Wind condition status & color
  let windStatus = 'Light / Calm';
  let windColor: 'green' | 'amber' | 'red' = 'green';
  if (c.windSpeedKnots > 22) {
    windStatus = 'High Wind (Warning)';
    windColor = 'red';
  } else if (c.windSpeedKnots > 15) {
    windStatus = 'Breezy / Moderate';
    windColor = 'amber';
  } else {
    windStatus = 'Gentle Breeze';
    windColor = 'green';
  }

  // Precipitation status & color
  let rainStatus = 'Clear Sky';
  let rainColor: 'green' | 'amber' | 'red' = 'green';
  if (c.precipitation > 5) {
    rainStatus = 'Heavy Showers';
    rainColor = 'red';
  } else if (c.precipitation > 0.5) {
    rainStatus = 'Light Showers';
    rainColor = 'amber';
  } else {
    rainStatus = 'Clear Sky';
    rainColor = 'green';
  }

  // SST status
  let sstStatus = 'PFZ Optimal';
  let sstColor: 'green' | 'amber' | 'blue' = 'green';
  if (c.seaSurfaceTemperature >= 27 && c.seaSurfaceTemperature <= 30.5) {
    sstStatus = 'PFZ Optimal';
    sstColor = 'green';
  } else if (c.seaSurfaceTemperature > 30.5) {
    sstStatus = 'Warm Surface';
    sstColor = 'amber';
  } else {
    sstStatus = 'Cool Coastal';
    sstColor = 'blue';
  }

  return [
    {
      id: 'sst',
      label: 'metric_sst',
      value: c.seaSurfaceTemperature.toFixed(1),
      unit: '°C',
      delta: isReal ? 'Live SST' : '0.2°C',
      deltaDirection: 'stable',
      status: sstStatus,
      statusColor: sstColor,
      icon: 'thermometer',
      detail: isReal ? 'Open-Meteo Marine' : 'Suitable range for pelagic activity',
      source: isReal ? 'Open-Meteo' : undefined,
    },
    {
      id: 'chlorophyll',
      label: 'metric_chlorophyll',
      value: '1.2',
      unit: 'mg/m³',
      status: 'Dense Biomass',
      statusColor: 'green',
      icon: 'leaf',
      detail: 'ISRO OCM-3 Proxy',
      source: undefined, // Mock proxy
    },
    {
      id: 'wind',
      label: 'metric_wind',
      value: c.windSpeedKnots.toFixed(1),
      unit: 'kts',
      status: windStatus,
      statusColor: windColor,
      icon: 'wind',
      detail: `${c.windDirectionCompass} • Gusts ${c.windGustsKnots.toFixed(0)} kt`,
      source: isReal ? 'Open-Meteo' : undefined,
    },
    {
      id: 'waves',
      label: 'metric_waves',
      value: c.waveHeightMeters.toFixed(1),
      unit: 'm',
      status: waveStatus,
      statusColor: waveColor,
      icon: 'waves',
      detail: `Period ${c.wavePeriodSeconds.toFixed(1)}s (Swell ${c.swellWaveHeightMeters.toFixed(1)}m)`,
      source: isReal ? 'Open-Meteo' : undefined,
    },
    {
      id: 'precipitation',
      label: 'metric_precipitation',
      value: c.precipitation.toFixed(1),
      unit: 'mm',
      status: rainStatus,
      statusColor: rainColor,
      icon: 'cloudRain',
      detail: `Humidity ${c.humidity}%`,
      source: isReal ? 'Open-Meteo' : undefined,
    },
    {
      id: 'tide',
      label: 'metric_tide',
      value: 'High',
      unit: '',
      status: 'Flood Tide',
      statusColor: 'blue',
      icon: 'arrowUpDown',
      detail: 'Hydrodynamic Table',
      source: undefined, // Mock proxy
    },
  ];
}
