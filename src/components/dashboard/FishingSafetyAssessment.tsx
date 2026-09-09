'use client';

import React, { useEffect, useState } from 'react';
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
} from 'lucide-react';
import { useTranslation } from '@/lib/i18n';
import { getSafetyAssessment } from '@/services/safetyService';
import { getLiveOrcaMarineData } from '@/services/orcaDataService';
import { evidenceSources } from '@/data/mockAlerts';
import { RiskLevel, SafetyAssessment } from '@/types';

const factorIconMap: Record<string, React.ReactNode> = {
  waves: <Waves size={14} />,
  wind: <Wind size={14} />,
  zap: <Zap size={14} />,
  tornado: <Tornado size={14} />,
  cloudRain: <CloudRain size={14} />,
  shield: <Shield size={14} />,
};

const riskConfig: Record<RiskLevel, {
  icon: React.ReactNode;
  bgColor: string;
  borderColor: string;
  textColor: string;
  dotColor: string;
  badgeBg: string;
  badgeText: string;
  bannerBg: string;
  bannerBorder: string;
}> = {
  low: {
    icon: <CheckCircle2 size={18} />,
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    textColor: 'text-green-700',
    dotColor: 'bg-green-500',
    badgeBg: 'bg-green-100',
    badgeText: 'text-green-700',
    bannerBg: 'bg-teal-50',
    bannerBorder: 'border-teal-200',
  },
  moderate: {
    icon: <AlertTriangle size={18} />,
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
    textColor: 'text-amber-700',
    dotColor: 'bg-amber-500',
    badgeBg: 'bg-amber-100',
    badgeText: 'text-amber-700',
    bannerBg: 'bg-amber-50',
    bannerBorder: 'border-amber-200',
  },
  high: {
    icon: <XCircle size={18} />,
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    textColor: 'text-red-700',
    dotColor: 'bg-red-500',
    badgeBg: 'bg-red-100',
    badgeText: 'text-red-700',
    bannerBg: 'bg-red-50',
    bannerBorder: 'border-red-200',
  },
};

const factorStatusColor: Record<string, string> = {
  green: 'text-green-600',
  amber: 'text-amber-600',
  red: 'text-red-600',
};

interface FishingSafetyAssessmentProps {
  onViewEvidence?: () => void;
  onViewRiskMap?: () => void;
}

export default function FishingSafetyAssessment({
  onViewEvidence,
  onViewRiskMap,
}: FishingSafetyAssessmentProps) {
  const [assessment, setAssessment] = useState<SafetyAssessment>(getSafetyAssessment());
  const { t } = useTranslation();

  useEffect(() => {
    let isMounted = true;

    async function syncLiveFactors() {
      try {
        const liveData = await getLiveOrcaMarineData();
        if (isMounted && liveData.isLive) {
          const c = liveData.current;
          setAssessment((prev) => ({
            ...prev,
            factors: prev.factors.map((f) => {
              if (f.id === 'waves') {
                return {
                  ...f,
                  value: `${c.waveHeightMeters.toFixed(1)} m — ${c.waveHeightMeters < 2.0 ? 'Acceptable' : 'Elevated'}`,
                  status: `Live (Swell ${c.swellWaveHeightMeters.toFixed(1)}m)`,
                  statusColor: c.waveHeightMeters < 2.0 ? 'green' : 'amber',
                };
              }
              if (f.id === 'wind') {
                return {
                  ...f,
                  value: `${c.windSpeedKnots.toFixed(1)} kt ${c.windDirectionCompass} — ${c.windSpeedKnots < 18 ? 'Moderate' : 'Caution'}`,
                  status: `Live (Gusts ${c.windGustsKnots.toFixed(0)} kt)`,
                  statusColor: c.windSpeedKnots < 18 ? 'green' : 'amber',
                };
              }
              if (f.id === 'rain') {
                return {
                  ...f,
                  value: `${c.precipitation.toFixed(1)} mm — ${c.precipitation < 1 ? 'Clear' : 'Showers'}`,
                  status: `Humidity ${c.humidity}%`,
                  statusColor: 'green',
                };
              }
              return f;
            }),
          }));
        }
      } catch {
        // Retain baseline factors on error
      }
    }

    syncLiveFactors();

    return () => {
      isMounted = false;
    };
  }, []);

  const config = riskConfig[assessment.riskLevel];

  const riskLabel =
    assessment.riskLevel === 'low'
      ? t('safety_lowRisk')
      : assessment.riskLevel === 'moderate'
      ? t('safety_moderateRisk')
      : t('safety_highRisk');

  const conditionLabel =
    assessment.riskLevel === 'low'
      ? t('safety_conditionsSuitable')
      : assessment.riskLevel === 'moderate'
      ? t('safety_conditionsCaution')
      : t('safety_conditionsNotRecommended');

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <h3 className="text-[11px] font-bold text-navy-900 uppercase tracking-wider">
          {t('safety_title')}
        </h3>
        <div className={`flex items-center gap-1.5 ${config.badgeBg} ${config.badgeText} px-2.5 py-1 rounded-full text-[11px] font-bold`}>
          <span className={`w-2 h-2 rounded-full ${config.dotColor}`} />
          {riskLabel}
        </div>
      </div>

      {/* Verdict Banner */}
      <div className={`mx-3 mt-3 px-3 py-2.5 rounded-lg border ${config.bannerBg} ${config.bannerBorder}`}>
        <p className={`text-[10px] font-bold uppercase tracking-wider ${config.textColor} mb-1`}>
          {assessment.verdictTitle}
        </p>
        <p className="text-[12px] text-navy-800 leading-relaxed">
          {assessment.description}
        </p>
      </div>

      {/* Quick Factor Breakdown */}
      <div className="px-4 pt-3 pb-1">
        <h4 className="text-[10px] font-bold text-navy-800 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
          <Info size={11} className="text-gray-400" />
          {t('safety_quickFactors')}
        </h4>
        <div className="grid grid-cols-2 gap-2">
          {assessment.factors.map((factor) => (
            <div
              key={factor.id}
              className="flex items-start gap-2 p-2 rounded-lg bg-gray-50 border border-gray-100"
            >
              <span className={factorStatusColor[factor.statusColor]}>
                {factorIconMap[factor.icon]}
              </span>
              <div className="min-w-0">
                <p className="text-[11px] font-semibold text-navy-900">{t(factor.label as keyof typeof t)}</p>
                <p className={`text-[10px] font-medium ${factorStatusColor[factor.statusColor]}`}>
                  {factor.value}
                </p>
                <p className="text-[9px] text-gray-400 mt-0.5">{factor.status}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* WHY section */}
      <div className="px-4 pt-3 pb-2">
        <h4 className="text-[10px] font-bold text-navy-800 uppercase tracking-wider mb-2">
          {t('safety_whyTitle')}
        </h4>
        <div className="space-y-1.5">
          {assessment.reasoning.map((reason, i) => (
            <div key={i} className="flex items-start gap-2">
              <CheckCircle2 size={12} className="text-teal-500 mt-0.5 flex-shrink-0" />
              <p className="text-[11px] text-gray-600 leading-relaxed">{reason}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Evidence */}
      <div className="px-4 pt-2 pb-3">
        <h4 className="text-[10px] font-bold text-navy-800 uppercase tracking-wider mb-2">
          {t('safety_verifiedEvidence')}
        </h4>
        <div className="flex flex-wrap gap-1.5">
          {evidenceSources.slice(0, 4).map((source) => (
            <span
              key={source.id}
              className="inline-flex items-center gap-1 px-2 py-1 bg-teal-50 text-teal-700 text-[10px] font-medium rounded-md border border-teal-100"
            >
              {source.name}
            </span>
          ))}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="px-4 pb-3 flex gap-2">
        <button
          onClick={onViewEvidence}
          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-teal-600 text-white text-[11px] font-semibold rounded-lg hover:bg-teal-700 transition-colors"
        >
          {t('safety_viewEvidence')}
        </button>
        <button
          onClick={onViewRiskMap}
          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-navy-900 text-white text-[11px] font-semibold rounded-lg hover:bg-navy-800 transition-colors"
        >
          {t('safety_viewRiskMap')}
        </button>
      </div>

      {/* Explore reasoning link */}
      <div className="px-4 pb-3 border-t border-gray-100 pt-2.5">
        <button className="flex items-center gap-1 text-[11px] text-teal-600 font-medium hover:text-teal-700 transition-colors">
          {t('safety_exploreReasoning')}
          <ArrowRight size={12} />
        </button>
      </div>

      {/* Disclaimer */}
      <div className="px-4 pb-3">
        <p className="text-[9px] text-gray-400 leading-relaxed italic">
          {t('safety_disclaimer')}
        </p>
      </div>
    </div>
  );
}
