'use client';

import React, { useEffect, useState } from 'react';
import {
  Search,
  Plus,
  Minus,
  Crosshair,
  Layers,
  Navigation,
} from 'lucide-react';
import { useTranslation } from '@/lib/i18n';
import { MapLayerType } from '@/types';
import { pfzZones } from '@/data/mockPFZData';
import { avoidZones, recommendedRoute } from '@/data/mockRoutes';

interface MarineMapProps {
  activeLayers: MapLayerType[];
  onToggleLayer: (layer: MapLayerType) => void;
}

const layerConfig: { id: MapLayerType; label: string; color: string }[] = [
  { id: 'pfz', label: 'PFZ', color: 'bg-green-500' },
  { id: 'weather', label: 'Weather', color: 'bg-blue-500' },
  { id: 'sst', label: 'SST', color: 'bg-orange-500' },
  { id: 'chlorophyll', label: 'Chlorophyll+', color: 'bg-emerald-500' },
  { id: 'risk', label: 'Risk', color: 'bg-red-500' },
  { id: 'geofence', label: 'Geofence', color: 'bg-purple-500' },
  { id: 'route', label: 'Route', color: 'bg-teal-500' },
];

// Dynamic import for Leaflet - only loads on client
const LeafletMap = React.lazy(() => import('./LeafletMap'));

export default function MarineMap({ activeLayers, onToggleLayer }: MarineMapProps) {
  const { t } = useTranslation();
  const [isClient, setIsClient] = useState(false);
  const [mapControls, setMapControls] = useState<{
    zoomIn: () => void;
    zoomOut: () => void;
    recenter: () => void;
  } | null>(null);

  useEffect(() => {
    setIsClient(true);
  }, []);

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden flex flex-col">
      {/* Title bar */}
      <div className="px-4 py-2.5 border-b border-gray-100 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold text-teal-600 bg-teal-50 px-2 py-0.5 rounded uppercase tracking-wider border border-teal-100">
              {t('map_assessedArea')} 4
            </span>
            <h3 className="text-[13px] font-bold text-navy-900">{t('map_title')}</h3>
          </div>
          <p className="text-[10px] text-gray-400 font-medium tracking-wider uppercase mt-0.5">
            {t('map_subtitle')}
          </p>
        </div>
        <div className="flex items-center gap-1">
          <Navigation size={12} className="text-teal-500" />
          <span className="text-[10px] text-gray-500 font-mono">
            LAT: 18°54&apos;12&quot;N | LON: 72°41&apos;56&quot;E | HDG: 240° • 8.2 KTS
          </span>
        </div>
      </div>

      {/* Layer toggles */}
      <div className="px-4 py-2 border-b border-gray-50 flex items-center gap-1.5">
        {layerConfig.map((layer) => {
          const active = activeLayers.includes(layer.id);
          return (
            <button
              key={layer.id}
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
            <LeafletMap activeLayers={activeLayers} onMapReady={setMapControls} />
          </React.Suspense>
        )}

        {/* Legend overlay */}
        <div className="absolute bottom-3 left-3 z-[1000] bg-white/95 backdrop-blur-sm border border-gray-200 rounded-lg px-3 py-2 shadow-sm">
          <div className="flex items-center gap-3 text-[10px]">
            <span className="flex items-center gap-1">
              <span className="w-3 h-2 rounded-sm bg-green-500/60 border border-green-600/30" />
              PFZ High Density
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-2 rounded-sm bg-yellow-500/60 border border-yellow-600/30" />
              PFZ Moderate
            </span>
            <span className="flex items-center gap-1">
              <span className="w-6 h-0.5 bg-teal-500" />
              Safe Corridor
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-2 rounded-sm bg-red-500/30 border border-red-500/50" />
              Risk Zone
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
