'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { getLiveOrcaMarineData, mapToMarineConditions } from '@/services/orcaDataService';
import { validateMarinePoint } from '@/services/marineService';
import { getVerifiedSafetyAssessment } from '@/services/safetyService';
import { OrcaLiveMarineData } from '@/types/openMeteo';
import { MarineCondition, SafetyAssessment } from '@/types';
import { cacheService } from '@/services/cacheService';
import { connectivityService } from '@/services/connectivityService';
import { formatTimestampIST } from '@/utils/freshness';

export interface LocationState {
  id?: string;
  name: string;
  latitude: number;
  longitude: number;
  displayLabel?: string;
  harborRef?: string;
  mapZoom?: number;
  region?: string;
  isCustom?: boolean;
}

export const COASTAL_LOCATIONS: LocationState[] = [
  {
    id: 'mumbai',
    name: 'Mumbai Coast',
    displayLabel: 'Mumbai Coast',
    latitude: 19.08,
    longitude: 72.88,
    harborRef: 'Sassoon Docks / New Ferry Wharf',
    mapZoom: 10,
    region: 'West Coast (Arabian Sea)',
  },
  {
    id: 'ratnagiri',
    name: 'Ratnagiri Coast',
    displayLabel: 'Ratnagiri Coast',
    latitude: 16.99,
    longitude: 73.31,
    harborRef: 'Mirkarwada Fishing Harbour',
    mapZoom: 10,
    region: 'West Coast (Arabian Sea)',
  },
  {
    id: 'goa',
    name: 'Goa Coast',
    displayLabel: 'Goa Coast',
    latitude: 15.50,
    longitude: 73.83,
    harborRef: 'Malim / Panaji / Betul',
    mapZoom: 10,
    region: 'West Coast (Arabian Sea)',
  },
  {
    id: 'mangalore',
    name: 'Mangalore Coast',
    displayLabel: 'Mangalore Coast',
    latitude: 12.91,
    longitude: 74.86,
    harborRef: 'Old Port (Bunder) Fishing Harbour',
    mapZoom: 10,
    region: 'West Coast (Arabian Sea)',
  },
  {
    id: 'kochi',
    name: 'Kochi Coast',
    displayLabel: 'Kochi Coast',
    latitude: 9.93,
    longitude: 76.27,
    harborRef: 'Cochin Fisheries Harbour (Thoppumpady)',
    mapZoom: 10,
    region: 'South-West Coast (Arabian Sea)',
  },
  {
    id: 'chennai',
    name: 'Chennai Coast',
    displayLabel: 'Chennai Coast',
    latitude: 13.08,
    longitude: 80.27,
    harborRef: 'Kasimedu (Chennai) Fishing Harbour',
    mapZoom: 10,
    region: 'East Coast (Bay of Bengal)',
  },
  {
    id: 'visakhapatnam',
    name: 'Visakhapatnam Coast',
    displayLabel: 'Visakhapatnam Coast',
    latitude: 17.69,
    longitude: 83.22,
    harborRef: 'Visakhapatnam Fishing Harbour',
    mapZoom: 10,
    region: 'East Coast (Bay of Bengal)',
  },
  {
    id: 'puri',
    name: 'Puri Coast',
    displayLabel: 'Puri Coast',
    latitude: 19.81,
    longitude: 85.83,
    harborRef: 'Puri Fish Landing Centre / Penthakata',
    mapZoom: 10,
    region: 'East Coast (Bay of Bengal)',
  },
  {
    id: 'kolkata',
    name: 'Kolkata Coast',
    displayLabel: 'Kolkata Coast',
    latitude: 21.63,
    longitude: 88.06,
    harborRef: 'Digha Mohana / Fraserganj Coastal Sector',
    mapZoom: 10,
    region: 'East Coast (Bay of Bengal)',
  },
  {
    id: 'port_blair',
    name: 'Port Blair',
    displayLabel: 'Port Blair (Andaman)',
    latitude: 11.62,
    longitude: 92.73,
    harborRef: 'Junglighat / Phoenix Bay Fisheries Jetty',
    mapZoom: 11,
    region: 'Andaman & Nicobar Islands (Bay of Bengal)',
  },
];

export const DEFAULT_LOCATION: LocationState = COASTAL_LOCATIONS[0];

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

interface LocationContextType {
  selectedLocation: LocationState;
  setSelectedLocation: (loc: LocationState) => void;
  locationsList: LocationState[];
  liveData: OrcaLiveMarineData | null;
  marineConditions: MarineCondition[];
  safetyAssessment: SafetyAssessment;
  isLoading: boolean;
  isLive: boolean;
  liveSource: 'fastapi' | 'open-meteo' | 'cached' | 'unavailable' | 'mock-fallback';
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
  const [liveSource, setLiveSource] = useState<'fastapi' | 'open-meteo' | 'cached' | 'unavailable' | 'mock-fallback'>('fastapi');
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [locationNotice, setLocationNotice] = useState<string | null>(null);

  const clearLocationNotice = useCallback(() => {
    setLocationNotice(null);
  }, []);

  const loadLocationData = useCallback(async (loc: LocationState) => {
    setIsLoading(true);
    clearLocationNotice();

    try {
      // Save active location selection to verified cache
      await cacheService.set('location', 'active_location', loc, 'User Selection');

      const [marineRes, safetyRes] = await Promise.all([
        getLiveOrcaMarineData(loc.latitude, loc.longitude, loc.name),
        getVerifiedSafetyAssessment(loc.latitude, loc.longitude, loc.name),
      ]);

      setLiveData(marineRes);
      setMarineConditions(mapToMarineConditions(marineRes));
      setSafetyAssessment(safetyRes);

      const isRealLive = marineRes.isLive === true;
      const isCached = marineRes.is_cached === true;

      setIsLive(isRealLive);
      setLiveSource(marineRes.source as any);

      if (isRealLive) {
        setLastUpdated(formatTimestampIST(Date.now()));
      } else if (isCached && marineRes.cache_timestamp) {
        setLastUpdated(formatTimestampIST(marineRes.cache_timestamp));
        setLocationNotice(`Showing verified cached intelligence from ${formatTimestampIST(marineRes.cache_timestamp)}.`);
      } else {
        setLastUpdated('Unavailable');
        setLocationNotice(`Live marine telemetry currently unavailable for ${loc.name}.`);
      }
    } catch (err) {
      console.warn(`[LocationProvider] Error fetching data for ${loc.name}:`, err);
      setIsLive(false);
      setLiveSource('unavailable');
      setLastUpdated('Unavailable');
      setLocationNotice(`Marine telemetry unavailable for ${loc.name}.`);
    } finally {
      setIsLoading(false);
    }
  }, [clearLocationNotice]);

  // Initial load & automatic recovery listener
  useEffect(() => {
    loadLocationData(DEFAULT_LOCATION);

    // Register auto-recovery listener when connection is restored
    const unsubscribeRecovery = connectivityService.onRecovery(async () => {
      console.info('[LocationProvider] Network restored. Syncing live telemetry for', selectedLocation.name);
      await loadLocationData(selectedLocation);
    });

    return () => {
      unsubscribeRecovery();
    };
  }, [loadLocationData, selectedLocation]);

  const setSelectedLocation = useCallback((loc: LocationState) => {
    setSelectedLocationState(loc);
    loadLocationData(loc);
  }, [loadLocationData]);

  const refreshData = useCallback(async (loc?: LocationState) => {
    await loadLocationData(loc || selectedLocation);
  }, [loadLocationData, selectedLocation]);

  /**
   * Handle user clicking on the map
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
