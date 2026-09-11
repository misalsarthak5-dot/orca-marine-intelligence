'use client';

import React from 'react';
import { Navigation, Compass, Shield, MapPin } from 'lucide-react';
import { useLocation } from '@/lib/location';

export default function FleetPage() {
  const { selectedLocation } = useLocation();

  return (
    <div className="p-4 space-y-4 max-w-4xl mx-auto">
      <div className="bg-white rounded-xl border border-gray-200 p-8 shadow-xs text-center">
        <div className="w-14 h-14 rounded-2xl bg-teal-50 border border-teal-200 flex items-center justify-center mx-auto mb-4 text-teal-600">
          <Navigation size={28} />
        </div>
        <h1 className="text-xl font-bold text-navy-900 mb-2">Route Intelligence</h1>
        <p className="text-sm text-gray-500 max-w-lg mx-auto leading-relaxed mb-6">
          Analyze marine conditions, wave hazards, and risk factors before selecting a navigational corridor.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-left max-w-2xl mx-auto pt-2 border-t border-gray-100">
          <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
            <div className="flex items-center gap-1.5 text-xs font-bold text-teal-800 mb-1">
              <MapPin size={13} className="text-teal-600" />
              Active Origin
            </div>
            <div className="text-xs text-gray-600">
              {selectedLocation.name} ({selectedLocation.latitude.toFixed(2)}°N, {selectedLocation.longitude.toFixed(2)}°E)
            </div>
          </div>

          <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
            <div className="flex items-center gap-1.5 text-xs font-bold text-teal-800 mb-1">
              <Shield size={13} className="text-teal-600" />
              Dynamic Safety
            </div>
            <div className="text-xs text-gray-600">
              Evaluates live wave heights and wind corridors along waypoint tracks.
            </div>
          </div>

          <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
            <div className="flex items-center gap-1.5 text-xs font-bold text-teal-800 mb-1">
              <Compass size={13} className="text-teal-600" />
              PFZ Vector Targeting
            </div>
            <div className="text-xs text-gray-600">
              Corridor generation towards official INCOIS Potential Fishing Zones.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
