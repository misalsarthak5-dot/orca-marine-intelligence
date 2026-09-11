'use client';

import React, { useEffect, useState } from 'react';
import {
  Search,
  Plus,
  Minus,
  Crosshair,
  Layers,
  Navigation,
  Info,
} from 'lucide-react';
import { useTranslation } from '@/lib/i18n';
import { useLocation } from '@/lib/location';
import { MapLayerType, CandidateRoute } from '@/types';

interface MarineMapProps {
  activeLayers: MapLayerType[];
  onToggleLayer: (layer: MapLayerType) => void;
  /** Live hazard severity from the MarineHazardsAlerts card */
  hazardCode?: 'clear' | 'caution' | 'high';
  /** Route Intelligence corridors */
  routes?: CandidateRoute[];
  recommendedRouteId?: string;
  selectedRouteId?: string;
  onSelectRoute?: (routeId: string) => void;
  destination?: { latitude: number; longitude: number; name: string };
  onMapClickCoordinates?: (lat: number, lon: number) => void;
}

const layerConfig: { id: MapLayerType; label: string; color: string }[] = [
  { id: 'pfz', label: 'PFZ', color: 'bg-green-500' },
  { id: 'hazards', label: 'Hazards', color: 'bg-amber-500' },
  { id: 'sst', label: 'SST', color: 'bg-orange-500' },
  { id: 'weather', label: 'Weather', color: 'bg-blue-500' },
  { id: 'chlorophyll', label: 'Chlorophyll+', color: 'bg-emerald-500' },
  { id: 'risk', label: 'Risk', color: 'bg-red-500' },
  { id: 'geofence', label: 'Geofence', color: 'bg-purple-500' },
  { id: 'route', label: 'Route', color: 'bg-teal-500' },
];

// Dynamic import for Leaflet - only loads on client
const LeafletMap = React.lazy(() => import('./LeafletMap'));

export default function MarineMap({
  activeLayers,
  onToggleLayer,
  hazardCode = 'caution',
  routes,
  recommendedRouteId,
  selectedRouteId,
  onSelectRoute,
  destination,
  onMapClickCoordinates,
}: MarineMapProps) {
  const { t } = useTranslation();
  const { selectedLocation } = useLocation();
  const [isClient, setIsClient] = useState(false);
  const [mapControls, setMapControls] = useState<{
    zoomIn: () => void;
    zoomOut: () => void;
    recenter: () => void;
  } | null>(null);

  useEffect(() => {
    setIsClient(true);
  }, []);

  const showSstLegend = activeLayers.includes('sst');

  return (
    <div id="orca-marine-map" className="bg-white rounded-xl border border-gray-200 overflow-hidden flex flex-col scroll-mt-4">
      {/* Title bar */}
      <div className="px-4 py-2.5 border-b border-gray-100 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold text-teal-600 bg-teal-50 px-2 py-0.5 rounded uppercase tracking-wider border border-teal-100">
              {t('map_assessedArea')}
            </span>
            <h3 className="text-[13px] font-bold text-navy-900">{selectedLocation.name} • Coastal Intelligence</h3>
          </div>
          <p className="text-[10px] text-teal-700 font-semibold tracking-wider mt-0.5">
            {selectedLocation.name} • {selectedLocation.latitude.toFixed(4)}°N, {selectedLocation.longitude.toFixed(4)}°E
          </p>
        </div>
        <div className="flex items-center gap-1">
          <Navigation size={12} className="text-teal-500" />
          <span className="text-[10px] text-gray-500 font-mono">
            LAT: {selectedLocation.latitude.toFixed(4)}°N | LON: {selectedLocation.longitude.toFixed(4)}°E
          </span>
        </div>
      </div>

      {/* Layer toggles */}
      <div className="px-4 py-2 border-b border-gray-50 flex items-center gap-1.5 flex-wrap">
        {layerConfig.map((layer) => {
          const active = activeLayers.includes(layer.id);
          return (
            <button
              key={layer.id}
              title={layer.label}
              onClick={() => onToggleLayer(layer.id)}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
                active
                  ? 'bg-navy-900 text-white shadow-sm'
                  : 'bg-gray-100 text-gray-500 hover:bg-gray-200 hover:text-gray-700'
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${active ? 'bg-white' : layer.color}`} />
              {layer.label}
            </button>
          );
        })}
      </div>

      {/* Location telemetry source notice */}
      <div className="px-4 py-2 bg-teal-50 border-b border-teal-200/80 flex items-center justify-between gap-2 text-[11px] text-teal-900">
        <div className="flex items-center gap-1.5 font-medium">
          <Info size={14} className="text-teal-600 flex-shrink-0" />
          <span>Official INCOIS PFZ Advisories, SST, and Marine Hazards active for {selectedLocation.name}.</span>
        </div>
        <span className="text-[10px] bg-teal-100 text-teal-800 font-semibold px-2 py-0.5 rounded border border-teal-200">
          INCOIS & Open-Meteo
        </span>
      </div>

      {/* Map container */}
      <div className="relative flex-1 min-h-[380px]">
        {/* Search overlay */}
        <div className="absolute top-3 left-3 right-14 z-[1000]">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder={t('map_searchPlaceholder')}
              className="w-full pl-9 pr-4 py-2 bg-white/95 backdrop-blur-sm border border-gray-200 rounded-lg text-[12px] text-navy-800 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-400 shadow-sm"
            />
          </div>
        </div>

        {/* Zoom controls overlay */}
        <div className="absolute top-3 right-3 z-[1000] flex flex-col gap-1">
          <button
            onClick={() => mapControls?.zoomIn()}
            title="Zoom In"
            aria-label="Zoom In"
            className="w-8 h-8 bg-white border border-gray-200 rounded-lg flex items-center justify-center hover:bg-gray-50 active:bg-gray-100 shadow-sm transition-colors cursor-pointer"
          >
            <Plus size={14} className="text-navy-700" />
          </button>
          <button
            onClick={() => mapControls?.zoomOut()}
            title="Zoom Out"
            aria-label="Zoom Out"
            className="w-8 h-8 bg-white border border-gray-200 rounded-lg flex items-center justify-center hover:bg-gray-50 active:bg-gray-100 shadow-sm transition-colors cursor-pointer"
          >
            <Minus size={14} className="text-navy-700" />
          </button>
          <button
            onClick={() => mapControls?.recenter()}
            title="Recenter Map"
            aria-label="Recenter Map"
            className="w-8 h-8 bg-white border border-gray-200 rounded-lg flex items-center justify-center hover:bg-gray-50 active:bg-gray-100 shadow-sm transition-colors cursor-pointer mt-1"
          >
            <Crosshair size={14} className="text-navy-700" />
          </button>
        </div>

        {/* Actual map */}
        {isClient && (
          <React.Suspense
            fallback={
              <div className="absolute inset-0 flex items-center justify-center bg-gray-50">
                <div className="text-center">
                  <div className="w-8 h-8 border-2 border-teal-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                  <p className="text-[11px] text-gray-400">Loading map...</p>
                </div>
              </div>
            }
          >
            <LeafletMap
              selectedLocation={selectedLocation}
              activeLayers={activeLayers}
              onMapReady={setMapControls}
              hazardCode={hazardCode}
              routes={routes}
              recommendedRouteId={recommendedRouteId}
              selectedRouteId={selectedRouteId}
              onSelectRoute={onSelectRoute}
              destination={destination}
              onMapClickCoordinates={onMapClickCoordinates}
            />
          </React.Suspense>
        )}

        {/* Legend overlay */}
        <div className="absolute bottom-3 left-3 z-[1000] bg-white/95 backdrop-blur-sm border border-gray-200 rounded-xl px-3.5 py-2.5 shadow-md space-y-2 max-w-xs">
          {/* Route Legend when Route Layer is Active or Routes are available */}
          {(activeLayers.includes('route') || (routes && routes.length > 0)) && (
            <div className="pb-2 border-b border-gray-100 space-y-1.5">
              <div className="text-[10px] font-bold text-navy-900 uppercase tracking-wider flex items-center gap-1.5">
                <Navigation size={11} className="text-teal-600" />
                <span>Route Intelligence Legend</span>
              </div>
              <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[10px]">
                <div className="flex items-center gap-1.5">
                  <div className="w-5 h-1 bg-teal-600 rounded-full shadow-xs" />
                  <span className="font-semibold text-teal-900">Recommended</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-5 h-0.5 border-t-2 border-dashed border-sky-500" />
                  <span className="text-gray-600">Alternative</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px]">⚓</span>
                  <span className="font-medium text-navy-800">Origin Port</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px]">🎯</span>
                  <span className="font-medium text-navy-800">PFZ Target</span>
                </div>
                <div className="flex items-center gap-1.5 col-span-2">
                  <div className="w-4 h-2 rounded-xs bg-rose-500/20 border border-dashed border-rose-500" />
                  <span className="text-rose-700 font-medium">Restricted / Avoidance Zone</span>
                </div>
              </div>
            </div>
          )}

          {showSstLegend && (
            <div className="flex items-center gap-2 text-[10px] pb-1 border-b border-gray-100">
              <span className="font-bold text-navy-900">Sea Surface Temp:</span>
              <span className="text-blue-600 font-medium">Cooler</span>
              <div
                className="h-1.5 w-16 rounded-full"
                style={{
                  background: 'linear-gradient(to right, #3b82f6, #06b6d4, #10b981, #f59e0b, #ef4444)',
                }}
              />
              <span className="text-rose-600 font-medium">Warmer</span>
              <span className="text-gray-400 text-[8px]">(Open-Meteo)</span>
            </div>
          )}

          <div className="flex items-center gap-2 text-[10px] text-gray-600">
            <span className="w-2 h-2 rounded-full bg-teal-500" />
            <span className="font-semibold text-teal-800">{selectedLocation.name} Active</span>
            <span className="text-gray-300">•</span>
            <span className="text-gray-500">Official INCOIS PFZ Vectors & Open-Meteo Telemetry</span>
          </div>
        </div>
      </div>
    </div>
  );
}
