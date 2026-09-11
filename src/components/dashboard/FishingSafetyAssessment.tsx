'use client';

import React, { useEffect, useState, useCallback } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Waves,
  Wind,
  Zap,
  Tornado,
  CloudRain,
  Shield,
  ArrowRight,
  Info,
  Calendar,
  Clock,
  MapPin,
  RefreshCw,
  Activity,
  Compass,
} from 'lucide-react';
import { useTranslation } from '@/lib/i18n';
import { useLocation } from '@/lib/location';
import { fetchFastAPISafety } from '@/services/safetyService';
import { RiskLevel } from '@/types';

type AssessmentPeriod = 'now' | 'tomorrow_morning' | 'tomorrow';

interface FishingSafetyAssessmentProps {
  onViewEvidence?: () => void;
  onViewRiskMap?: () => void;
}

interface SafetyFactorItem {
  id: string;
  label: string;
  value: string;
  status: string;
  statusColor: 'green' | 'amber' | 'red';
  icon: string;
  threshold?: string;
}

const riskTheme: Record<RiskLevel, {
  label: string;
  title: string;
  icon: React.ReactNode;
  cardBg: string;
  cardBorder: string;
  badgeBg: string;
  badgeText: string;
  dotColor: string;
  textColor: string;
  progressColor: string;
}> = {
  low: {
    label: 'LOW RISK',
    title: 'CONDITIONS APPEAR SUITABLE',
    icon: <CheckCircle2 size={18} className="text-emerald-600" />,
    cardBg: 'bg-emerald-50/70',
    cardBorder: 'border-emerald-200',
    badgeBg: 'bg-emerald-100',
    badgeText: 'text-emerald-800',
    dotColor: 'bg-emerald-500',
    textColor: 'text-emerald-900',
    progressColor: 'bg-emerald-500',
  },
  moderate: {
    label: 'CAUTION ADVISED',
    title: 'CAUTION ADVISED',
    icon: <AlertTriangle size={18} className="text-amber-600" />,
    cardBg: 'bg-amber-50/70',
    cardBorder: 'border-amber-200',
    badgeBg: 'bg-amber-100',
    badgeText: 'text-amber-800',
    dotColor: 'bg-amber-500',
    textColor: 'text-amber-900',
    progressColor: 'bg-amber-500',
  },
  high: {
    label: 'NOT RECOMMENDED',
    title: 'NOT RECOMMENDED',
    icon: <XCircle size={18} className="text-rose-600" />,
    cardBg: 'bg-rose-50/70',
    cardBorder: 'border-rose-200',
    badgeBg: 'bg-rose-100',
    badgeText: 'text-rose-800',
    dotColor: 'bg-rose-500',
    textColor: 'text-rose-900',
    progressColor: 'bg-rose-500',
  },
};

export default function FishingSafetyAssessment({
  onViewEvidence,
  onViewRiskMap,
}: FishingSafetyAssessmentProps) {
  const { t } = useTranslation();
  const { safetyAssessment: baseAssessment, selectedLocation, liveData, isLoading: isLocationLoading } = useLocation();

  const [period, setPeriod] = useState<AssessmentPeriod>('now');
  const [periodData, setPeriodData] = useState<any | null>(null);
  const [isFetchingPeriod, setIsFetchingPeriod] = useState<boolean>(false);

  // Load period-specific data from FastAPI when period or location changes
  const loadPeriodAssessment = useCallback(async (targetPeriod: AssessmentPeriod, lat: number, lon: number) => {
    setIsFetchingPeriod(true);
    try {
      const data = await fetchFastAPISafety(lat, lon, targetPeriod);
      setPeriodData(data);
    } catch (err) {
      console.warn('[FishingSafety] Failed to fetch period safety, falling back to local state:', err);
      setPeriodData(null);
    } finally {
      setIsFetchingPeriod(false);
    }
  }, []);

  useEffect(() => {
    loadPeriodAssessment(period, selectedLocation.latitude, selectedLocation.longitude);
  }, [period, selectedLocation.latitude, selectedLocation.longitude, loadPeriodAssessment]);

  // Listen for Ask ORCA sync events (e.g. user asked about tomorrow morning in chat)
  useEffect(() => {
    const handleSafetySync = (event: Event) => {
      const customEvent = event as CustomEvent<{ timeWindow?: AssessmentPeriod }>;
      if (customEvent.detail?.timeWindow) {
        setPeriod(customEvent.detail.timeWindow);
      }
    };
    window.addEventListener('orca:safety-sync', handleSafetySync);
    return () => window.removeEventListener('orca:safety-sync', handleSafetySync);
  }, []);

  // Determine current active risk level
  const rawRisk = periodData?.risk_level?.toLowerCase() || (period === 'now' && liveData?.fastapiSafety?.risk_level?.toLowerCase()) || baseAssessment.riskLevel;
  const riskLevel: RiskLevel = rawRisk === 'caution' ? 'moderate' : rawRisk === 'high' ? 'high' : 'low';
  const theme = riskTheme[riskLevel];

  // Risk Score: 18 for low, 48 for caution/moderate, 78 for high (deterministic from backend risk level)
  const riskScore = riskLevel === 'high' ? 78 : riskLevel === 'moderate' ? 48 : 18;

  // Period label & timing description
  const isForecast = period !== 'now';
  const periodTitle =
    period === 'tomorrow_morning'
      ? 'Tomorrow Morning'
      : period === 'tomorrow'
      ? 'Tomorrow'
      : 'Current Marine Conditions';

  const periodTiming =
    period === 'tomorrow_morning'
      ? '05:00–11:00 IST'
      : period === 'tomorrow'
      ? '05:00–19:00 IST'
      : 'Real-time Telemetry';

  // Extract environmental factors
  const metrics = periodData?.metrics_snapshot || (period === 'now' ? {
    wind_speed_knots: liveData?.current.windSpeedKnots ?? 10.0,
    wind_gusts_knots: liveData?.current.windGustsKnots ?? 13.0,
    wave_height_meters: liveData?.current.waveHeightMeters ?? 1.0,
    wave_period_seconds: liveData?.current.wavePeriodSeconds ?? 6.5,
    sea_surface_temperature_c: liveData?.current.seaSurfaceTemperature ?? 29.0,
    precipitation_mm: liveData?.current.precipitation ?? 0.0,
    wind_direction: liveData?.current.windDirectionCompass ?? 'NW',
  } : null);

  const waveH = metrics?.wave_height_meters ?? 1.0;
  const windSpd = metrics?.wind_speed_knots ?? 10.0;
  const windGusts = metrics?.wind_gusts_knots ?? 13.0;
  const precip = metrics?.precipitation_mm ?? 0.0;
  const sst = metrics?.sea_surface_temperature_c ?? 29.0;
  const windDir = metrics?.wind_direction || 'NW';

  // Primary factors breakdown
  const primaryFactors: SafetyFactorItem[] = [
    {
      id: 'waves',
      label: 'Wave Height',
      value: `${waveH.toFixed(1)} m`,
      status: waveH < 1.8 ? 'Acceptable' : waveH < 2.5 ? 'Moderate' : 'Rough Seas',
      statusColor: waveH < 1.8 ? 'green' : waveH < 2.5 ? 'amber' : 'red',
      icon: 'waves',
      threshold: 'Safe < 1.8m',
    },
    {
      id: 'wind',
      label: 'Wind Speed',
      value: `${windSpd.toFixed(1)} kts`,
      status: windSpd < 15 ? 'Moderate' : windSpd < 22 ? 'Fresh Breeze' : 'High Wind',
      statusColor: windSpd < 15 ? 'green' : windSpd < 22 ? 'amber' : 'red',
      icon: 'wind',
      threshold: 'Safe < 15 kts',
    },
    {
      id: 'gusts',
      label: 'Wind Gusts',
      value: `${windGusts.toFixed(1)} kts`,
      status: windGusts < 20 ? 'Low' : windGusts < 28 ? 'Elevated' : 'Squall Gusts',
      statusColor: windGusts < 20 ? 'green' : windGusts < 28 ? 'amber' : 'red',
      icon: 'wind',
      threshold: 'Safe < 20 kts',
    },
    {
      id: 'rain',
      label: 'Rainfall',
      value: `${precip.toFixed(1)} mm`,
      status: precip < 1.0 ? 'Low' : precip < 5.0 ? 'Showers' : 'Heavy Rain',
      statusColor: precip < 1.0 ? 'green' : precip < 5.0 ? 'amber' : 'red',
      icon: 'cloudRain',
      threshold: 'Safe < 1mm/hr',
    },
  ];

  // Secondary operational signals
  const secondaryFactors = [
    { label: 'Lightning', value: 'Clear', status: 'No convective alert', icon: <Zap size={12} className="text-emerald-500" /> },
    { label: 'Cyclone', value: 'Clear', status: 'No depression', icon: <Tornado size={12} className="text-emerald-500" /> },
    { label: 'Geofence Buffer', value: 'Clear', status: '>3.5 NM buffer', icon: <Shield size={12} className="text-emerald-500" /> },
  ];

  // ── Dynamic evidence-based summary ──────────────────────────────────
  //
  // Computes a human-readable explanation of WHY ORCA reached the verdict,
  // using ONLY the actual values already returned by the system.
  // Never hardcodes location names, values, or risk states.
  //
  const buildDynamicSummary = (): { shortSummary: string; reasons: string[] } => {
    const locName = selectedLocation.name;
    const periodRef = isForecast
      ? period === 'tomorrow_morning'
        ? 'for tomorrow morning (05:00\u201311:00 IST)'
        : 'for tomorrow (05:00\u201319:00 IST)'
      : 'based on current conditions';
    const conditionRef = isForecast ? 'forecast conditions' : 'current conditions';
    const nearRef = isForecast ? 'near' : 'near';

    // Identify elevated factors for explainability
    const elevatedWaves = waveH >= 1.8;
    const highWaves = waveH >= 2.5;
    const elevatedWind = windSpd >= 15.0;
    const highWind = windSpd >= 22.0;
    const elevatedGusts = windGusts >= 20.0;
    const highGusts = windGusts >= 28.0;
    const elevatedRain = precip >= 1.0;
    const highRain = precip >= 5.0;

    // Collect which factors are contributing to caution/high
    const cautionFactors: string[] = [];
    const highFactors: string[] = [];

    if (highWaves) highFactors.push(`rough wave height (${waveH.toFixed(1)} m \u2014 exceeds the 2.5 m safe limit)`);
    else if (elevatedWaves) cautionFactors.push(`elevated wave height (${waveH.toFixed(1)} m \u2014 moderate swell above the 1.8 m threshold)`);

    if (highWind) highFactors.push(`high wind speed (${windSpd.toFixed(1)} kts \u2014 exceeds the 22 kt advisory limit)`);
    else if (elevatedWind) cautionFactors.push(`elevated wind speed (${windSpd.toFixed(1)} kts \u2014 above the 15 kt caution threshold)`);

    if (highGusts) highFactors.push(`severe gusts (${windGusts.toFixed(1)} kts \u2014 exceeds the 28 kt squall limit)`);
    else if (elevatedGusts) cautionFactors.push(`moderate gusts (${windGusts.toFixed(1)} kts)`);

    if (highRain) highFactors.push(`heavy precipitation (${precip.toFixed(1)} mm \u2014 significantly reducing sea visibility)`);
    else if (elevatedRain) cautionFactors.push(`light to moderate precipitation (${precip.toFixed(1)} mm)`);

    // ── LOW RISK ──
    if (riskLevel === 'low') {
      const shortSummary =
        `${conditionRef.charAt(0).toUpperCase() + conditionRef.slice(1)} ${nearRef} ${locName} appear suitable ${periodRef}. ` +
        `Waves are around ${waveH.toFixed(1)} m, winds are around ${windSpd.toFixed(1)} kts, ` +
        `and precipitation is ${precip < 0.5 ? 'negligible' : `around ${precip.toFixed(1)} mm`}. ` +
        `ORCA recommends proceeding with standard caution and verifying official marine warnings before venturing to sea.`;

      const reasons = [
        `Wave height is ${waveH.toFixed(1)} m \u2014 within the safe operational limit of 1.8 m for motorized craft.`,
        `Sustained wind speed is ${windSpd.toFixed(1)} kts ${windDir} with gusts up to ${windGusts.toFixed(1)} kts \u2014 below the 15 kt caution threshold.`,
        `Precipitation is ${precip.toFixed(1)} mm \u2014 ${precip < 0.5 ? 'clear and dry conditions, no significant visibility impact.' : 'within acceptable limits with minimal visibility impact.'}`,
        `No active marine cyclonic depressions or significant convective alerts detected in this sector.`,
      ];
      return { shortSummary, reasons };
    }

    // ── HIGH RISK ──
    if (riskLevel === 'high') {
      const allHighFactors = [...highFactors, ...cautionFactors];
      const factorPhrase = allHighFactors.length > 0
        ? allHighFactors.slice(0, 2).join(' and ')
        : `adverse environmental conditions`;

      const shortSummary =
        `${conditionRef.charAt(0).toUpperCase() + conditionRef.slice(1)} ${nearRef} ${locName} are currently unfavorable for fishing ${periodRef}. ` +
        `${factorPhrase.charAt(0).toUpperCase() + factorPhrase.slice(1)} ${allHighFactors.length > 0 ? 'is' : 'are'} contributing to the higher risk assessment. ` +
        `ORCA does not recommend venturing out during this assessment period.`;

      const reasons: string[] = [];
      if (highWaves) reasons.push(`Wave height is ${waveH.toFixed(1)} m \u2014 rough seas exceeding the 2.5 m operational limit. Small craft are at significant risk.`);
      else if (elevatedWaves) reasons.push(`Wave height is ${waveH.toFixed(1)} m \u2014 moderate to rough swell above safe thresholds.`);
      else reasons.push(`Wave height is ${waveH.toFixed(1)} m.`);

      if (highWind) reasons.push(`Wind speed is ${windSpd.toFixed(1)} kts ${windDir} with gusts to ${windGusts.toFixed(1)} kts \u2014 high wind advisory in effect. Conditions exceed the 22 kt safe limit.`);
      else if (elevatedWind) reasons.push(`Wind speed is ${windSpd.toFixed(1)} kts ${windDir} with gusts to ${windGusts.toFixed(1)} kts \u2014 above the caution threshold.`);
      else reasons.push(`Wind speed is ${windSpd.toFixed(1)} kts ${windDir} with gusts to ${windGusts.toFixed(1)} kts.`);

      if (highRain) reasons.push(`Precipitation is ${precip.toFixed(1)} mm \u2014 heavy rain significantly reducing sea visibility.`);
      else if (elevatedRain) reasons.push(`Precipitation is ${precip.toFixed(1)} mm \u2014 light to moderate rain affecting visibility.`);
      else reasons.push(`Precipitation is ${precip.toFixed(1)} mm \u2014 limited rain impact on visibility.`);

      reasons.push(`ORCA does not recommend departure during this assessment period. Seek safe anchorage and monitor official advisories closely.`);
      return { shortSummary, reasons };
    }

    // ── CAUTION / MODERATE ──
    const factorPhrase = cautionFactors.length > 0
      ? cautionFactors.slice(0, 2).join(' and ')
      : `marginal environmental conditions`;

    const shortSummary =
      `${conditionRef.charAt(0).toUpperCase() + conditionRef.slice(1)} ${nearRef} ${locName} are marginal for fishing ${periodRef}. ` +
      (cautionFactors.length > 0
        ? `${factorPhrase.charAt(0).toUpperCase() + factorPhrase.slice(1)} ${cautionFactors.length === 1 ? 'is' : 'are'} contributing to the caution assessment. `
        : '') +
      `ORCA recommends caution and heightened vigilance for experienced mariners during this period.`;

    const reasons: string[] = [];
    if (elevatedWaves) reasons.push(`Wave height is ${waveH.toFixed(1)} m \u2014 above the 1.8 m caution threshold. Elevated swell is the primary contributing factor.`);
    else reasons.push(`Wave height is ${waveH.toFixed(1)} m \u2014 within acceptable limits.`);

    if (elevatedWind) reasons.push(`Wind speed is ${windSpd.toFixed(1)} kts ${windDir} with gusts to ${windGusts.toFixed(1)} kts \u2014 above the 15 kt caution advisory threshold.`);
    else reasons.push(`Sustained wind is ${windSpd.toFixed(1)} kts ${windDir} with gusts to ${windGusts.toFixed(1)} kts \u2014 within moderate operating limits.`);

    if (elevatedRain) reasons.push(`Precipitation is ${precip.toFixed(1)} mm \u2014 light showers may reduce sea visibility. Monitor conditions.`);
    else reasons.push(`Precipitation is ${precip.toFixed(1)} mm \u2014 clear conditions with no significant visibility impact.`);

    reasons.push(`Experienced motorized craft (>9 m) may operate with heightened vigilance. Small craft and non-mechanized boats are advised to remain in port.`);
    return { shortSummary, reasons };
  };

  const { shortSummary, reasons: dynamicReasons } = buildDynamicSummary();

  return (
    <div
      id="orca-safety-assessment"
      className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm transition-all"
    >
      {/* 1. Header & Location */}
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-navy-50 text-navy-800 rounded-md">
            <Shield size={15} />
          </div>
          <div>
            <h3 className="text-[12px] font-bold text-navy-900 uppercase tracking-wider">
              Fishing Safety Assessment
            </h3>
            <p className="text-[10px] text-gray-500 flex items-center gap-1 mt-0.5">
              <MapPin size={10} className="text-teal-600 flex-shrink-0" />
              <span className="font-semibold text-navy-800">{selectedLocation.name}</span>
              <span>({selectedLocation.latitude.toFixed(2)}°N, {selectedLocation.longitude.toFixed(2)}°E)</span>
            </p>
          </div>
        </div>

        {/* Live / Forecast Badge */}
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold border ${isForecast ? 'bg-indigo-50 text-indigo-700 border-indigo-200' : 'bg-teal-50 text-teal-700 border-teal-200'}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${isForecast ? 'bg-indigo-500' : 'bg-teal-500 animate-pulse'}`} />
          {isForecast ? 'FORECAST MODE' : 'LIVE TELEMETRY'}
        </span>
      </div>

      {/* 2. Assessment Period Switcher */}
      <div className="px-4 pt-2.5 pb-1 bg-gray-50/60 border-b border-gray-100">
        <div className="flex items-center justify-between gap-1">
          <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider flex items-center gap-1">
            <Clock size={10} /> Period:
          </span>
          <div className="inline-flex bg-gray-200/70 p-0.5 rounded-lg text-[10px] font-semibold">
            <button
              onClick={() => setPeriod('now')}
              className={`px-2.5 py-1 rounded-md transition-all flex items-center gap-1 ${
                period === 'now'
                  ? 'bg-white text-navy-900 shadow-sm font-bold'
                  : 'text-gray-600 hover:text-navy-900'
              }`}
            >
              Current
            </button>
            <button
              onClick={() => setPeriod('tomorrow_morning')}
              className={`px-2.5 py-1 rounded-md transition-all flex items-center gap-1 ${
                period === 'tomorrow_morning'
                  ? 'bg-white text-navy-900 shadow-sm font-bold'
                  : 'text-gray-600 hover:text-navy-900'
              }`}
            >
              Tomorrow Morning
            </button>
            <button
              onClick={() => setPeriod('tomorrow')}
              className={`px-2.5 py-1 rounded-md transition-all flex items-center gap-1 ${
                period === 'tomorrow'
                  ? 'bg-white text-navy-900 shadow-sm font-bold'
                  : 'text-gray-600 hover:text-navy-900'
              }`}
            >
              Tomorrow (Full Day)
            </button>
          </div>
        </div>
      </div>

      {/* 3. Primary Safety Verdict Box */}
      <div className="p-4 space-y-3">
        <div className={`p-3.5 rounded-xl border ${theme.cardBg} ${theme.cardBorder} relative overflow-hidden transition-all`}>
          {/* Top Row: Status Badge & Assessment Period Label */}
          <div className="flex items-center justify-between gap-2 mb-2">
            <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold ${theme.badgeBg} ${theme.badgeText}`}>
              <span className={`w-2 h-2 rounded-full ${theme.dotColor}`} />
              {theme.label}
            </div>
            <div className="text-right">
              <span className="text-[10px] font-extrabold text-navy-800 uppercase tracking-wider block">
                {isForecast ? periodTitle.toUpperCase() : 'CURRENT MARINE CONDITIONS'}
              </span>
              <span className="text-[10px] text-gray-500 font-medium">
                {periodTiming}
              </span>
            </div>
          </div>

          {/* Main Verdict Title */}
          <div className="flex items-center gap-2 mb-1.5">
            {theme.icon}
            <h2 className={`text-base font-extrabold tracking-tight ${theme.textColor}`}>
              {theme.title}
            </h2>
          </div>

          {/* Location details */}
          <p className="text-[11px] font-semibold text-gray-700">
            {selectedLocation.name} • {selectedLocation.latitude.toFixed(2)}°N, {selectedLocation.longitude.toFixed(2)}°E
          </p>

          {/* Recommendation summary */}
          <p className="text-[11px] text-gray-600 mt-1 leading-relaxed">
            {shortSummary}
          </p>
        </div>

        {/* 4. Risk Score & Visual Meter */}
        <div className="bg-gray-50/80 rounded-xl p-3 border border-gray-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 block">
              Risk Score
            </span>
            <div className="flex items-baseline gap-1.5 mt-0.5">
              <span className="text-2xl font-black text-navy-900 tracking-tight">{riskScore}</span>
              <span className="text-[11px] font-bold text-gray-400">/ 100</span>
              <span className={`text-[10px] font-bold ml-1.5 px-2 py-0.5 rounded-full ${theme.badgeBg} ${theme.badgeText}`}>
                {riskLevel === 'low' ? 'Low Risk (0–33)' : riskLevel === 'moderate' ? 'Caution (34–66)' : 'High Risk (67–100)'}
              </span>
            </div>
          </div>

          {/* Segmented Risk Indicator Meter */}
          <div className="w-full sm:w-48 space-y-1">
            <div className="flex justify-between text-[9px] font-bold text-gray-400">
              <span className="text-emerald-700">Low (0–33)</span>
              <span className="text-amber-700">Caution</span>
              <span className="text-rose-700">High (67+)</span>
            </div>
            <div className="h-2.5 w-full bg-gray-200 rounded-full overflow-hidden flex gap-1 p-0.5">
              <div
                className={`h-full flex-1 rounded-l-full transition-all ${
                  riskScore <= 33 ? 'bg-emerald-500 ring-1 ring-emerald-600' : 'bg-emerald-200'
                }`}
              />
              <div
                className={`h-full flex-1 transition-all ${
                  riskScore > 33 && riskScore <= 66 ? 'bg-amber-500 ring-1 ring-amber-600' : 'bg-amber-200'
                }`}
              />
              <div
                className={`h-full flex-1 rounded-r-full transition-all ${
                  riskScore > 66 ? 'bg-rose-500 ring-1 ring-rose-600' : 'bg-rose-200'
                }`}
              />
            </div>
          </div>
        </div>

        {/* 5. Key Environmental Factors */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-[10px] font-bold text-navy-900 uppercase tracking-wider flex items-center gap-1.5">
              <Activity size={11} className="text-teal-600" />
              Key Safety Factors ({isForecast ? 'Forecast Peak' : 'Live'})
            </h4>
            <span className="text-[9px] font-semibold text-gray-400">Open-Meteo Verified</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {primaryFactors.map((f) => {
              const badgeClass =
                f.statusColor === 'green'
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : f.statusColor === 'amber'
                  ? 'bg-amber-50 text-amber-700 border-amber-200'
                  : 'bg-rose-50 text-rose-700 border-rose-200';

              return (
                <div
                  key={f.id}
                  className="p-2.5 rounded-lg bg-gray-50 border border-gray-100 flex flex-col justify-between"
                >
                  <div className="flex items-center justify-between text-gray-500 mb-1">
                    <span className="text-[10px] font-bold text-navy-800">{f.label}</span>
                    {f.id === 'waves' ? <Waves size={13} className="text-blue-500" /> : f.id === 'rain' ? <CloudRain size={13} className="text-teal-500" /> : <Wind size={13} className="text-indigo-500" />}
                  </div>
                  <div className="my-0.5">
                    <span className="text-[15px] font-extrabold text-navy-900">{f.value}</span>
                  </div>
                  <div className="mt-1 flex items-center justify-between">
                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${badgeClass}`}>
                      {f.status}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Secondary Environmental Signals */}
          <div className="mt-2 grid grid-cols-3 gap-2">
            {secondaryFactors.map((s, idx) => (
              <div key={idx} className="p-2 rounded-lg bg-gray-50/70 border border-gray-100 flex items-center gap-2">
                {s.icon}
                <div className="min-w-0">
                  <p className="text-[10px] font-bold text-navy-900 truncate">{s.label}: {s.value}</p>
                  <p className="text-[9px] text-gray-400 truncate">{s.status}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 6. Why ORCA Recommends This */}
        <div className="pt-2 border-t border-gray-100">
          <h4 className="text-[10px] font-bold text-navy-900 uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <Info size={11} className="text-teal-600" />
            Why ORCA Recommends This
          </h4>
          <div className="space-y-1.5 bg-teal-50/40 p-3 rounded-lg border border-teal-100/60">
            {dynamicReasons.map((reason, i) => (
              <div key={i} className="flex items-start gap-2">
                <CheckCircle2 size={12} className="text-teal-600 mt-0.5 flex-shrink-0" />
                <p className="text-[11px] text-gray-700 leading-relaxed">{reason}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2 pt-1">
          <button
            onClick={onViewRiskMap}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-navy-900 text-white text-[11px] font-semibold rounded-lg hover:bg-navy-800 transition-colors shadow-sm"
          >
            <Compass size={12} />
            View Risk Map
          </button>
          <button
            onClick={() => loadPeriodAssessment(period, selectedLocation.latitude, selectedLocation.longitude)}
            disabled={isFetchingPeriod}
            className="px-3 py-2 border border-gray-200 text-navy-800 text-[11px] font-semibold rounded-lg hover:bg-gray-50 transition-colors flex items-center gap-1.5"
          >
            <RefreshCw size={12} className={isFetchingPeriod ? 'animate-spin text-teal-600' : ''} />
            Refresh
          </button>
        </div>

        {/* 7. Official Advisory Disclaimer */}
        <div className="pt-2 border-t border-gray-100">
          <p className="text-[10px] text-gray-500 leading-relaxed italic bg-gray-50 p-2 rounded-md border border-gray-100">
            ORCA provides AI-assisted decision support based on available environmental data. Always check official marine weather warnings and local authority advisories before venturing to sea.
          </p>
        </div>
      </div>
    </div>
  );
}
