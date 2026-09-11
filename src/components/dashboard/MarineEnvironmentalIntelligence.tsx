'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Thermometer,
  FlaskConical,
  Satellite,
  RefreshCw,
  AlertCircle,
  Info,
  Database,
  MapPin,
  Activity,
  ExternalLink,
} from 'lucide-react';
import { useLocation } from '@/lib/location';
import { fetchChlorophyll, ChlorophyllResult } from '@/services/chlorophyllService';

interface MarineEnvironmentalIntelligenceProps {
  onShowSSTOnMap?: () => void;
}

export default function MarineEnvironmentalIntelligence({
  onShowSSTOnMap,
}: MarineEnvironmentalIntelligenceProps) {
  const { selectedLocation, liveData, isLoading: locationLoading } = useLocation();
  const [chlorophyll, setChlorophyll] = useState<ChlorophyllResult | null>(null);
  const [chlLoading, setChlLoading] = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState('');

  // ── SST: reuse existing liveData from useLocation (Open-Meteo Marine) ──────
  // This is the exact same value shown in MarineMetrics — never duplicated or re-fetched.
  const sst = liveData?.current.seaSurfaceTemperature ?? null;
  const sstAvailable = sst !== null && sst !== undefined && !isNaN(sst);

  // SST thermal classification (matches Open-Meteo typical Indian Ocean ranges)
  const getSSTInfo = (temp: number): { label: string; color: string; dot: string; detail: string } => {
    if (temp < 24)  return { label: 'Cool Waters',    color: 'text-blue-700',    dot: 'bg-blue-500',    detail: 'Below seasonal average' };
    if (temp < 27)  return { label: 'Moderate',       color: 'text-teal-700',    dot: 'bg-teal-500',    detail: 'Seasonal baseline range' };
    if (temp < 29)  return { label: 'Warm Waters',    color: 'text-amber-700',   dot: 'bg-amber-500',   detail: 'Active pelagic zone indicator' };
    if (temp < 31)  return { label: 'Very Warm',      color: 'text-orange-700',  dot: 'bg-orange-500',  detail: 'Summer peak — monitor mixing' };
    return           { label: 'Elevated SST',          color: 'text-rose-700',    dot: 'bg-rose-500',    detail: 'Well above seasonal baseline' };
  };

  const sstInfo = sstAvailable ? getSSTInfo(sst!) : null;

  // ── Chlorophyll: fetch from backend /api/chlorophyll ─────────────────────
  const loadChlorophyll = useCallback(async () => {
    setChlLoading(true);
    try {
      const result = await fetchChlorophyll(
        selectedLocation.latitude,
        selectedLocation.longitude
      );
      setChlorophyll(result);
    } catch {
      setChlorophyll({
        available: false,
        value: null,
        unit: 'mg/m³',
        source: 'NASA Ocean Color / MODIS-Aqua',
        provider: 'NASA Earthdata',
        status: 'not_connected',
        message: 'Satellite data source not connected.',
      });
    } finally {
      setChlLoading(false);
      setLastRefreshed(
        new Date().toLocaleTimeString('en-IN', {
          hour: '2-digit',
          minute: '2-digit',
          timeZone: 'Asia/Kolkata',
        }) + ' IST'
      );
    }
  }, [selectedLocation.latitude, selectedLocation.longitude]);

  useEffect(() => {
    loadChlorophyll();
  }, [loadChlorophyll]);

  return (
    <div
      id="orca-environmental-intelligence"
      className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm"
    >
      {/* ── Header ── */}
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-teal-50 text-teal-700 rounded-md">
            <Activity size={15} />
          </div>
          <div>
            <h3 className="text-[12px] font-bold text-navy-900 uppercase tracking-wider">
              Marine Environmental Intelligence
            </h3>
            <p className="text-[10px] text-gray-500 flex items-center gap-1 mt-0.5">
              <MapPin size={10} className="text-teal-600 flex-shrink-0" />
              <span className="font-semibold text-navy-800">{selectedLocation.name}</span>
              <span>
                ({selectedLocation.latitude.toFixed(2)}°N, {selectedLocation.longitude.toFixed(2)}°E)
              </span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {lastRefreshed && (
            <span className="text-[9px] text-gray-400 hidden sm:block">{lastRefreshed}</span>
          )}
          <button
            onClick={() => loadChlorophyll()}
            disabled={chlLoading}
            title="Refresh environmental data"
            className="p-1.5 text-gray-400 hover:text-teal-600 hover:bg-teal-50 rounded-lg transition-colors"
          >
            <RefreshCw size={12} className={chlLoading ? 'animate-spin text-teal-500' : ''} />
          </button>
        </div>
      </div>

      {/* ── Body ── */}
      <div className="p-4 grid grid-cols-1 sm:grid-cols-2 gap-4">

        {/* ── SST Panel ── */}
        <div className="rounded-xl border border-blue-100 bg-gradient-to-br from-blue-50/60 to-teal-50/40 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="p-1.5 bg-blue-100 text-blue-600 rounded-lg">
                <Thermometer size={14} />
              </div>
              <span className="text-[11px] font-bold text-navy-900 uppercase tracking-wider">
                Sea Surface Temperature
              </span>
            </div>
            <button
              onClick={onShowSSTOnMap}
              title="Show SST on map"
              className="text-[9px] font-semibold text-teal-600 hover:text-teal-800 flex items-center gap-1 px-2 py-1 rounded-md hover:bg-teal-50 transition-colors border border-teal-100"
            >
              Map
              <ExternalLink size={9} />
            </button>
          </div>

          {locationLoading ? (
            <div className="h-10 bg-blue-100/50 rounded-lg animate-pulse" />
          ) : sstAvailable ? (
            <>
              <div className="flex items-baseline gap-1.5 mb-1.5">
                <span className="text-3xl font-black text-navy-900 tabular-nums tracking-tight">
                  {sst!.toFixed(1)}
                </span>
                <span className="text-lg font-bold text-gray-500">°C</span>
              </div>
              <div className="flex items-center gap-1.5 mb-3">
                <span className={`w-2 h-2 rounded-full ${sstInfo!.dot}`} />
                <span className={`text-[10px] font-bold ${sstInfo!.color}`}>
                  {sstInfo!.label}
                </span>
                <span className="text-[9px] text-gray-400">— {sstInfo!.detail}</span>
              </div>
            </>
          ) : (
            <div className="flex items-center gap-2 py-2">
              <AlertCircle size={14} className="text-amber-500 flex-shrink-0" />
              <span className="text-[11px] text-amber-700 font-medium">
                SST data unavailable — check Open-Meteo connection.
              </span>
            </div>
          )}

          {/* SST Color Scale Legend */}
          <div className="mt-1 mb-3">
            <div className="flex justify-between text-[8px] font-bold text-gray-400 mb-1">
              <span className="text-blue-600">Cooler</span>
              <span className="text-orange-600">Warmer</span>
            </div>
            <div
              className="h-2 w-full rounded-full"
              style={{
                background: 'linear-gradient(to right, #3b82f6, #06b6d4, #10b981, #f59e0b, #ef4444)',
              }}
            />
            <div className="flex justify-between text-[8px] text-gray-400 mt-0.5">
              <span>&lt;24°C</span>
              <span>27°C</span>
              <span>&gt;30°C</span>
            </div>
          </div>

          {/* Source label */}
          <div className="mt-auto pt-2 border-t border-blue-100">
            <div className="flex items-center gap-1.5">
              <Database size={10} className="text-teal-600" />
              <span className="text-[9px] font-semibold text-teal-700">
                Source: Open-Meteo Marine API
              </span>
            </div>
            <p className="text-[8px] text-gray-400 mt-0.5">
              Model-derived surface temperature • Not satellite imagery
            </p>
          </div>
        </div>

        {/* ── Chlorophyll Panel ── */}
        <div className="rounded-xl border border-emerald-100 bg-gradient-to-br from-emerald-50/40 to-slate-50/40 p-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="p-1.5 bg-emerald-100 text-emerald-600 rounded-lg">
              <FlaskConical size={14} />
            </div>
            <span className="text-[11px] font-bold text-navy-900 uppercase tracking-wider">
              Chlorophyll-a (Ocean Color)
            </span>
          </div>

          {chlLoading ? (
            <div className="h-10 bg-emerald-100/40 rounded-lg animate-pulse mb-3" />
          ) : (
            <>
              {/* Unavailable Badge */}
              <div className="flex items-start gap-2 bg-slate-50 border border-slate-200 rounded-lg p-2.5 mb-3">
                <AlertCircle size={13} className="text-slate-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-[10px] font-bold text-slate-700">
                    Satellite Data Unavailable
                  </p>
                  <p className="text-[9px] text-slate-500 mt-0.5 leading-relaxed">
                    NASA Ocean Color satellite source not connected.
                    Chlorophyll-a values will appear here when integrated.
                  </p>
                </div>
              </div>

              {/* Future Value Placeholder (honest) */}
              <div className="flex items-baseline gap-1.5 mb-1.5 opacity-35">
                <span className="text-2xl font-black text-slate-400">—</span>
                <span className="text-sm font-bold text-slate-400">mg/m³</span>
              </div>
            </>
          )}

          {/* Source + Readiness */}
          <div className="pt-2 border-t border-emerald-100 space-y-1.5">
            <div className="flex items-center gap-1.5">
              <Satellite size={10} className="text-emerald-600" />
              <span className="text-[9px] font-semibold text-emerald-700">
                Source: NASA Ocean Color / MODIS-Aqua
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
              <span className="text-[9px] font-bold text-slate-500">
                Status: Not Connected
              </span>
            </div>
            <div className="flex items-start gap-1.5 pt-1">
              <Info size={9} className="text-slate-400 flex-shrink-0 mt-0.5" />
              <p className="text-[8px] text-slate-400 leading-relaxed">
                Integration path: NASA Earthdata (OB.DAAC) or INCOIS ocean-color
                bulletin. Data will appear here when the satellite source is connected.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* ── Footer Note ── */}
      <div className="px-4 pb-3">
        <p className="text-[9px] text-gray-400 italic bg-gray-50 px-3 py-2 rounded-md border border-gray-100">
          ORCA Environmental Intelligence uses verified model and satellite data sources.
          SST is derived from Open-Meteo marine model output, not satellite imagery.
          Chlorophyll-a will be added when NASA Ocean Color or INCOIS data is connected.
        </p>
      </div>
    </div>
  );
}
