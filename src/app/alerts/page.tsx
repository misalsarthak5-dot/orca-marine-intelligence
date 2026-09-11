'use client';

import React from 'react';
import MarineHazardsAlerts from '@/components/dashboard/MarineHazardsAlerts';
import FishingSafetyAssessment from '@/components/dashboard/FishingSafetyAssessment';
import { useLocation } from '@/lib/location';
import { AlertTriangle, PhoneCall, MapPin } from 'lucide-react';

export default function AlertsPage() {
  const { selectedLocation, setSelectedLocation, locationsList } = useLocation();

  return (
    <div className="p-4 space-y-4 max-w-6xl mx-auto">
      {/* Top Header */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600">
              <AlertTriangle size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold text-navy-900">Marine Hazards & Live Alerts</h1>
                <span className="bg-amber-50 text-amber-800 text-[10px] font-bold px-2 py-0.5 rounded-full border border-amber-200">
                  Real-time Telemetry
                </span>
              </div>
              <p className="text-[11px] text-gray-500 mt-0.5">
                Multi-parameter coastal hazard assessment based on Open-Meteo marine models and INCOIS bulletins.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-xs font-semibold text-gray-500 flex items-center gap-1">
              <MapPin size={12} className="text-teal-600" />
              Sector:
            </label>
            <select
              value={selectedLocation.name}
              onChange={(e) => {
                const found = locationsList.find((l) => l.name === e.target.value);
                if (found) setSelectedLocation(found);
              }}
              aria-label="Select Coastal Sector"
              className="text-xs font-bold text-navy-900 bg-gray-50 border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-teal-500/30 cursor-pointer"
            >
              {locationsList.map((loc) => (
                <option key={loc.name} value={loc.name}>
                  {loc.name} ({loc.latitude.toFixed(1)}°N, {loc.longitude.toFixed(1)}°E)
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Main Grid: Hazards + Safety Assessment */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-7">
          <MarineHazardsAlerts />
        </div>

        <div className="lg:col-span-5 space-y-4">
          <FishingSafetyAssessment />

          {/* Emergency & Official Coastal Contacts */}
          <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-xs">
            <div className="flex items-center gap-2 mb-3">
              <PhoneCall size={16} className="text-teal-600" />
              <h3 className="text-xs font-bold text-navy-900 uppercase tracking-wider">
                Coastal Safety & Emergency Lines
              </h3>
            </div>
            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between p-2 bg-gray-50 rounded-lg border border-gray-100">
                <span className="font-semibold text-navy-800">Indian Coast Guard SAR Toll-Free</span>
                <span className="font-mono font-bold text-teal-700 bg-white px-2 py-0.5 rounded border border-gray-200">
                  1554
                </span>
              </div>
              <div className="flex items-center justify-between p-2 bg-gray-50 rounded-lg border border-gray-100">
                <span className="font-semibold text-navy-800">INCOIS Ocean State Forecast Centre</span>
                <span className="font-mono text-gray-600 text-[11px]">incois.gov.in</span>
              </div>
              <div className="flex items-center justify-between p-2 bg-gray-50 rounded-lg border border-gray-100">
                <span className="font-semibold text-navy-800">IMD Cyclone Warning Division</span>
                <span className="font-mono text-gray-600 text-[11px]">mausam.imd.gov.in</span>
              </div>
            </div>
            <p className="text-[10px] text-gray-400 mt-3 leading-relaxed">
              In severe conditions, always consult harbour master advisories and adhere strictly to localized fishing bans or port signals.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
