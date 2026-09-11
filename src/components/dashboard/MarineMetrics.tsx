'use client';

import React, { useEffect, useState } from 'react';
import {
  Thermometer,
  Leaf,
  Wind,
  Waves,
  CloudRain,
  ArrowUpDown,
  TrendingDown,
  TrendingUp,
  Minus,
} from 'lucide-react';
import { useTranslation } from '@/lib/i18n';
import { useLocation } from '@/lib/location';
import { MarineCondition } from '@/types';
import { MapPin, Crosshair, AlertCircle } from 'lucide-react';

const iconMap: Record<string, React.ReactNode> = {
  thermometer: <Thermometer size={16} />,
  leaf: <Leaf size={16} />,
  wind: <Wind size={16} />,
  waves: <Waves size={16} />,
  cloudRain: <CloudRain size={16} />,
  arrowUpDown: <ArrowUpDown size={16} />,
};

const statusColorMap: Record<string, string> = {
  green: 'bg-green-50 text-green-700 border-green-200',
  amber: 'bg-amber-50 text-amber-700 border-amber-200',
  red: 'bg-red-50 text-red-700 border-red-200',
  blue: 'bg-blue-100 text-blue-500 border-blue-200',
  gray: 'bg-gray-50 text-gray-600 border-gray-200',
};

const statusDotMap: Record<string, string> = {
  green: 'bg-green-500',
  amber: 'bg-amber-500',
  red: 'bg-red-500',
  blue: 'bg-blue-500',
  gray: 'bg-gray-400',
};

const iconBgMap: Record<string, string> = {
  green: 'bg-green-100 text-green-600',
  amber: 'bg-amber-100 text-amber-600',
  red: 'bg-red-100 text-red-600',
  blue: 'bg-blue-100 text-blue-600',
  gray: 'bg-gray-100 text-gray-500',
};

export default function MarineMetrics() {
  const { t } = useTranslation();
  const {
    selectedLocation,
    setSelectedLocation,
    locationsList,
    marineConditions: conditions,
    isLoading,
    isLive,
    liveSource,
    lastUpdated,
    locationNotice,
    clearLocationNotice,
    useMyLocation,
  } = useLocation();

  return (
    <div className="flex flex-col gap-2">
      {/* Location Selector & Live Status Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-1 text-[11px]">
        {/* Left: Location Selector & Connection Pill */}
        <div className="flex flex-wrap items-center gap-2.5">
          <span className="font-bold text-navy-900 tracking-wide text-[11px] uppercase">
            Live Marine Environment
          </span>

          {/* Assessment Location Selector */}
          <div className="inline-flex items-center gap-1.5 bg-white border border-gray-200 rounded-lg px-2.5 py-1 shadow-xs">
            <MapPin size={12} className="text-teal-600 flex-shrink-0" />
            <label htmlFor="assessment-location-select" className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">
              Assessment Location:
            </label>
            <select
              id="assessment-location-select"
              value={selectedLocation.name}
              onChange={(e) => {
                const found = locationsList.find((l) => l.name === e.target.value);
                if (found) setSelectedLocation(found);
              }}
              className="bg-transparent text-[11px] font-semibold text-navy-900 focus:outline-none cursor-pointer pr-1"
            >
              {locationsList.map((loc) => (
                <option key={loc.name} value={loc.name}>
                  {loc.name} ({loc.latitude.toFixed(2)}°N, {loc.longitude.toFixed(2)}°E)
                </option>
              ))}
              {selectedLocation.isCustom && (
                <option value={selectedLocation.name}>
                  {selectedLocation.name}
                </option>
              )}
            </select>

            <button
              onClick={useMyLocation}
              title="Use My Location"
              aria-label="Use My Location"
              className="p-1 text-teal-600 hover:text-teal-800 hover:bg-teal-50 rounded transition-colors flex items-center gap-1 text-[10px] font-medium ml-1 border-l border-gray-200 pl-2 cursor-pointer"
            >
              <Crosshair size={11} />
              <span className="hidden sm:inline">Use My Location</span>
            </button>
          </div>

          {/* Connection / Status Badge */}
          {isLoading ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-blue-50 border border-blue-200 text-[10px] font-medium text-blue-700 animate-pulse">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-ping" />
              Updating marine conditions...
            </span>
          ) : isLive ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-teal-50 border border-teal-200 text-[10px] font-semibold text-teal-700 shadow-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-teal-500 animate-pulse" />
              {liveSource === 'fastapi' ? 'Connected: FastAPI Backend (Open-Meteo)' : 'Connected: Open-Meteo Live API'}
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-amber-50 border border-amber-200 text-[10px] font-medium text-amber-700">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
              Marine data temporarily unavailable for this location.
            </span>
          )}
        </div>

        {/* Right: Coordinates & Last Updated */}
        <div className="flex items-center gap-2 text-[10px] text-gray-500 font-mono">
          <span className="hidden md:inline">
            {selectedLocation.name} • {selectedLocation.latitude.toFixed(4)}°N, {selectedLocation.longitude.toFixed(4)}°E
          </span>
          <span className="text-gray-300 hidden md:inline">•</span>
          <span className="text-navy-700 font-semibold">
            {isLoading ? 'Updating marine conditions...' : `Last updated: ${lastUpdated || 'Live Telemetry'}`}
          </span>
        </div>
      </div>

      {/* Notice Banner (e.g. land click warning or unavailable state) */}
      {locationNotice && (
        <div className="flex items-center justify-between px-3 py-1.5 bg-amber-50 border border-amber-200 text-amber-900 rounded-lg text-[11px] transition-all shadow-xs">
          <div className="flex items-center gap-2">
            <AlertCircle size={14} className="text-amber-600 flex-shrink-0" />
            <span className="font-medium">{locationNotice}</span>
          </div>
          <button
            onClick={clearLocationNotice}
            className="text-amber-700 hover:text-amber-900 font-bold text-xs px-1.5 py-0.5 rounded hover:bg-amber-100 transition-colors"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Conditions Horizontal Cards */}
      <div className="flex gap-3 overflow-x-auto pb-1 scrollbar-thin">
        {isLoading ? (
          // Loading Skeleton Cards for the selected location
          [
            { id: 'sst', label: 'metric_sst', icon: 'thermometer', unit: '°C' },
            { id: 'chlorophyll', label: 'metric_chlorophyll', icon: 'leaf', unit: 'mg/m³' },
            { id: 'wind', label: 'metric_wind', icon: 'wind', unit: 'kts' },
            { id: 'waves', label: 'metric_waves', icon: 'waves', unit: 'm' },
            { id: 'precipitation', label: 'metric_precipitation', icon: 'cloudRain', unit: 'mm' },
            { id: 'tide', label: 'metric_tide', icon: 'arrowUpDown', unit: '' },
          ].map((item) => (
            <div
              key={item.id}
              className="flex-shrink-0 flex-1 min-w-[155px] bg-white rounded-xl border border-blue-100 p-3.5 shadow-xs animate-pulse"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-400 flex items-center justify-center">
                  {iconMap[item.icon]}
                </div>
                <span className="text-[9px] font-semibold text-blue-500 bg-blue-50 px-1.5 py-0.5 rounded">
                  Fetching...
                </span>
              </div>
              <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">
                {t(item.label as keyof typeof t)}
              </p>
              <div className="flex items-baseline gap-1 mb-2">
                <span className="text-xl font-bold text-gray-300">--</span>
                <span className="text-xs text-gray-400 font-medium">{item.unit}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 border border-blue-100">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-ping" />
                  Updating...
                </span>
              </div>
            </div>
          ))
        ) : !isLive ? (
          // Unavailable State Cards
          conditions.map((c) => (
            <div
              key={c.id}
              className="flex-shrink-0 flex-1 min-w-[155px] bg-white rounded-xl border border-gray-200 p-3.5 opacity-90"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-gray-100 text-gray-500">
                  {iconMap[c.icon]}
                </div>
                <span className="text-[9px] font-semibold text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-100">
                  Unavailable
                </span>
              </div>
              <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">
                {t(c.label as keyof typeof t)}
              </p>
              <div className="flex items-baseline gap-1 mb-2">
                <span className="text-xl font-bold text-gray-400">--</span>
                <span className="text-xs text-gray-400 font-medium">{c.unit}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border bg-amber-50 text-amber-700 border-amber-200">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                  Data Pending
                </span>
              </div>
            </div>
          ))
        ) : (
          // Live Data Cards for Selected Location
          conditions.map((c) => (
            <div
              key={c.id}
              className="flex-shrink-0 flex-1 min-w-[155px] bg-white rounded-xl border border-gray-200 p-3.5 hover:shadow-md hover:border-gray-300 transition-all duration-200"
            >
              <div className="flex items-start justify-between mb-2">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${iconBgMap[c.statusColor]}`}>
                  {iconMap[c.icon]}
                </div>
                {c.id === 'chlorophyll' ? (
                  <span className="text-[9px] font-semibold text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
                    Satellite Feed Pending
                  </span>
                ) : c.source ? (
                  <span className="text-[9px] font-semibold text-teal-600 bg-teal-50/80 px-1.5 py-0.5 rounded border border-teal-100">
                    Source: Open-Meteo
                  </span>
                ) : c.delta ? (
                  <span className="flex items-center gap-0.5 text-[11px] text-gray-500">
                    {c.deltaDirection === 'down' && <TrendingDown size={11} className="text-blue-500" />}
                    {c.deltaDirection === 'up' && <TrendingUp size={11} className="text-red-500" />}
                    {c.deltaDirection === 'stable' && <Minus size={11} className="text-gray-400" />}
                    {c.delta}
                  </span>
                ) : null}
              </div>

              <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">
                {t(c.label as keyof typeof t)}
              </p>

              <div className="flex items-baseline gap-1 mb-2">
                <span className="text-xl font-bold text-navy-900">{c.value}</span>
                <span className="text-xs text-gray-500 font-medium">{c.unit}</span>
              </div>

              <div className="flex items-center justify-between">
                <span className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border ${statusColorMap[c.statusColor]}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${statusDotMap[c.statusColor]}`} />
                  {c.status}
                </span>
                {c.detail && (
                  <span className="text-[10px] text-gray-400 truncate max-w-[85px]" title={c.detail}>
                    {c.detail}
                  </span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
