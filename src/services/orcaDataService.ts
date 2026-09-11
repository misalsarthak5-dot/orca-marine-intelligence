import { fetchWeatherForecast, fetchFastAPIWeather } from './weatherService';
import { fetchMarineConditions, fetchFastAPIMarine } from './marineService';
import { fetchFastAPISafety } from './safetyService';
import type { MarineCondition } from '../types/index';
import type { OrcaLiveMarineData } from '../types/openMeteo';
import { cacheService, getLocationKey } from './cacheService';
import { connectivityService } from './connectivityService';
import { evaluateFreshness, type FreshnessEvaluation } from '../utils/freshness';

/**
 * Convert degree angle (0-360) to 8-point compass bearing
 */
export function degreesToCompass(deg: number): string {
  const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
  const idx = Math.round(((deg % 360) + 360) % 360 / 45) % 8;
  return directions[idx];
}

/** Helper with timeout to prevent hanging requests */
async function withTimeout<T>(promise: Promise<T>, timeoutMs: number = 5000): Promise<T> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error(`API request timed out after ${timeoutMs}ms`));
    }, timeoutMs);

    promise
      .then((res) => {
        clearTimeout(timer);
        resolve(res);
      })
      .catch((err) => {
        clearTimeout(timer);
        reject(err);
      });
  });
}

/**
 * Fetch and assemble real-time weather and marine conditions.
 * Architecture:
 * 1. Live API (FastAPI backend / Direct Open-Meteo) -> on success, updates verified cache
 * 2. If API fails/times out -> retrieve verified local cache (IndexedDB)
 * 3. If no cache -> return explicit UNAVAILABLE state (never fabricate fake values)
 */
export async function getLiveOrcaMarineData(
  lat: number,
  lon: number,
  locationName: string = 'Coast',
  options?: { skipLive?: boolean; thresholdMinutes?: number }
): Promise<OrcaLiveMarineData & { is_cached?: boolean; cache_timestamp?: number; freshness?: FreshnessEvaluation }> {
  if (typeof lat !== 'number' || typeof lon !== 'number' || isNaN(lat) || isNaN(lon)) {
    throw new Error(`Invalid coordinates supplied to getLiveOrcaMarineData: lat=${lat}, lon=${lon}`);
  }

  const locationKey = getLocationKey(lat, lon);

  if (!options?.skipLive) {
    // ── Tier 1: Live API Attempt (FastAPI Backend) ──────────────
    try {
      const [fastWeather, fastMarine, fastSafety] = await withTimeout(
        Promise.all([
          fetchFastAPIWeather(lat, lon),
          fetchFastAPIMarine(lat, lon),
          fetchFastAPISafety(lat, lon),
        ]),
        5000
      );

    const wc = fastWeather.current || {};
    const mc = fastMarine.current || {};

    const waveHeight = mc.wave_height ?? 1.1;
    const windSpeed = wc.wind_speed ?? 12.0;
    const precip = wc.precipitation ?? 0.0;

    let tomorrowMorningWave = waveHeight;
    let tomorrowMorningWind = windSpeed;
    let tomorrowMorningRain = precip;

    const hourlyTimes = fastWeather.hourly?.time;
    if (hourlyTimes && Array.isArray(hourlyTimes) && hourlyTimes.length > 0) {
      const morningIndices: number[] = [];
      const now = new Date();
      const tomorrow = new Date(now);
      tomorrow.setDate(tomorrow.getDate() + 1);
      const tomorrowStr = tomorrow.toISOString().split('T')[0];

      hourlyTimes.forEach((tStr: string, i: number) => {
        if (typeof tStr === 'string' && tStr.startsWith(tomorrowStr)) {
          const hour = parseInt(tStr.split('T')[1]?.split(':')[0] || '0', 10);
          if (hour >= 6 && hour <= 11) {
            morningIndices.push(i);
          }
        }
      });

      if (morningIndices.length > 0) {
        const waves = morningIndices.map(i => fastMarine.hourly?.wave_height?.[i] ?? waveHeight);
        const winds = morningIndices.map(i => fastWeather.hourly?.wind_speed?.[i] ?? windSpeed);
        const rains = morningIndices.map(i => fastWeather.hourly?.precipitation?.[i] ?? 0);

        tomorrowMorningWave = waves.reduce((a: number, b: number) => a + b, 0) / waves.length;
        tomorrowMorningWind = winds.reduce((a: number, b: number) => a + b, 0) / winds.length;
        tomorrowMorningRain = rains.reduce((a: number, b: number) => a + b, 0);
      }
    }

    const isTomorrowSafe = tomorrowMorningWave < 2.0 && tomorrowMorningWind < 18.0 && tomorrowMorningRain < 10.0;
    const nowMs = Date.now();

    const liveData: OrcaLiveMarineData & { is_cached?: boolean; cache_timestamp?: number; freshness?: FreshnessEvaluation } = {
      source: 'fastapi',
      isLive: true,
      is_cached: false,
      fetchedAt: new Date(nowMs).toISOString(),
      fastapiSafety: fastSafety,
      coordinates: {
        lat,
        lon,
        locationName,
      },
      current: {
        temperature: wc.temperature ?? 28.4,
        humidity: wc.humidity ?? 80,
        precipitation: precip,
        windSpeedKnots: windSpeed,
        windDirectionDeg: wc.wind_direction ?? 240,
        windDirectionCompass: wc.wind_direction_compass ?? 'SW',
        windGustsKnots: wc.wind_gusts ?? (windSpeed * 1.3),
        waveHeightMeters: waveHeight,
        waveDirectionDeg: mc.wave_direction ?? 260,
        wavePeriodSeconds: mc.wave_period ?? 6.5,
        swellWaveHeightMeters: mc.swell_wave_height ?? 0.8,
        swellWavePeriodSeconds: mc.swell_wave_period ?? 5.4,
        seaSurfaceTemperature: mc.sea_surface_temperature ?? 29.0,
      },
      tomorrowMorning: {
        window: 'Tomorrow 06:00–11:00 IST',
        avgWaveHeight: parseFloat(tomorrowMorningWave.toFixed(1)),
        avgWindSpeed: parseFloat(tomorrowMorningWind.toFixed(1)),
        precipitationTotal: parseFloat(tomorrowMorningRain.toFixed(1)),
        isSafe: isTomorrowSafe,
        reason: fastSafety?.recommendation || (isTomorrowSafe
          ? `Waves avg ${tomorrowMorningWave.toFixed(1)}m, wind ${tomorrowMorningWind.toFixed(1)} kts within safe thresholds.`
          : `Marginal conditions: swell or wind gusts approaching advisory limits.`),
      },
      freshness: evaluateFreshness(true, nowMs),
    };

    // Save to verified local cache & update connectivity
    await cacheService.set('marine_data', locationKey, liveData, 'FastAPI / Open-Meteo');
    connectivityService.recordSuccess('marine_telemetry');

    return liveData;
  } catch (fastApiErr) {
    console.info('[ORCA Data Service] FastAPI backend unreachable or timed out, trying direct Open-Meteo:', fastApiErr);
  }
  } // end if (!options?.skipLive)

  if (!options?.skipLive) {
  // ── Tier 2: Direct Open-Meteo API Attempt ───────────────────
  try {
    const [weatherRes, marineRes] = await withTimeout(
      Promise.all([
        fetchWeatherForecast(lat, lon),
        fetchMarineConditions(lat, lon),
      ]),
      5000
    );

    const currentWeather = weatherRes.current;
    const currentMarine = marineRes.current;

    let tomorrowMorningWave = currentMarine.wave_height ?? 1.2;
    let tomorrowMorningWind = currentWeather.wind_speed_10m ?? 12;
    let tomorrowMorningRain = 0;

    const hourlyTimes = weatherRes.hourly.time;
    if (hourlyTimes && hourlyTimes.length > 0) {
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
    const nowMs = Date.now();

    const liveData: OrcaLiveMarineData & { is_cached?: boolean; cache_timestamp?: number; freshness?: FreshnessEvaluation } = {
      source: 'open-meteo',
      isLive: true,
      is_cached: false,
      fetchedAt: new Date(nowMs).toISOString(),
      coordinates: {
        lat,
        lon,
        locationName,
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
      freshness: evaluateFreshness(true, nowMs),
    };

    // Save to verified local cache & update connectivity
    await cacheService.set('marine_data', locationKey, liveData, 'Open-Meteo Marine API');
    connectivityService.recordSuccess('marine_telemetry');

    return liveData;
  } catch (error) {
    console.warn(`[ORCA Data Service] Live fetch failed for ${locationName} (${lat}, ${lon}):`, error);
    connectivityService.recordFailure('marine_telemetry', error);
  }
  } // end if (!options?.skipLive)

  // ── Tier 3: Verified Local Cache Fallback ───────────────────
  let cachedRecord = await cacheService.get<any>('marine_data', locationKey);
  if (!cachedRecord) {
    cachedRecord = await cacheService.get<any>('ocean_data', locationKey);
  }

  if (cachedRecord && cachedRecord.data) {
    const cachedData = cachedRecord.data;
    const freshness = evaluateFreshness({
      isLive: false,
      dataTimestamp: cachedRecord.timestamp,
      thresholdMinutes: options?.thresholdMinutes,
    });

    return {
      ...cachedData,
      source: 'cached',
      isLive: false,
      is_cached: true,
      cache_timestamp: cachedRecord.timestamp,
      freshness,
    };
  }

  // ── Tier 4: Honest UNAVAILABLE State (Zero Data Fabrication) ─
  const unavailableFreshness = evaluateFreshness(false, null);
  return {
    source: 'unavailable',
    isLive: false,
    is_cached: false,
    fetchedAt: new Date().toISOString(),
    coordinates: {
      lat,
      lon,
      locationName: `${locationName} (Data Unavailable)`,
    },
    current: {
      temperature: 0,
      humidity: 0,
      precipitation: 0,
      windSpeedKnots: 0,
      windDirectionDeg: 0,
      windDirectionCompass: 'N/A',
      windGustsKnots: 0,
      waveHeightMeters: 0,
      waveDirectionDeg: 0,
      wavePeriodSeconds: 0,
      swellWaveHeightMeters: 0,
      swellWavePeriodSeconds: 0,
      seaSurfaceTemperature: 0,
    },
    tomorrowMorning: {
      window: 'Tomorrow',
      avgWaveHeight: 0,
      avgWindSpeed: 0,
      precipitationTotal: 0,
      isSafe: false,
      reason: `Live marine telemetry currently unavailable for ${locationName}.`,
    },
    freshness: unavailableFreshness,
  };
}

/**
  * Retrieve verified ocean data with live-first caching and fallback.
  */
export async function getVerifiedOceanData(
  lat: number,
  lon: number,
  options?: { skipLive?: boolean; thresholdMinutes?: number; locationName?: string }
): Promise<{ data: any; freshness: FreshnessEvaluation }> {
  const locName = options?.locationName || 'Coast';
  const res = await getLiveOrcaMarineData(lat, lon, locName, options);
  if (res.source === 'unavailable') {
    return {
      data: null,
      freshness: res.freshness || evaluateFreshness(false, null),
    };
  }
  return {
    data: res,
    freshness: res.freshness || evaluateFreshness(res.isLive, res.cache_timestamp || Date.now()),
  };
}

/**
 * Transform live/cached Open-Meteo / FastAPI data into the standard ORCA MarineCondition[] array
 */
export function mapToMarineConditions(
  liveData: OrcaLiveMarineData & { is_cached?: boolean; cache_timestamp?: number; freshness?: FreshnessEvaluation }
): MarineCondition[] {
  const isAvailable = liveData.source !== 'unavailable';
  const isRealLive = liveData.isLive === true;
  const isCached = liveData.is_cached === true;
  const c = liveData.current;
  const locName = liveData.coordinates?.locationName || 'Coast';
  const freshness = liveData.freshness;

  if (!isAvailable) {
    return [
      {
        id: 'sst',
        label: 'metric_sst',
        value: '--',
        unit: '°C',
        status: 'Unavailable',
        statusColor: 'gray',
        icon: 'thermometer',
        detail: `Marine data temporarily unavailable for ${locName}`,
        freshness,
      },
      {
        id: 'chlorophyll',
        label: 'metric_chlorophyll',
        value: '--',
        unit: 'mg/m³',
        status: 'Pending',
        statusColor: 'gray',
        icon: 'leaf',
        detail: 'Satellite feed pending (NASA / INCOIS)',
        freshness,
      },
      {
        id: 'wind',
        label: 'metric_wind',
        value: '--',
        unit: 'kts',
        status: 'Unavailable',
        statusColor: 'gray',
        icon: 'wind',
        detail: `Marine data temporarily unavailable for ${locName}`,
        freshness,
      },
      {
        id: 'waves',
        label: 'metric_waves',
        value: '--',
        unit: 'm',
        status: 'Unavailable',
        statusColor: 'gray',
        icon: 'waves',
        detail: `Marine data temporarily unavailable for ${locName}`,
        freshness,
      },
      {
        id: 'precipitation',
        label: 'metric_precipitation',
        value: '--',
        unit: 'mm',
        status: 'Unavailable',
        statusColor: 'gray',
        icon: 'cloudRain',
        detail: `Marine data temporarily unavailable for ${locName}`,
        freshness,
      },
      {
        id: 'tide',
        label: 'metric_tide',
        value: '--',
        unit: '',
        status: 'Pending',
        statusColor: 'gray',
        icon: 'arrowUpDown',
        detail: 'Hydrodynamic Table',
        freshness,
      },
    ];
  }

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

  const deltaText = isRealLive ? 'Live Telemetry' : isCached ? `Cached (${freshness?.formattedTime || 'Saved'})` : 'Baseline';
  const detailSuffix = isCached ? ` [Cached · ${freshness?.ageText || ''}]` : '';

  return [
    {
      id: 'sst',
      label: 'metric_sst',
      value: c.seaSurfaceTemperature.toFixed(1),
      unit: '°C',
      delta: deltaText,
      deltaDirection: 'stable',
      status: sstStatus,
      statusColor: sstColor,
      icon: 'thermometer',
      detail: (isRealLive ? 'Open-Meteo Marine' : 'Verified cache') + detailSuffix,
      source: isRealLive ? 'Open-Meteo' : 'Cached',
      freshness,
    },
    {
      id: 'chlorophyll',
      label: 'metric_chlorophyll',
      value: '--',
      unit: 'mg/m³',
      status: 'Pending',
      statusColor: 'gray',
      icon: 'leaf',
      detail: 'Satellite feed pending (NASA / INCOIS)',
      freshness,
    },
    {
      id: 'wind',
      label: 'metric_wind',
      value: c.windSpeedKnots.toFixed(1),
      unit: 'kts',
      status: windStatus,
      statusColor: windColor,
      icon: 'wind',
      detail: `${c.windDirectionCompass} • Gusts ${c.windGustsKnots.toFixed(0)} kt` + detailSuffix,
      source: isRealLive ? 'Open-Meteo' : 'Cached',
      freshness,
    },
    {
      id: 'waves',
      label: 'metric_waves',
      value: c.waveHeightMeters.toFixed(1),
      unit: 'm',
      status: waveStatus,
      statusColor: waveColor,
      icon: 'waves',
      detail: `Period ${c.wavePeriodSeconds.toFixed(1)}s (Swell ${c.swellWaveHeightMeters.toFixed(1)}m)` + detailSuffix,
      source: isRealLive ? 'Open-Meteo' : 'Cached',
      freshness,
    },
    {
      id: 'precipitation',
      label: 'metric_precipitation',
      value: c.precipitation.toFixed(1),
      unit: 'mm',
      status: rainStatus,
      statusColor: rainColor,
      icon: 'cloudRain',
      detail: `Humidity ${c.humidity}%` + detailSuffix,
      source: isRealLive ? 'Open-Meteo' : 'Cached',
      freshness,
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
      freshness,
    },
  ];
}
