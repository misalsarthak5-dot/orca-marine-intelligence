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
import { getMarineConditions, getLiveOrcaMarineData, mapToMarineConditions } from '@/services/marineDataService';
import { MarineCondition } from '@/types';

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
  const [conditions, setConditions] = useState<MarineCondition[]>(getMarineConditions());
  const [isLive, setIsLive] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const { t } = useTranslation();

  useEffect(() => {
    let isMounted = true;

    async function loadLiveData() {
      try {
        setIsLoading(true);
        const liveData = await getLiveOrcaMarineData();
        if (isMounted) {
          if (liveData.isLive) {
            setConditions(mapToMarineConditions(liveData));
            setIsLive(true);
          } else {
            // Keep fallback conditions
            setIsLive(false);
          }
        }
      } catch (err) {
        console.warn('Unable to sync live Open-Meteo data, retaining fallback values:', err);
        if (isMounted) {
          setIsLive(false);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadLiveData();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="flex flex-col gap-1.5">
      {/* Live Data Feed Bar */}
      <div className="flex items-center justify-between px-1 text-[11px]">
        <div className="flex items-center gap-2">
          <span className="font-bold text-navy-900 tracking-wide text-[11px] uppercase">
            Live Marine Environment
          </span>
          {isLive ? (
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-teal-50 border border-teal-200 text-[10px] font-semibold text-teal-700 shadow-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-teal-500 animate-pulse" />
              Connected: Open-Meteo Live API
            </span>
          ) : isLoading ? (
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-gray-100 border border-gray-200 text-[10px] text-gray-500">
              <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-pulse" />
              Syncing Open-Meteo...
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-amber-50 border border-amber-200 text-[10px] font-medium text-amber-700">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
              Demo Mock Baseline
            </span>
          )}
        </div>
        <span className="text-[10px] text-gray-400 font-mono hidden sm:inline-block">
          Mumbai Coast • 19.0760°N, 72.8777°E
        </span>
      </div>

      {/* Conditions Horizontal Cards */}
      <div className="flex gap-3 overflow-x-auto pb-1 scrollbar-thin">
        {conditions.map((c) => (
          <div
            key={c.id}
            className="flex-shrink-0 flex-1 min-w-[155px] bg-white rounded-xl border border-gray-200 p-3.5 hover:shadow-md hover:border-gray-300 transition-all duration-200"
          >
            <div className="flex items-start justify-between mb-2">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${iconBgMap[c.statusColor]}`}>
                {iconMap[c.icon]}
              </div>
              {c.source ? (
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
        ))}
      </div>
    </div>
  );
}
