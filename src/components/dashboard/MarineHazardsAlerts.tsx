'use client';

import React, { useEffect, useState, useCallback } from 'react';
import {
  AlertTriangle,
  AlertCircle,
  ShieldCheck,
  Waves,
  Wind,
  CloudRain,
  Zap,
  Activity,
  Layers,
  MapPin,
  RefreshCw,
  Info,
} from 'lucide-react';
import { useLocation } from '@/lib/location';
import { fetchFastAPIHazards } from '@/services/hazardService';
import { HazardAssessment, HazardCondition } from '@/types';

interface MarineHazardsAlertsProps {
  onShowOnMap?: () => void;
  /** Callback to lift hazard severity to parent (e.g., dashboard for map coloring) */
  onHazardCode?: (code: 'clear' | 'caution' | 'high') => void;
}

// Safe default theme in case overallCode is undefined/unexpected
const DEFAULT_STATE_THEME = {
  bg: 'bg-emerald-50/60',
  border: 'border-emerald-200',
  badgeBg: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  dot: 'bg-emerald-500',
  icon: <ShieldCheck size={16} className="text-emerald-600" />,
  titleColor: 'text-emerald-950',
  emoji: '🟢',
};

const STATE_THEMES = {
  clear: {
    bg: 'bg-emerald-50/60',
    border: 'border-emerald-200',
    badgeBg: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    dot: 'bg-emerald-500',
    icon: <ShieldCheck size={16} className="text-emerald-600" />,
    titleColor: 'text-emerald-950',
    emoji: '🟢',
  },
  caution: {
    bg: 'bg-amber-50/70',
    border: 'border-amber-300',
    badgeBg: 'bg-amber-100 text-amber-800 border-amber-300',
    dot: 'bg-amber-500',
    icon: <AlertTriangle size={16} className="text-amber-600" />,
    titleColor: 'text-amber-950',
    emoji: '🟡',
  },
  high: {
    bg: 'bg-rose-50/70',
    border: 'border-rose-300',
    badgeBg: 'bg-rose-100 text-rose-800 border-rose-300',
    dot: 'bg-rose-600',
    icon: <AlertCircle size={16} className="text-rose-600" />,
    titleColor: 'text-rose-950',
    emoji: '🔴',
  },
};

export default function MarineHazardsAlerts({ onShowOnMap, onHazardCode }: MarineHazardsAlertsProps) {
  const { selectedLocation } = useLocation();

  const [assessment, setAssessment] = useState<HazardAssessment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<string>('');

  const loadHazards = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchFastAPIHazards(
        selectedLocation.latitude,
        selectedLocation.longitude
      );
      setAssessment(data);
      // Notify parent of the hazard severity code for map layer coloring
      if (onHazardCode && data.overall_code) {
        const code = data.overall_code as 'clear' | 'caution' | 'high';
        onHazardCode(code);
      }
      setLastRefreshed(
        new Date().toLocaleTimeString('en-IN', {
          hour: '2-digit',
          minute: '2-digit',
          timeZone: 'Asia/Kolkata',
        }) + ' IST'
      );
    } catch (err) {
      console.error('[MarineHazardsAlerts] Fetch error:', err);
      setError('Unable to retrieve coastal hazard telemetry.');
    } finally {
      setLoading(false);
    }
  }, [selectedLocation.latitude, selectedLocation.longitude, onHazardCode]);

  useEffect(() => {
    loadHazards();
  }, [loadHazards]);

  // Safe stateTheme — fallback to 'clear' if code is unexpected
  const overallCode = assessment?.overall_code;
  const stateTheme =
    (overallCode && overallCode in STATE_THEMES
      ? STATE_THEMES[overallCode as keyof typeof STATE_THEMES]
      : null) ?? DEFAULT_STATE_THEME;

  const overallState = assessment?.overall_state || 'NO SIGNIFICANT HAZARDS';
  const activeCount = assessment?.active_conditions_count ?? 0;

  const getConditionIcon = (iconId: string) => {
    switch (iconId) {
      case 'waves':
        return <Waves size={15} className="text-blue-600" />;
      case 'wind':
        return <Wind size={15} className="text-cyan-600" />;
      case 'rain':
        return <CloudRain size={15} className="text-indigo-600" />;
      case 'lightning':
        return <Zap size={15} className="text-amber-500" />;
      case 'cyclone':
        return <Activity size={15} className="text-purple-600" />;
      default:
        return <AlertTriangle size={15} className="text-gray-500" />;
    }
  };

  // Left border accent color per severity
  const getSeverityBorderClass = (cond: HazardCondition): string => {
    if (cond.severity === 'high') return 'border-l-2 border-rose-400 bg-rose-50/40';
    if (cond.severity === 'caution') return 'border-l-2 border-amber-400 bg-amber-50/40';
    if (cond.severity === 'unavailable') return 'border-l-2 border-gray-200 bg-gray-50/30';
    return 'border-l-2 border-emerald-200 bg-emerald-50/20';
  };

  const getSeverityBadge = (cond: HazardCondition) => {
    if (cond.severity === 'unavailable') {
      return (
        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 border border-gray-200">
          Unavailable
        </span>
      );
    }
    if (cond.severity === 'high') {
      return (
        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-100 text-rose-800 border border-rose-300 animate-pulse">
          High Alert
        </span>
      );
    }
    if (cond.severity === 'caution') {
      return (
        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-300">
          Elevated
        </span>
      );
    }
    return (
      <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">
        Normal
      </span>
    );
  };

  return (
    <div
      id="orca-marine-hazards"
      className="bg-white rounded-xl border border-gray-200 overflow-hidden flex flex-col transition-all scroll-mt-4 shadow-sm"
    >
      {/* ── Header ── */}
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between bg-slate-50/50">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-teal-50 text-teal-700 border border-teal-200">
            <AlertTriangle size={15} />
          </div>
          <div>
            <h3 className="text-[13px] font-bold text-navy-900 leading-tight">
              Marine Hazards &amp; Alerts
            </h3>
            <p className="text-[10px] text-gray-500 font-medium flex items-center gap-1 mt-0.5">
              <MapPin size={10} className="text-teal-600" />
              <span className="font-semibold text-navy-800">{selectedLocation.name}</span>
              <span>•</span>
              <span className="font-mono text-gray-400">
                {selectedLocation.latitude.toFixed(2)}°N, {selectedLocation.longitude.toFixed(2)}°E
              </span>
            </p>
          </div>
        </div>

        <button
          onClick={loadHazards}
          disabled={loading}
          title="Refresh hazard assessment"
          className="p-1.5 text-gray-400 hover:text-navy-700 hover:bg-gray-100 rounded-lg transition-colors cursor-pointer disabled:opacity-50"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin text-teal-600' : ''} />
        </button>
      </div>

      {/* ── Loading Skeleton ── */}
      {loading && (
        <div className="p-4 space-y-3 animate-pulse">
          <div className="h-10 bg-gray-100 rounded-lg w-full" />
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-12 bg-gray-50 rounded-lg w-full" />
          ))}
        </div>
      )}

      {/* ── Error State ── */}
      {!loading && error && (
        <div className="p-4 text-center">
          <AlertCircle size={20} className="text-rose-400 mx-auto mb-2" />
          <p className="text-[11px] text-gray-500">{error}</p>
          <button
            onClick={loadHazards}
            className="mt-2 text-[11px] font-semibold text-teal-700 underline hover:no-underline cursor-pointer"
          >
            Retry
          </button>
        </div>
      )}

      {/* ── Main Content ── */}
      {!loading && !error && assessment && (
        <>
          {/* Overall State Banner */}
          <div className={`px-4 py-3 border-b ${stateTheme.bg} ${stateTheme.border} transition-colors`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className={`w-2.5 h-2.5 rounded-full ${stateTheme.dot} animate-pulse`} />
                <span
                  className={`text-[11px] font-bold tracking-wider uppercase px-2 py-0.5 rounded-md border ${stateTheme.badgeBg}`}
                >
                  {stateTheme.emoji}&nbsp;{overallState}
                </span>
              </div>
              <span className="text-[11px] font-semibold text-gray-600">
                {activeCount === 0
                  ? '0 conditions require attention'
                  : `${activeCount} condition${activeCount > 1 ? 's' : ''} require attention`}
              </span>
            </div>

            <p className="text-[11px] font-medium text-gray-700 mt-2 leading-relaxed">
              {assessment.headline}
            </p>
          </div>

          {/* Condition Rows */}
          <div className="p-3 divide-y divide-gray-100">
            {assessment.conditions.map((cond) => (
              <div
                key={cond.id}
                className={`py-2.5 px-2 rounded-lg transition-colors my-0.5 ${getSeverityBorderClass(cond)}`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-1 rounded bg-white shadow-xs border border-gray-100">
                      {getConditionIcon(cond.id)}
                    </div>
                    <div>
                      <h4 className="text-[11px] font-semibold text-navy-900 flex items-center gap-1.5">
                        {cond.name}
                      </h4>
                      <div className="flex items-center gap-1.5 mt-0.5 text-[10px] text-gray-500">
                        <span className="font-bold text-navy-800">{cond.value}</span>
                        {cond.peak_gusts && (
                          <span className="text-gray-400">
                            (Gusts: <span className="text-navy-700 font-semibold">{cond.peak_gusts}</span>)
                          </span>
                        )}
                        <span>•</span>
                        <span className="text-gray-400 font-mono text-[9px]">{cond.threshold}</span>
                      </div>
                    </div>
                  </div>

                  <div>{getSeverityBadge(cond)}</div>
                </div>

                {/* Factual Explainability Note */}
                <p className="text-[10px] text-gray-500 mt-1.5 pl-7 leading-relaxed">
                  {cond.explanation}
                </p>
              </div>
            ))}
          </div>

          {/* Footer */}
          <div className="px-4 py-2.5 bg-slate-50 border-t border-gray-100 flex items-center justify-between">
            <span className="text-[9px] text-gray-400 font-medium">
              Last updated: {lastRefreshed || 'Just now'}
            </span>

            {onShowOnMap && (
              <button
                onClick={onShowOnMap}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-bold text-teal-700 bg-teal-50 border border-teal-200 rounded-lg hover:bg-teal-100 transition-colors cursor-pointer"
              >
                <Layers size={11} className="text-teal-600" />
                Show Hazards on Map
              </button>
            )}
          </div>

          {/* Official Advisory Disclaimer */}
          <div className="px-4 py-2 bg-gray-50/70 border-t border-gray-100">
            <p className="text-[9px] text-gray-400 leading-normal flex items-start gap-1.5">
              <Info size={11} className="text-gray-400 mt-0.5 flex-shrink-0" />
              <span>
                ORCA provides AI-assisted decision support based on available environmental data.
                Always check official marine weather warnings and local authority advisories before venturing to sea.
              </span>
            </p>
          </div>
        </>
      )}
    </div>
  );
}
