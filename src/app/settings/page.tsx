'use client';

import React, { useState } from 'react';
import { useTranslation } from '@/lib/i18n';
import { useLocation } from '@/lib/location';
import { Language } from '@/types';
import { Settings, Globe, MapPin, Server, Check, Sliders } from 'lucide-react';
import { FASTAPI_BASE_URL } from '@/config/api';

const languages: { code: Language; name: string; nativeName: string }[] = [
  { code: 'en', name: 'English', nativeName: 'English' },
  { code: 'hi', name: 'Hindi', nativeName: 'हिंदी' },
  { code: 'mr', name: 'Marathi', nativeName: 'मराठी' },
];

export default function SettingsPage() {
  const { language, setLanguage } = useTranslation();
  const { selectedLocation, setSelectedLocation, locationsList } = useLocation();
  const [units, setUnits] = useState<'metric' | 'nautical'>('metric');

  return (
    <div className="p-4 space-y-4 max-w-4xl mx-auto">
      {/* Top Banner */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-xs">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-teal-50 border border-teal-200 flex items-center justify-center text-teal-600">
            <Settings size={20} />
          </div>
          <div>
            <h1 className="text-base font-bold text-navy-900">Application Settings</h1>
            <p className="text-[11px] text-gray-500 mt-0.5">
              Manage language preferences, coastal operational sector, and data feed integrations.
            </p>
          </div>
        </div>
      </div>

      {/* Language Preferences Card */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-xs space-y-3">
        <div className="flex items-center gap-2 pb-2 border-b border-gray-100">
          <Globe size={16} className="text-teal-600" />
          <h2 className="text-xs font-bold text-navy-900 uppercase tracking-wider">
            Language Preference / भाषा निवडा
          </h2>
        </div>
        <p className="text-xs text-gray-500">
          Select the interface and Ask ORCA conversational response language:
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
          {languages.map((lang) => {
            const isSelected = language === lang.code;
            return (
              <button
                key={lang.code}
                onClick={() => setLanguage(lang.code)}
                className={`p-3 rounded-xl border text-left transition-all flex items-center justify-between cursor-pointer ${
                  isSelected
                    ? 'border-teal-600 bg-teal-50/70 text-teal-900 ring-1 ring-teal-500/20'
                    : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50 text-navy-800'
                }`}
              >
                <div>
                  <div className="text-sm font-bold">{lang.nativeName}</div>
                  <div className="text-[11px] text-gray-500">{lang.name}</div>
                </div>
                {isSelected && (
                  <div className="w-5 h-5 rounded-full bg-teal-600 text-white flex items-center justify-center">
                    <Check size={12} />
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Default Coastal Sector Selection */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-xs space-y-3">
        <div className="flex items-center gap-2 pb-2 border-b border-gray-100">
          <MapPin size={16} className="text-teal-600" />
          <h2 className="text-xs font-bold text-navy-900 uppercase tracking-wider">
            Active Coastal Sector
          </h2>
        </div>
        <p className="text-xs text-gray-500">
          Choose your primary operating harbour or coastal district for instant marine metrics:
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 pt-1">
          {locationsList.map((loc) => {
            const isSelected = selectedLocation.name === loc.name;
            return (
              <button
                key={loc.name}
                onClick={() => setSelectedLocation(loc)}
                className={`p-2.5 rounded-lg border text-left text-xs transition-all cursor-pointer ${
                  isSelected
                    ? 'border-teal-600 bg-teal-50 text-teal-900 font-bold'
                    : 'border-gray-200 hover:bg-gray-50 text-navy-800'
                }`}
              >
                <div className="truncate">{loc.name}</div>
                <div className="text-[10px] text-gray-400 font-mono mt-0.5">
                  {loc.latitude.toFixed(1)}°N, {loc.longitude.toFixed(1)}°E
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Measurement Units */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-xs space-y-3">
        <div className="flex items-center gap-2 pb-2 border-b border-gray-100">
          <Sliders size={16} className="text-teal-600" />
          <h2 className="text-xs font-bold text-navy-900 uppercase tracking-wider">
            Measurement Units
          </h2>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setUnits('metric')}
            className={`px-4 py-2 rounded-lg text-xs font-semibold border transition-colors cursor-pointer ${
              units === 'metric'
                ? 'bg-teal-600 text-white border-teal-600 shadow-xs'
                : 'bg-gray-50 text-gray-700 border-gray-200 hover:bg-gray-100'
            }`}
          >
            Metric (km/h, m, °C)
          </button>
          <button
            onClick={() => setUnits('nautical')}
            className={`px-4 py-2 rounded-lg text-xs font-semibold border transition-colors cursor-pointer ${
              units === 'nautical'
                ? 'bg-teal-600 text-white border-teal-600 shadow-xs'
                : 'bg-gray-50 text-gray-700 border-gray-200 hover:bg-gray-100'
            }`}
          >
            Nautical (kts, ft, °F)
          </button>
        </div>
      </div>

      {/* Connected Data Services */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-xs space-y-3">
        <div className="flex items-center gap-2 pb-2 border-b border-gray-100">
          <Server size={16} className="text-teal-600" />
          <h2 className="text-xs font-bold text-navy-900 uppercase tracking-wider">
            Connected Data Services
          </h2>
        </div>

        <div className="space-y-2 text-xs">
          <div className="flex items-center justify-between p-2.5 bg-gray-50 rounded-lg border border-gray-100">
            <div>
              <div className="font-semibold text-navy-900">INCOIS GeoServer WFS (PFZ &amp; Landing Centres)</div>
              <div className="text-[10px] text-gray-400">PFZ_Automation:pfzlines &bull; PFZ_LandingCentres</div>
            </div>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-green-100 text-green-800 text-[10px] font-bold">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
              Connected
            </span>
          </div>

          <div className="flex items-center justify-between p-2.5 bg-gray-50 rounded-lg border border-gray-100">
            <div>
              <div className="font-semibold text-navy-900">Open-Meteo Marine &amp; Weather API</div>
              <div className="text-[10px] text-gray-400">Wave swell, wind gusts, temperature, precipitation</div>
            </div>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-green-100 text-green-800 text-[10px] font-bold">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
              Connected
            </span>
          </div>

          <div className="flex items-center justify-between p-2.5 bg-gray-50 rounded-lg border border-gray-100">
            <div>
              <div className="font-semibold text-navy-900">ORCA FastAPI Backend</div>
              <div className="text-[10px] text-gray-400 font-mono">{FASTAPI_BASE_URL}</div>
            </div>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-green-100 text-green-800 text-[10px] font-bold">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
              Active
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
