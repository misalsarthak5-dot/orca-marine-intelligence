'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Navigation,
  Compass,
  Shield,
  MapPin,
  Anchor,
  AlertTriangle,
  CheckCircle2,
  Wind,
  Waves,
  Clock,
  ArrowRight,
  TrendingDown,
  Info,
  Layers,
  Sparkles,
  RefreshCw,
  Sliders,
} from 'lucide-react';
import { useLocation } from '@/lib/location';
import { useTranslation } from '@/lib/i18n';
import { MapLayerType, CandidateRoute, RouteAnalysisResponse } from '@/types';
import { analyzeMarineRoutes } from '@/services/routeService';
import { fetchFastAPIPFZ, PFZAdvisory } from '@/services/pfzService';
import MarineMap from './MarineMap';

interface TargetDestination {
  name: string;
  latitude: number;
  longitude: number;
  advisoryInfo?: string;
}

export default function RouteIntelligence() {
  const { selectedLocation } = useLocation();
  const { t, language } = useTranslation();

  // Destination state
  const [destMode, setDestMode] = useState<'pfz' | 'custom'>('pfz');
  const [availablePfzs, setAvailablePfzs] = useState<PFZAdvisory[]>([]);
  const [loadingPfz, setLoadingPfz] = useState<boolean>(true);
  const [selectedPfzId, setSelectedPfzId] = useState<string>('');
  
  // Custom destination inputs
  const [customLat, setCustomLat] = useState<string>('');
  const [customLon, setCustomLon] = useState<string>('');
  const [customName, setCustomName] = useState<string>('Custom Marine Waypoint');

  // Time window state
  const [timeWindow, setTimeWindow] = useState<'current' | 'tomorrow_morning' | 'tomorrow'>('tomorrow_morning');

  // Analysis results
  const [analysisResult, setAnalysisResult] = useState<RouteAnalysisResponse | null>(null);
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null);

  // Map layers
  const [activeLayers, setActiveLayers] = useState<MapLayerType[]>(['route', 'pfz', 'hazards', 'weather']);

  const toggleLayer = (layer: MapLayerType) => {
    setActiveLayers((prev) =>
      prev.includes(layer) ? prev.filter((l) => l !== layer) : [...prev, layer]
    );
  };

  // Load real PFZ landing centres for the selected location
  useEffect(() => {
    let isMounted = true;
    
    // Clear previous location's analysis immediately to prevent stale state across locations
    setAnalysisResult(null);
    setSelectedRouteId(null);
    setAnalysisError(null);
    setCustomLat('');
    setCustomLon('');

    async function loadPfzCentres() {
      setLoadingPfz(true);
      try {
        const pfzData = await fetchFastAPIPFZ(selectedLocation.latitude, selectedLocation.longitude, 350);
        if (!isMounted) return;
        
        if (pfzData.active_advisories && pfzData.active_advisories.length > 0) {
          setAvailablePfzs(pfzData.active_advisories);
          setSelectedPfzId(pfzData.active_advisories[0].id);
          setDestMode('pfz');
        } else if (pfzData.nearest_advisory) {
          setAvailablePfzs([pfzData.nearest_advisory]);
          setSelectedPfzId(pfzData.nearest_advisory.id);
          setDestMode('pfz');
        } else {
          setAvailablePfzs([]);
          setSelectedPfzId('');
          setDestMode('custom');
        }
      } catch (err) {
        if (isMounted) {
          setAvailablePfzs([]);
          setSelectedPfzId('');
          setDestMode('custom');
        }
      } finally {
        if (isMounted) setLoadingPfz(false);
      }
    }

    loadPfzCentres();
    return () => {
      isMounted = false;
    };
  }, [selectedLocation.name, selectedLocation.latitude, selectedLocation.longitude]);

  // Determine current active destination coordinates
  // Preferred destination is the offshore INCOIS PFZ target feature, while landing centres serve as reference.
  const getActiveDestination = useCallback((): TargetDestination | null => {
    if (destMode === 'pfz') {
      const pfz = availablePfzs.find((p) => p.id === selectedPfzId);
      if (pfz) {
        const lcLat = pfz.lc_coordinates.latitude;
        const lcLon = pfz.lc_coordinates.longitude;
        const distKm = pfz.advisory_distance_to_km || pfz.advisory_distance_from_km || 25;
        const bearing = pfz.bearing_degrees !== null && pfz.bearing_degrees !== undefined ? pfz.bearing_degrees : 240;
        
        // Calculate offshore PFZ feature target coordinate using bearing & advisory distance
        const rad = (bearing * Math.PI) / 180;
        const targetLat = lcLat + (distKm / 111.0) * Math.cos(rad);
        const targetLon = lcLon + (distKm / (111.0 * Math.cos((lcLat * Math.PI) / 180))) * Math.sin(rad);

        return {
          name: `${pfz.landing_center} PFZ Target (${distKm} km ${pfz.direction || ''})`,
          latitude: Number(targetLat.toFixed(4)),
          longitude: Number(targetLon.toFixed(4)),
          advisoryInfo: `${distKm} km ${pfz.direction || ''} (${pfz.depth_from_m || 20}–${pfz.depth_to_m || 60}m depth) • Ref Landing Centre: ${pfz.landing_center}`,
        };
      }
      return null;
    } else {
      const lat = parseFloat(customLat);
      const lon = parseFloat(customLon);
      if (!isNaN(lat) && !isNaN(lon)) {
        return {
          name: customName || 'Selected Route Destination',
          latitude: lat,
          longitude: lon,
        };
      }
      return null;
    }
  }, [destMode, availablePfzs, selectedPfzId, customLat, customLon, customName]);

  // View Routes on Map handler: activates route layer, selects recommended corridor, fits bounds
  const handleViewRoutesOnMap = () => {
    if (!activeLayers.includes('route')) {
      setActiveLayers((prev) => [...prev, 'route']);
    }
    if (analysisResult?.recommended_route_id) {
      setSelectedRouteId(analysisResult.recommended_route_id);
    }
    const coords: [number, number][] = [];
    coords.push([selectedLocation.latitude, selectedLocation.longitude]);
    const dest = getActiveDestination();
    if (dest) {
      coords.push([dest.latitude, dest.longitude]);
    }
    if (analysisResult?.routes) {
      analysisResult.routes.forEach((r) => {
        r.coordinates.forEach((c) => coords.push([c[0], c[1]]));
      });
    }
    window.dispatchEvent(
      new CustomEvent('orca:fit-route-bounds', {
        detail: { coordinates: coords },
      })
    );
  };

  // Analyze routes handler
  const handleAnalyzeRoutes = async (overrideDest?: TargetDestination) => {
    const dest = overrideDest || getActiveDestination();
    if (!dest) {
      setAnalysisError(t('route_no_pfz') || 'Please select a destination on the map or enter coordinates.');
      return;
    }

    setAnalyzing(true);
    setAnalysisError(null);

    try {
      const result = await analyzeMarineRoutes({
        origin_lat: selectedLocation.latitude,
        origin_lon: selectedLocation.longitude,
        destination_lat: dest.latitude,
        destination_lon: dest.longitude,
        destination_name: dest.name,
        time_window: timeWindow,
      });

      if (!result.available) {
        setAnalysisError(result.disclaimer || 'Route analysis service temporarily unavailable.');
        setAnalysisResult(null);
      } else {
        setAnalysisResult(result);
        setSelectedRouteId(result.recommended_route_id);
        if (!activeLayers.includes('route')) {
          setActiveLayers((prev) => [...prev, 'route']);
        }
      }
    } catch (err) {
      setAnalysisError('Failed to analyze routes. Please check connection to ORCA backend.');
      setAnalysisResult(null);
    } finally {
      setAnalyzing(false);
    }
  };

  // Handler for user clicking directly on the map to choose destination
  const handleMapClick = (lat: number, lon: number) => {
    const formattedLat = lat.toFixed(4);
    const formattedLon = lon.toFixed(4);
    setCustomLat(formattedLat);
    setCustomLon(formattedLon);
    setCustomName('Selected Route Destination');
    setDestMode('custom');
    
    const clickedDest: TargetDestination = {
      name: 'Selected Route Destination',
      latitude: parseFloat(formattedLat),
      longitude: parseFloat(formattedLon),
    };
    handleAnalyzeRoutes(clickedDest);
  };

  // Auto-run analysis when destination or time window changes
  useEffect(() => {
    const dest = getActiveDestination();
    if (dest) {
      handleAnalyzeRoutes(dest);
    }
  }, [selectedPfzId, timeWindow]);

  const activeDestination = getActiveDestination();
  const recommendedRoute = analysisResult?.routes?.find(
    (r) => r.id === analysisResult.recommended_route_id
  );

  return (
    <div className="p-4 space-y-5 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-navy-900 via-navy-800 to-teal-950 rounded-2xl border border-navy-700/60 p-6 text-white shadow-lg relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="p-2 bg-teal-500/20 border border-teal-400/30 rounded-xl text-teal-300">
                <Navigation size={22} className="rotate-45" />
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-white">
                {t('route_intel_title') || 'Route Intelligence'}
              </h1>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-teal-500/20 text-teal-300 border border-teal-400/30">
                Decision Support MVP
              </span>
            </div>
            <p className="text-sm text-gray-300 max-w-2xl">
              {t('route_intel_subtitle') || 'Compare marine conditions and risk across possible routes.'}
            </p>
          </div>

          <div className="flex items-center gap-3">
            {analysisResult && (
              <button
                onClick={handleViewRoutesOnMap}
                className="flex items-center gap-2 px-4 py-2.5 bg-teal-500/20 hover:bg-teal-500/30 text-teal-300 font-bold rounded-xl border border-teal-400/40 shadow-sm transition-all cursor-pointer text-sm"
              >
                <Compass size={16} />
                <span>View Routes on Map</span>
              </button>
            )}
            <button
              onClick={() => handleAnalyzeRoutes()}
              disabled={analyzing || !activeDestination}
              className="flex items-center gap-2 px-5 py-2.5 bg-teal-500 hover:bg-teal-400 active:bg-teal-600 disabled:opacity-50 text-navy-950 font-bold rounded-xl shadow-md transition-all cursor-pointer text-sm"
            >
              <RefreshCw size={16} className={analyzing ? 'animate-spin' : ''} />
              <span>{analyzing ? (t('route_analyzing') || 'Analyzing Corridors...') : (t('route_analyze_btn') || 'Analyze Routes')}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Control Panel: Origin, Destination & Time Window */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Origin Selector / Info */}
        <div className="bg-white rounded-2xl border border-gray-200/80 p-5 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
              <MapPin size={14} className="text-teal-600" />
              {t('route_origin') || 'Origin (Shared Coastal Location)'}
            </span>
            <span className="w-2 h-2 rounded-full bg-teal-500 animate-pulse" />
          </div>
          
          <div className="p-3.5 bg-teal-50/50 rounded-xl border border-teal-100/80">
            <div className="font-bold text-navy-900 text-base flex items-center gap-2">
              <span>{selectedLocation.name}</span>
              <span className="text-xs font-normal text-teal-700 px-2 py-0.5 bg-teal-100/60 rounded-md">
                Active Coastline
              </span>
            </div>
            <div className="text-xs text-gray-600 mt-1 font-mono">
              {selectedLocation.latitude.toFixed(4)}° N, {selectedLocation.longitude.toFixed(4)}° E
            </div>
          </div>
          <p className="text-[11px] text-gray-500 leading-normal">
            Linked to ORCA global location state. To switch departure port, use the top location bar.
          </p>
        </div>

        {/* Destination Selector */}
        <div className="bg-white rounded-2xl border border-gray-200/80 p-5 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
              <Anchor size={14} className="text-teal-600" />
              {t('route_destination') || 'Destination / Target PFZ'}
            </span>
            
            {/* Mode switch */}
            <div className="flex items-center bg-gray-100 p-0.5 rounded-lg text-[11px] font-medium">
              {availablePfzs.length > 0 && (
                <button
                  onClick={() => setDestMode('pfz')}
                  className={`px-2 py-0.5 rounded-md transition-all ${
                    destMode === 'pfz' ? 'bg-white text-teal-700 shadow-xs font-bold' : 'text-gray-500'
                  }`}
                >
                  PFZ Target
                </button>
              )}
              <button
                onClick={() => setDestMode('custom')}
                className={`px-2 py-0.5 rounded-md transition-all ${
                  destMode === 'custom' ? 'bg-white text-teal-700 shadow-xs font-bold' : 'text-gray-500'
                }`}
              >
                Custom
              </button>
            </div>
          </div>

          {destMode === 'pfz' && availablePfzs.length > 0 ? (
            <div className="space-y-2">
              {loadingPfz ? (
                <div className="p-3 bg-gray-50 rounded-xl border border-gray-100 flex items-center gap-2 text-xs text-gray-500">
                  <div className="w-4 h-4 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" />
                  <span>Loading INCOIS landing centres...</span>
                </div>
              ) : (
                <select
                  value={selectedPfzId}
                  onChange={(e) => setSelectedPfzId(e.target.value)}
                  className="w-full text-xs font-semibold text-navy-900 bg-gray-50 border border-gray-200 rounded-xl p-2.5 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
                >
                  {availablePfzs.map((pfz) => (
                    <option key={pfz.id} value={pfz.id}>
                      {pfz.landing_center} ({pfz.district || pfz.sector}) — {pfz.distance_from_query_km ? `${pfz.distance_from_query_km.toFixed(1)} km away` : 'Active PFZ'}
                    </option>
                  ))}
                </select>
              )}

              {activeDestination?.advisoryInfo && (
                <div className="text-[11px] text-teal-800 bg-teal-50/60 px-2.5 py-1 rounded-lg border border-teal-100">
                  Sector: {activeDestination.advisoryInfo}
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-2">
              {availablePfzs.length === 0 && (
                <div className="p-2.5 bg-amber-50/70 rounded-xl border border-amber-200/60 text-[11px] text-amber-900 leading-tight">
                  No localized INCOIS PFZ target identified. Click anywhere on the map or enter coordinates to evaluate route risk.
                </div>
              )}
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="number"
                  step="0.0001"
                  placeholder="Latitude (e.g. 11.55)"
                  value={customLat}
                  onChange={(e) => setCustomLat(e.target.value)}
                  className="text-xs p-2 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:border-teal-500"
                />
                <input
                  type="number"
                  step="0.0001"
                  placeholder="Longitude (e.g. 92.85)"
                  value={customLon}
                  onChange={(e) => setCustomLon(e.target.value)}
                  className="text-xs p-2 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:border-teal-500"
                />
              </div>
              <input
                type="text"
                placeholder="Waypoint / Target Name"
                value={customName}
                onChange={(e) => setCustomName(e.target.value)}
                className="w-full text-xs p-2 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:border-teal-500"
              />
            </div>
          )}
        </div>

        {/* Forecast Period Selector */}
        <div className="bg-white rounded-2xl border border-gray-200/80 p-5 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
              <Clock size={14} className="text-teal-600" />
              {t('route_time_window') || 'Forecast Period'}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-2">
            {[
              { id: 'current', label: 'Current' },
              { id: 'tomorrow_morning', label: 'Tomorrow AM' },
              { id: 'tomorrow', label: 'Tomorrow' },
            ].map((period) => (
              <button
                key={period.id}
                onClick={() => setTimeWindow(period.id as any)}
                className={`py-2.5 px-2 rounded-xl text-xs font-bold transition-all text-center border cursor-pointer ${
                  timeWindow === period.id
                    ? 'bg-navy-900 text-white border-navy-900 shadow-sm'
                    : 'bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100'
                }`}
              >
                {period.label}
              </button>
            ))}
          </div>
          <p className="text-[11px] text-gray-500 leading-normal">
            Samples real-time marine waves and wind forecasts along each waypoint track for the chosen period.
          </p>
        </div>
      </div>

      {/* Analysis Error Notification */}
      {analysisError && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-2xl text-rose-800 text-sm flex items-start gap-3">
          <AlertTriangle size={18} className="text-rose-600 shrink-0 mt-0.5" />
          <div>
            <div className="font-bold">Route Analysis Error</div>
            <div className="text-xs text-rose-700 mt-0.5">{analysisError}</div>
          </div>
        </div>
      )}

      {/* Recommendation Highlight Banner */}
      {analysisResult && recommendedRoute && (
        <div className="bg-gradient-to-r from-emerald-900 via-teal-900 to-navy-900 rounded-2xl border border-emerald-500/30 p-5 text-white shadow-md space-y-3">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-400/40 flex items-center justify-center text-emerald-300 shrink-0">
                <CheckCircle2 size={22} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-emerald-300">
                    {t('route_recommended') || 'ORCA RECOMMENDED CORRIDOR'}
                  </span>
                  <span className="px-2 py-0.5 bg-emerald-500/20 border border-emerald-400/30 rounded text-[10px] font-bold text-emerald-200">
                    {recommendedRoute.name}
                  </span>
                </div>
                <div className="text-sm font-semibold text-gray-200 mt-0.5">
                  {analysisResult.recommendation_reason}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3 shrink-0">
              <div className="flex items-center gap-4 bg-white/10 px-4 py-2 rounded-xl backdrop-blur-xs border border-white/10">
                <div>
                  <div className="text-[10px] uppercase text-gray-300 font-bold">Route Risk</div>
                  <div className="text-lg font-extrabold text-emerald-300">
                    {recommendedRoute.risk_score} <span className="text-xs font-normal text-gray-300">/ 100</span>
                  </div>
                </div>
                <div className="w-px h-8 bg-white/20" />
                <div>
                  <div className="text-[10px] uppercase text-gray-300 font-bold">Distance</div>
                  <div className="text-lg font-extrabold text-white">
                    {recommendedRoute.distance_km} <span className="text-xs font-normal text-gray-300">km</span>
                  </div>
                </div>
                <div className="w-px h-8 bg-white/20" />
                <div>
                  <div className="text-[10px] uppercase text-gray-300 font-bold">Duration</div>
                  <div className="text-lg font-extrabold text-white">
                    {recommendedRoute.estimated_time_hours} <span className="text-xs font-normal text-gray-300">hrs</span>
                  </div>
                </div>
              </div>

              <button
                onClick={handleViewRoutesOnMap}
                className="flex items-center gap-1.5 px-3.5 py-2.5 bg-emerald-500 hover:bg-emerald-400 text-navy-950 font-bold text-xs rounded-xl shadow-md transition-all cursor-pointer shrink-0"
              >
                <Compass size={14} />
                <span>View on Map</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Content: Route Comparison Cards & Map */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Column: Route Comparison Cards */}
        <div className="lg:col-span-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-navy-900 uppercase tracking-wider flex items-center gap-2">
              <Compass size={16} className="text-teal-600" />
              Candidate Corridors ({analysisResult?.routes?.length || 0})
            </h2>
            <div className="flex items-center gap-2">
              {analysisResult && (
                <button
                  onClick={handleViewRoutesOnMap}
                  className="text-[11px] font-bold text-teal-700 bg-teal-50 hover:bg-teal-100 px-2.5 py-1 rounded-lg border border-teal-200 transition-colors cursor-pointer flex items-center gap-1"
                >
                  <Navigation size={11} />
                  <span>View on Map</span>
                </button>
              )}
              <span className="text-[11px] text-gray-500 font-medium">
                {t('route_speed_note') || 'Estimated at 8 knots'}
              </span>
            </div>
          </div>

          {analyzing ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="p-4 bg-white rounded-2xl border border-gray-200 animate-pulse space-y-3">
                  <div className="h-4 bg-gray-200 rounded w-1/3" />
                  <div className="h-8 bg-gray-100 rounded" />
                  <div className="h-4 bg-gray-200 rounded w-2/3" />
                </div>
              ))}
            </div>
          ) : analysisResult && analysisResult.routes ? (
            <div className="space-y-3">
              {analysisResult.routes.map((route) => {
                const isRecommended = route.id === analysisResult.recommended_route_id;
                const isSelected = selectedRouteId === route.id;
                const isLow = route.risk_level === 'LOW';
                const isCaution = route.risk_level === 'CAUTION';

                return (
                  <div
                    key={route.id}
                    onClick={() => {
                      setSelectedRouteId(route.id);
                      if (!activeLayers.includes('route')) {
                        setActiveLayers((prev) => [...prev, 'route']);
                      }
                    }}
                    className={`p-4 rounded-2xl border transition-all cursor-pointer relative ${
                      isSelected
                        ? 'bg-white border-teal-500 shadow-md ring-2 ring-teal-500/20'
                        : 'bg-white border-gray-200/80 hover:border-gray-300 shadow-xs'
                    }`}
                  >
                    {isRecommended && (
                      <div className="absolute -top-2.5 right-4 px-2.5 py-0.5 rounded-full text-[9px] font-extrabold uppercase tracking-wider bg-emerald-600 text-white shadow-xs">
                        ORCA Recommended
                      </div>
                    )}

                    <div className="flex items-start justify-between mb-2">
                      <div className="space-y-1">
                        <div className="font-bold text-navy-900 text-sm flex items-center flex-wrap gap-1.5">
                          <span>{route.name}</span>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              isLow
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                : isCaution
                                ? 'bg-amber-50 text-amber-700 border border-amber-200'
                                : 'bg-rose-50 text-rose-700 border border-rose-200'
                            }`}
                          >
                            Env Risk: {route.risk_level}
                          </span>
                          {route.restriction_status === 'RESTRICTED' ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-300">
                              RESTRICTED
                            </span>
                          ) : route.restriction_status === 'CLEAR' ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                              GEOFENCE CLEAR
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-600 border border-gray-200" title="Authoritative restriction data unavailable">
                              Geofence: Unavailable
                            </span>
                          )}
                          {route.overall_status === 'NOT_VIABLE' ? (
                            <span className="px-2 py-0.5 rounded text-[9px] font-extrabold bg-rose-600 text-white shadow-xs">
                              NOT VIABLE
                            </span>
                          ) : route.overall_status === 'VIABLE' ? (
                            <span className="px-2 py-0.5 rounded text-[9px] font-extrabold bg-emerald-600 text-white shadow-xs">
                              VIABLE
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[9px] font-medium bg-slate-800 text-slate-100">
                              ENV ANALYSIS ONLY
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-gray-500">
                          {route.distance_km} km • ~{route.estimated_time_hours} hrs @ 8 kt
                        </div>
                      </div>

                      <div className="text-right shrink-0">
                        <div
                          className={`text-xl font-extrabold ${
                            isLow ? 'text-emerald-600' : isCaution ? 'text-amber-600' : 'text-rose-600'
                          }`}
                        >
                          {route.risk_score}
                          <span className="text-[10px] text-gray-400 font-normal"> / 100</span>
                        </div>
                        <div className="text-[10px] font-semibold text-gray-400 uppercase">Risk Index</div>
                      </div>
                    </div>

                    {/* Marine Conditions Sampled */}
                    <div className="grid grid-cols-3 gap-2 py-2.5 my-2 border-y border-gray-100 bg-gray-50/60 rounded-xl px-2.5">
                      <div>
                        <div className="text-[10px] text-gray-500 flex items-center gap-1 font-medium">
                          <Waves size={11} className="text-teal-600" /> Peak Wave
                        </div>
                        <div className="text-xs font-bold text-navy-900 mt-0.5">
                          {route.conditions?.peak_wave_m !== null && route.conditions?.peak_wave_m !== undefined
                            ? `${route.conditions.peak_wave_m} m`
                            : 'N/A'}
                        </div>
                      </div>

                      <div>
                        <div className="text-[10px] text-gray-500 flex items-center gap-1 font-medium">
                          <Wind size={11} className="text-teal-600" /> Peak Wind
                        </div>
                        <div className="text-xs font-bold text-navy-900 mt-0.5">
                          {route.conditions?.peak_wind_kt !== null && route.conditions?.peak_wind_kt !== undefined
                            ? `${route.conditions.peak_wind_kt} kt`
                            : 'N/A'}
                        </div>
                      </div>

                      <div>
                        <div className="text-[10px] text-gray-500 flex items-center gap-1 font-medium">
                          <Wind size={11} className="text-amber-600" /> Peak Gust
                        </div>
                        <div className="text-xs font-bold text-navy-900 mt-0.5">
                          {route.conditions?.peak_gust_kt !== null && route.conditions?.peak_gust_kt !== undefined
                            ? `${route.conditions.peak_gust_kt} kt`
                            : 'N/A'}
                        </div>
                      </div>
                    </div>

                    {/* Risk Factors Tags & Select Action */}
                    <div className="flex items-center justify-between mt-2 pt-1">
                      <div className="flex flex-wrap gap-1">
                        {route.risk_factors && route.risk_factors.map((factor, idx) => (
                          <span
                            key={idx}
                            className="px-2 py-0.5 bg-gray-100 rounded-md text-[10px] text-gray-600 font-medium"
                          >
                            {factor}
                          </span>
                        ))}
                      </div>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${isSelected ? 'bg-teal-100 text-teal-800' : 'text-gray-400'}`}>
                        {isSelected ? 'Selected Corridor' : 'Click to Select'}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="p-8 bg-white rounded-2xl border border-gray-200 text-center space-y-2">
              <Compass size={32} className="mx-auto text-gray-300" />
              <div className="text-sm font-semibold text-gray-700">No Routes Analyzed Yet</div>
              <p className="text-xs text-gray-400 max-w-xs mx-auto">
                Select your destination above and click &quot;Analyze Routes&quot; to calculate marine risk corridors.
              </p>
            </div>
          )}

          {/* Explanation Panel */}
          {analysisResult && (
            <div className="bg-white rounded-2xl border border-gray-200/80 p-4 shadow-xs space-y-2">
              <div className="text-xs font-bold text-navy-900 uppercase tracking-wider flex items-center gap-1.5">
                <Info size={14} className="text-teal-600" />
                {t('route_why_rec') || 'WHY ORCA RECOMMENDS THIS CORRIDOR'}
              </div>
              <p className="text-xs text-gray-600 leading-relaxed">
                {analysisResult.recommendation_reason}
              </p>
            </div>
          )}
        </div>

        {/* Right Column: Live Interactive Map */}
        <div className="lg:col-span-7 space-y-4">
          <div className="bg-white rounded-2xl border border-gray-200/80 shadow-xs overflow-hidden">
            <div className="p-3.5 border-b border-gray-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Layers size={16} className="text-teal-600" />
                <span className="text-xs font-bold text-navy-900 uppercase tracking-wider">
                  Corridor Visualizer & Live Overlays
                </span>
              </div>
              
              <div className="flex items-center gap-2 text-[11px] text-gray-500">
                <span className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-teal-500" /> Route Corridors
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> PFZ Vectors
                </span>
              </div>
            </div>

            <div className="h-[460px] relative">
              <MarineMap
                activeLayers={activeLayers}
                onToggleLayer={toggleLayer}
                routes={analysisResult?.routes}
                recommendedRouteId={analysisResult?.recommended_route_id}
                selectedRouteId={selectedRouteId || undefined}
                onSelectRoute={(id) => setSelectedRouteId(id)}
                onMapClickCoordinates={handleMapClick}
                destination={
                  activeDestination
                    ? {
                        latitude: activeDestination.latitude,
                        longitude: activeDestination.longitude,
                        name: activeDestination.name,
                      }
                    : undefined
                }
              />
            </div>
          </div>

          {/* Data Provenance & Method Section */}
          <div className="bg-white rounded-2xl border border-gray-200/80 p-4 shadow-xs space-y-2">
            <div className="text-xs font-bold text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
              <Sparkles size={13} className="text-teal-600" />
              {t('route_data_provenance') || 'Data & Method Provenance'}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2 text-xs">
              <div className="p-2 bg-gray-50 rounded-xl border border-gray-100">
                <span className="text-gray-400 block text-[10px] font-bold">PFZ TARGET</span>
                <span className="font-semibold text-navy-900">INCOIS WFS</span>
              </div>
              <div className="p-2 bg-gray-50 rounded-xl border border-gray-100">
                <span className="text-gray-400 block text-[10px] font-bold">MARINE & WEATHER</span>
                <span className="font-semibold text-navy-900">Open-Meteo API</span>
              </div>
              <div className="p-2 bg-gray-50 rounded-xl border border-gray-100">
                <span className="text-gray-400 block text-[10px] font-bold">CORRIDOR GEOMETRY</span>
                <span className="font-semibold text-navy-900">ORCA Geodesic Engine</span>
              </div>
              <div className="p-2 bg-gray-50 rounded-xl border border-gray-100">
                <span className="text-gray-400 block text-[10px] font-bold">RISK SCORING</span>
                <span className="font-semibold text-navy-900">ORCA Safety Model</span>
              </div>
            </div>
          </div>

          {/* Official Safety Disclaimer */}
          <div className="p-3.5 bg-amber-50/50 border border-amber-200/60 rounded-2xl text-amber-900 text-xs flex items-start gap-2.5 leading-relaxed">
            <Shield size={16} className="text-amber-600 shrink-0 mt-0.5" />
            <span>
              {t('route_disclaimer') ||
                'ORCA provides decision-support recommendations based on available marine and weather data. Route suggestions are not authoritative navigation instructions and do not guarantee safety. Follow official maritime advisories and local authority guidance.'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
