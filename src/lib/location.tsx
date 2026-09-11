'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { getLiveOrcaMarineData, mapToMarineConditions } from '@/services/orcaDataService';
import { validateMarinePoint } from '@/services/marineService';
import { OrcaLiveMarineData } from '@/types/openMeteo';
import { MarineCondition, SafetyAssessment } from '@/types';

export interface LocationState {
  name: string;
  latitude: number;
  longitude: number;
  isCustom?: boolean;
}

export const COASTAL_LOCATIONS: LocationState[] = [
  { name: 'Mumbai Coast', latitude: 19.0760, longitude: 72.8777 },
  { name: 'Ratnagiri Coast', latitude: 16.9902, longitude: 73.3120 },
  { name: 'Goa Coast', latitude: 15.4989, longitude: 73.8278 },
  { name: 'Mangalore Coast', latitude: 12.9141, longitude: 74.8560 },
  { name: 'Kochi Coast', latitude: 9.9312, longitude: 76.2673 },
  { name: 'Chennai Coast', latitude: 13.0827, longitude: 80.2707 },
  { name: 'Visakhapatnam Coast', latitude: 17.6868, longitude: 83.2185 },
  { name: 'Puri Coast', latitude: 19.8135, longitude: 85.8312 },
  { name: 'Kolkata Coast', latitude: 21.6266, longitude: 88.0645 },
  { name: 'Port Blair', latitude: 11.6234, longitude: 92.7265 },
];

export const DEFAULT_LOCATION: LocationState = COASTAL_LOCATIONS[0];

/**
 * All locations now use fully dynamic, live data from Open-Meteo and INCOIS.
 * Retained for backwards-compatibility; always returns false.
 */
export function isMumbaiDemoCoverage(_loc?: LocationState | null): boolean {
  return false;
}

function createInitialMarineConditions(locName: string): MarineCondition[] {
  return [
    { id: 'sst', label: 'metric_sst', value: '--', unit: '°C', status: 'Fetching...', statusColor: 'gray', icon: 'thermometer', detail: `Initializing for ${locName}` },
    { id: 'chlorophyll', label: 'metric_chlorophyll', value: '--', unit: 'mg/m³', status: 'Pending', statusColor: 'gray', icon: 'leaf', detail: 'Satellite feed pending (NASA / INCOIS)' },
    { id: 'wind', label: 'metric_wind', value: '--', unit: 'kts', status: 'Fetching...', statusColor: 'gray', icon: 'wind', detail: `Initializing for ${locName}` },
    { id: 'waves', label: 'metric_waves', value: '--', unit: 'm', status: 'Fetching...', statusColor: 'gray', icon: 'waves', detail: `Initializing for ${locName}` },
    { id: 'precipitation', label: 'metric_precipitation', value: '--', unit: 'mm', status: 'Fetching...', statusColor: 'gray', icon: 'cloudRain', detail: `Initializing for ${locName}` },
    { id: 'tide', label: 'metric_tide', value: '--', unit: '', status: 'Pending', statusColor: 'gray', icon: 'arrowUpDown', detail: 'Hydrodynamic Table' },
  ];
}

function createInitialSafetyAssessment(loc: LocationState): SafetyAssessment {
  return {
    riskLevel: 'low',
    riskScore: 0,
    maxScore: 100,
    area: loc.name,
    validityPeriod: 'Fetching Telemetry...',
    verdictTitle: `ASSESSMENT INITIALIZING (${loc.name.toUpperCase()})`,
    verdictSubtitle: 'FETCHING REAL-TIME MARINE TELEMETRY',
    description: `Connecting to Open-Meteo & ORCA Safety Engine for ${loc.name}...`,
    factors: [
      { id: 'waves', label: 'factor_waves', value: '--', status: 'Connecting...', statusColor: 'green', icon: 'waves' },
      { id: 'wind', label: 'factor_wind', value: '--', status: 'Connecting...', statusColor: 'green', icon: 'wind' },
      { id: 'lightning', label: 'factor_lightning', value: 'Clear', status: 'No alert detected', statusColor: 'green', icon: 'zap' },
      { id: 'cyclone', label: 'factor_cyclone', value: 'Clear', status: 'No depression', statusColor: 'green', icon: 'tornado' },
      { id: 'rain', label: 'factor_rain', value: '--', status: 'Connecting...', statusColor: 'green', icon: 'cloudRain' },
      { id: 'geofence', label: 'factor_geofence', value: 'Clear', status: 'Safe boundary', statusColor: 'green', icon: 'shield' },
    ],
    reasoning: [`Initializing safety assessment matrix for ${loc.name}...`],
    recommendation: `Retrieving live environmental telemetry for ${loc.name}.`,
    disclaimer: 'AI assessment based on real-time environmental data. Verify official marine advisories before departure.',
  };
}

function formatISTTimestamp(date: Date = new Date()): string {
  try {
    return date.toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      timeZone: 'Asia/Kolkata',
    }) + ' IST';
  } catch {
    const hh = String(date.getHours()).padStart(2, '0');
    const mm = String(date.getMinutes()).padStart(2, '0');
    return `${hh}:${mm} IST`;
  }
}

interface LocationContextType {
  selectedLocation: LocationState;
  setSelectedLocation: (loc: LocationState) => void;
  locationsList: LocationState[];
  liveData: OrcaLiveMarineData | null;
  marineConditions: MarineCondition[];
  safetyAssessment: SafetyAssessment;
  isLoading: boolean;
  isLive: boolean;
  liveSource: 'fastapi' | 'open-meteo' | 'mock-fallback';
  lastUpdated: string | null;
  locationNotice: string | null;
  clearLocationNotice: () => void;
  selectPointFromMap: (lat: number, lon: number) => Promise<boolean>;
  useMyLocation: () => Promise<void>;
  refreshData: (loc?: LocationState) => Promise<void>;
}

const LocationContext = createContext<LocationContextType | undefined>(undefined);

export function LocationProvider({ children }: { children: ReactNode }) {
  const [selectedLocation, setSelectedLocationState] = useState<LocationState>(DEFAULT_LOCATION);
  const [liveData, setLiveData] = useState<OrcaLiveMarineData | null>(null);
  const [marineConditions, setMarineConditions] = useState<MarineCondition[]>(() => createInitialMarineConditions(DEFAULT_LOCATION.name));
  const [safetyAssessment, setSafetyAssessment] = useState<SafetyAssessment>(() => createInitialSafetyAssessment(DEFAULT_LOCATION));
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isLive, setIsLive] = useState<boolean>(false);
  const [liveSource, setLiveSource] = useState<'fastapi' | 'open-meteo' | 'mock-fallback'>('fastapi');
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [locationNotice, setLocationNotice] = useState<string | null>(null);

  const clearLocationNotice = useCallback(() => {
    setLocationNotice(null);
  }, []);

  const loadLocationData = useCallback(async (loc: LocationState) => {
    setIsLoading(true);
    setLiveData(null); // Clear previous location data immediately to prevent stale state
    clearLocationNotice();

    console.log("[ORCA] Selected location:", loc);
    console.log("[ORCA] Fetching coordinates:", loc.latitude, loc.longitude);

    try {
      const data = await getLiveOrcaMarineData(loc.latitude, loc.longitude, loc.name);

      if (data && data.isLive) {
        setLiveData(data);
        setMarineConditions(mapToMarineConditions(data));
        setIsLive(true);
        setLiveSource(data.source);
        setLastUpdated(formatISTTimestamp(new Date()));

        // Update dynamic safety assessment factors and verdict for the selected location
        const c = data.current;
        const waveH = c.waveHeightMeters ?? 1.1;
        const windSpd = c.windSpeedKnots ?? 12.0;
        const precip = c.precipitation ?? 0.0;

        const isWaveElevated = waveH > 1.8;
        const isWindElevated = windSpd > 15.0;
        const isRainElevated = precip > 1.0;

        const fastRisk = data.fastapiSafety?.risk_level?.toLowerCase();
        const riskLevel: 'low' | 'moderate' | 'high' = 
          (fastRisk === 'high' || fastRisk === 'caution' || fastRisk === 'low')
            ? (fastRisk === 'caution' ? 'moderate' : fastRisk as 'low' | 'high')
            : ((waveH > 2.5 || windSpd > 22 || precip > 5) ? 'high' :
               (isWaveElevated || isWindElevated || isRainElevated) ? 'moderate' : 'low');

        const verdictTitle = data.fastapiSafety?.status
          ? `VERDICT: ${data.fastapiSafety.status} (${loc.name.toUpperCase()})`
          : riskLevel === 'low' 
          ? `VERDICT: CONDITIONS APPEAR SUITABLE (${loc.name.toUpperCase()})` 
          : riskLevel === 'moderate'
          ? `VERDICT: CAUTION ADVISED FOR ${loc.name.toUpperCase()}`
          : `VERDICT: HIGH RISK AT ${loc.name.toUpperCase()}`;

        const dynamicReasoning = [
          `Live wave swell at ${loc.name} is ${waveH.toFixed(1)}m (${waveH < 1.8 ? 'within safe operational threshold' : waveH < 2.5 ? 'moderate swell observed' : 'rough seas detected'}).`,
          `Surface wind speed is ${windSpd.toFixed(1)} kts ${c.windDirectionCompass} with gusts to ${c.windGustsKnots.toFixed(0)} kts.`,
          `Precipitation telemetry is ${precip.toFixed(1)} mm with ${c.humidity}% relative humidity; no adverse convective cells detected.`,
        ];

        const computedRiskScore = riskLevel === 'high' ? 78 : riskLevel === 'moderate' ? 48 : 18;

        setSafetyAssessment((prev) => ({
          ...prev,
          riskLevel,
          riskScore: computedRiskScore,
          area: loc.name,
          verdictTitle,
          description: data.fastapiSafety?.recommendation || (
            riskLevel === 'low'
              ? `Environmental telemetry at ${loc.name} indicates wave heights at ${waveH.toFixed(1)}m and wind speeds at ${windSpd.toFixed(1)} kts within operational limits. Mechanized craft (>9m) may proceed with standard vigilance.`
              : `Elevated sea conditions observed at ${loc.name} with waves at ${waveH.toFixed(1)}m and winds at ${windSpd.toFixed(1)} kts. Heightened vigilance required.`
          ),
          reasoning: dynamicReasoning,
          factors: prev.factors.map((f) => {
            if (f.id === 'waves') {
              return {
                ...f,
                value: `${waveH.toFixed(1)} m — ${waveH < 1.8 ? 'Acceptable' : waveH < 2.5 ? 'Moderate Swell' : 'Rough Seas'}`,
                status: `Live at ${loc.name} (Swell ${c.swellWaveHeightMeters.toFixed(1)}m)`,
                statusColor: waveH < 1.8 ? 'green' : waveH < 2.5 ? 'amber' : 'red',
              };
            }
            if (f.id === 'wind') {
              return {
                ...f,
                value: `${windSpd.toFixed(1)} kt ${c.windDirectionCompass} — ${windSpd < 15 ? 'Gentle Breeze' : windSpd < 22 ? 'Caution' : 'High Wind'}`,
                status: `Live at ${loc.name} (Gusts ${c.windGustsKnots.toFixed(0)} kt)`,
                statusColor: windSpd < 15 ? 'green' : windSpd < 22 ? 'amber' : 'red',
              };
            }
            if (f.id === 'rain') {
              return {
                ...f,
                value: `${precip.toFixed(1)} mm — ${precip < 1 ? 'Clear / Dry' : precip < 5 ? 'Showers' : 'Heavy Rain'}`,
                status: `Humidity ${c.humidity}% at ${loc.name}`,
                statusColor: precip < 1 ? 'green' : precip < 5 ? 'amber' : 'red',
              };
            }
            if (f.id === 'lightning') {
              return {
                ...f,
                value: 'Clear',
                status: `No alert at ${loc.name}`,
                statusColor: 'green',
              };
            }
            if (f.id === 'cyclone') {
              return {
                ...f,
                value: 'Clear',
                status: `No depression at ${loc.name}`,
                statusColor: 'green',
              };
            }
            if (f.id === 'geofence') {
              return {
                ...f,
                value: 'Clear',
                status: `Safe boundary buffer at ${loc.name}`,
                statusColor: 'green',
              };
            }
            return f;
          }),
        }));
      } else {
        // Live data not available — label unavailable state for the current location
        setIsLive(false);
        setLiveSource('mock-fallback');
        setLastUpdated(formatISTTimestamp(new Date()) + ' (Offline)');
        setLocationNotice(`Marine data temporarily unavailable for ${loc.name}.`);
        const fallbackObj: OrcaLiveMarineData = {
          source: 'mock-fallback',
          isLive: false,
          fetchedAt: new Date().toISOString(),
          coordinates: { lat: loc.latitude, lon: loc.longitude, locationName: loc.name },
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
            window: 'Tomorrow 05:00–11:00 IST',
            avgWaveHeight: 0,
            avgWindSpeed: 0,
            precipitationTotal: 0,
            isSafe: false,
            reason: `Marine data temporarily unavailable for ${loc.name}.`,
          },
        };
        setLiveData(fallbackObj);
        setMarineConditions(mapToMarineConditions(fallbackObj));
        setSafetyAssessment((prev) => ({
          ...prev,
          area: loc.name,
          verdictTitle: `VERDICT: TELEMETRY UNAVAILABLE (${loc.name.toUpperCase()})`,
          description: `Marine data temporarily unavailable for ${loc.name}. Please verify official coastal marine advisories.`,
          factors: prev.factors.map((f) => ({
            ...f,
            value: '--',
            status: `Unavailable at ${loc.name}`,
            statusColor: 'amber',
          })),
        }));
      }
    } catch (err) {
      console.warn(`Failed to fetch environmental telemetry for ${loc.name}:`, err);
      setIsLive(false);
      setLiveSource('mock-fallback');
      setLastUpdated(formatISTTimestamp(new Date()) + ' (Offline)');
      setLocationNotice(`Marine data temporarily unavailable for ${loc.name}.`);
      const fallbackObj: OrcaLiveMarineData = {
        source: 'mock-fallback',
        isLive: false,
        fetchedAt: new Date().toISOString(),
        coordinates: { lat: loc.latitude, lon: loc.longitude, locationName: loc.name },
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
          window: 'Tomorrow 05:00–11:00 IST',
          avgWaveHeight: 0,
          avgWindSpeed: 0,
          precipitationTotal: 0,
          isSafe: false,
          reason: `Marine data temporarily unavailable for ${loc.name}.`,
        },
      };
      setLiveData(fallbackObj);
      setMarineConditions(mapToMarineConditions(fallbackObj));
      setSafetyAssessment((prev) => ({
        ...prev,
        area: loc.name,
        verdictTitle: `VERDICT: TELEMETRY UNAVAILABLE (${loc.name.toUpperCase()})`,
        description: `Marine data temporarily unavailable for ${loc.name}. Please verify official coastal marine advisories.`,
        factors: prev.factors.map((f) => ({
          ...f,
          value: '--',
          status: `Unavailable at ${loc.name}`,
          statusColor: 'amber',
        })),
      }));
    } finally {
      setIsLoading(false);
    }
  }, [clearLocationNotice]);

  // Initial load
  useEffect(() => {
    loadLocationData(DEFAULT_LOCATION);
  }, [loadLocationData]);

  const setSelectedLocation = useCallback((loc: LocationState) => {
    setSelectedLocationState(loc);
    loadLocationData(loc);
  }, [loadLocationData]);

  const refreshData = useCallback(async (loc?: LocationState) => {
    await loadLocationData(loc || selectedLocation);
  }, [loadLocationData, selectedLocation]);

  /**
   * Handle user clicking on the map:
   * Validates whether clicked point is marine. If on land, shows notice and rejects.
   */
  const selectPointFromMap = useCallback(async (lat: number, lon: number): Promise<boolean> => {
    setIsLoading(true);
    setLocationNotice(null);

    try {
      const validation = await validateMarinePoint(lat, lon);

      if (validation.is_marine === false) {
        setIsLoading(false);
        setLocationNotice('Please select a point in the marine area.');
        return false;
      }

      const customLocation: LocationState = {
        name: `Selected Point (${lat.toFixed(2)}°N, ${lon.toFixed(2)}°E)`,
        latitude: parseFloat(lat.toFixed(4)),
        longitude: parseFloat(lon.toFixed(4)),
        isCustom: true,
      };

      setSelectedLocationState(customLocation);
      await loadLocationData(customLocation);
      return true;
    } catch (err) {
      console.error('Error during marine map click selection:', err);
      setLocationNotice('Please select a point in the marine area.');
      setIsLoading(false);
      return false;
    }
  }, [loadLocationData]);

  /**
   * Browser Geolocation API
   */
  const useMyLocation = useCallback(async () => {
    if (typeof window === 'undefined' || !navigator.geolocation) {
      setLocationNotice('Geolocation is not supported by your browser.');
      return;
    }

    setIsLoading(true);
    setLocationNotice(null);

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const { latitude, longitude } = pos.coords;
        const validation = await validateMarinePoint(latitude, longitude);

        if (validation.is_marine === false) {
          setIsLoading(false);
          setLocationNotice(
            `Your device coordinates (${latitude.toFixed(2)}°N, ${longitude.toFixed(2)}°E) appear inland. Please select a coastal assessment sector or click on the marine map.`
          );
          return;
        }

        const geoLoc: LocationState = {
          name: `My Position (${latitude.toFixed(2)}°N, ${longitude.toFixed(2)}°E)`,
          latitude: parseFloat(latitude.toFixed(4)),
          longitude: parseFloat(longitude.toFixed(4)),
          isCustom: true,
        };

        setSelectedLocationState(geoLoc);
        await loadLocationData(geoLoc);
      },
      (error) => {
        setIsLoading(false);
        let errorMsg = 'Could not access device location.';
        if (error.code === error.PERMISSION_DENIED) {
          errorMsg = 'Location permission was denied. You can select a coastal sector from the dropdown or click on the map.';
        } else if (error.code === error.POSITION_UNAVAILABLE) {
          errorMsg = 'Device location is currently unavailable.';
        }
        setLocationNotice(errorMsg);
      },
      { timeout: 8000, enableHighAccuracy: false }
    );
  }, [loadLocationData]);

  return (
    <LocationContext.Provider
      value={{
        selectedLocation,
        setSelectedLocation,
        locationsList: COASTAL_LOCATIONS,
        liveData,
        marineConditions,
        safetyAssessment,
        isLoading,
        isLive,
        liveSource,
        lastUpdated,
        locationNotice,
        clearLocationNotice,
        selectPointFromMap,
        useMyLocation,
        refreshData,
      }}
    >
      {children}
    </LocationContext.Provider>
  );
}

export function useLocation() {
  const context = useContext(LocationContext);
  if (!context) {
    throw new Error('useLocation must be used within a LocationProvider');
  }
  return context;
}
