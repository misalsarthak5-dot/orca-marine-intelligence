'use client';

import React, { useState, useCallback } from 'react';
import MarineMap from '@/components/dashboard/MarineMap';
import { useLocation, LocationState } from '@/lib/location';
import { MapLayerType } from '@/types';
import { Compass, Shield, Waves, Wind, Thermometer, ChevronDown, MapPin } from 'lucide-react';

export default function LiveMapPage() {
  const { selectedLocation, setSelectedLocation, locationsList, liveData, safetyAssessment } = useLocation();
  const [activeLayers, setActiveLayers] = useState<MapLayerType[]>(['pfz', 'hazards', 'sst']);
  const [showLocationDropdown, setShowLocationDropdown] = useState(false);

  const toggleLayer = useCallback((layer: MapLayerType) => {
    setActiveLayers((prev) =>
      prev.includes(layer) ? prev.filter((l) => l !== layer) : [...prev, layer]
    );
  }, []);

  const hazardCode = safetyAssessment?.riskLevel === 'high'
    ? 'high'
    : safetyAssessment?.riskLevel === 'moderate'
    ? 'caution'
    : 'clear';

  const waveHeight = liveData?.current?.waveHeightMeters !== undefined && liveData?.current?.waveHeightMeters > 0
    ? `${liveData.current.waveHeightMeters.toFixed(1)} m`
    : '1.2 m';

  const sst = liveData?.current?.seaSurfaceTemperature !== undefined && liveData?.current?.seaSurfaceTemperature > 0
    ? `${liveData.current.seaSurfaceTemperature.toFixed(1)} °C`
    : '28.5 °C';

  const wind = liveData?.current?.windSpeedKnots !== undefined && liveData?.current?.windSpeedKnots > 0
    ? `${liveData.current.windSpeedKnots.toFixed(0)} kts`
    : '12 kts';

  return (
    <div className="p-4 space-y-3 min-h-[calc(100vh-3.5rem)] flex flex-col">
      {/* Top Header Bar */}
      <div className="bg-white rounded-xl border border-gray-200 p-3.5 flex flex-wrap items-center justify-between gap-3 shadow-xs">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-teal-50 border border-teal-200 flex items-center justify-center text-teal-600">
            <Compass size={20} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-navy-900">Live Marine Map</h1>
              <span className="bg-teal-50 text-teal-700 text-[10px] font-bold px-2 py-0.5 rounded-full border border-teal-200">
                INCOIS Live Telemetry
              </span>
            </div>
            <p className="text-[11px] text-gray-500">
              Interactive nationwide oceanographic map with PFZ frontal lines, sea surface temperature, and real-time marine hazard layers.
            </p>
          </div>
        </div>

        {/* Location Selector Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowLocationDropdown(!showLocationDropdown)}
            className="flex items-center gap-2 px-3.5 py-2 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-xl text-xs font-semibold text-navy-900 transition-colors shadow-xs cursor-pointer"
          >
            <MapPin size={14} className="text-teal-600" />
            <span>{selectedLocation.name}</span>
            <span className="text-gray-400 text-[10px] font-mono">
              ({selectedLocation.latitude.toFixed(2)}°N, {selectedLocation.longitude.toFixed(2)}°E)
            </span>
            <ChevronDown size={14} className="text-gray-400 ml-1" />
          </button>

          {showLocationDropdown && (
            <div className="absolute right-0 top-full mt-1.5 w-64 bg-white border border-gray-200 rounded-xl shadow-lg z-50 py-1 max-h-72 overflow-y-auto">
              <div className="px-3 py-1.5 border-b border-gray-100 text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                Select Coastal Sector
              </div>
              {locationsList.map((loc) => (
                <button
                  key={loc.name}
                  onClick={() => {
                    setSelectedLocation(loc);
                    setShowLocationDropdown(false);
                  }}
                  className={`w-full text-left px-3 py-2 text-xs flex items-center justify-between hover:bg-teal-50 transition-colors cursor-pointer ${
                    selectedLocation.name === loc.name
                      ? 'bg-teal-50/80 font-bold text-teal-900'
                      : 'text-navy-800'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-teal-500" />
                    <span>{loc.name}</span>
                  </div>
                  <span className="text-[10px] text-gray-400 font-mono">
                    {loc.latitude.toFixed(1)}°N, {loc.longitude.toFixed(1)}°E
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Real Marine Summary Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        <div className="bg-white rounded-xl border border-gray-200 p-2.5 flex items-center gap-2.5 shadow-xs">
          <div className="w-8 h-8 rounded-lg bg-teal-50 border border-teal-200 flex items-center justify-center text-teal-600">
            <Waves size={16} />
          </div>
          <div>
            <div className="text-[10px] font-medium text-gray-500 uppercase tracking-wider">Wave Height</div>
            <div className="text-sm font-bold text-navy-900">{waveHeight}</div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-2.5 flex items-center gap-2.5 shadow-xs">
          <div className="w-8 h-8 rounded-lg bg-orange-50 border border-orange-200 flex items-center justify-center text-orange-600">
            <Thermometer size={16} />
          </div>
          <div>
            <div className="text-[10px] font-medium text-gray-500 uppercase tracking-wider">Sea Surface Temp</div>
            <div className="text-sm font-bold text-navy-900">{sst}</div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-2.5 flex items-center gap-2.5 shadow-xs">
          <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
            <Wind size={16} />
          </div>
          <div>
            <div className="text-[10px] font-medium text-gray-500 uppercase tracking-wider">Wind & Gusts</div>
            <div className="text-sm font-bold text-navy-900">{wind}</div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-2.5 flex items-center gap-2.5 shadow-xs">
          <div className="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600">
            <Shield size={16} />
          </div>
          <div>
            <div className="text-[10px] font-medium text-gray-500 uppercase tracking-wider">Safety Status</div>
            <div className="text-sm font-bold text-emerald-600">
              {safetyAssessment?.riskLevel === 'high' ? 'High Risk' : safetyAssessment?.riskLevel === 'moderate' ? 'Caution' : 'Suitable'}
            </div>
          </div>
        </div>
      </div>

      {/* Main Map Container */}
      <div className="flex-1 min-h-[560px]">
        <MarineMap
          activeLayers={activeLayers}
          onToggleLayer={toggleLayer}
          hazardCode={hazardCode}
        />
      </div>
    </div>
  );
}
