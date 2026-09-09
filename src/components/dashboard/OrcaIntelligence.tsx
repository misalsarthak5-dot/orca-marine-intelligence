'use client';

import React from 'react';
import {
  ArrowRight,
  CheckCircle2,
  Navigation,
  Route,
} from 'lucide-react';
import { useTranslation } from '@/lib/i18n';
import { nearestPFZ } from '@/data/mockPFZData';

interface OrcaIntelligenceProps {
  onReviewRoute?: () => void;
}

export default function OrcaIntelligence({ onReviewRoute }: OrcaIntelligenceProps) {
  const { t } = useTranslation();

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-100">
        <h3 className="text-[11px] font-bold text-navy-900 uppercase tracking-wider">
          {t('intel_title')}
        </h3>
      </div>

      {/* Action Suggested */}
      <div className="px-4 py-3 border-b border-gray-100">
        <div className="flex items-center gap-1.5 mb-2">
          <Route size={12} className="text-teal-600" />
          <span className="text-[10px] font-bold text-teal-600 uppercase tracking-wider">
            {t('intel_actionSuggested')}
          </span>
        </div>
        <h4 className="text-[13px] font-bold text-navy-900 mb-1.5">{t('intel_routeRecommendation')}</h4>
        <p className="text-[11px] text-gray-600 leading-relaxed">
          Current trajectory encounters elevated wave conditions. A 2° port deviation reduces estimated exposure.
        </p>
        <div className="flex gap-2 mt-3">
          <button
            onClick={onReviewRoute}
            className="px-3 py-1.5 bg-teal-600 text-white text-[10px] font-semibold rounded-lg hover:bg-teal-700 transition-colors flex items-center gap-1"
          >
            {t('intel_reviewRoute')}
            <ArrowRight size={10} />
          </button>
          <button className="px-3 py-1.5 bg-gray-100 text-navy-700 text-[10px] font-semibold rounded-lg hover:bg-gray-200 transition-colors">
            {t('intel_simulate')}
          </button>
        </div>
      </div>

      {/* WHY section */}
      <div className="px-4 py-3 border-b border-gray-100">
        <h4 className="text-[10px] font-bold text-navy-800 uppercase tracking-wider mb-2">
          {t('intel_whyTitle')}
        </h4>
        <div className="space-y-1.5">
          {[
            'Wave conditions are elevated along the current corridor.',
            'Wind conditions are increasing from SW.',
            'A lower-risk corridor is available.',
          ].map((reason, i) => (
            <div key={i} className="flex items-start gap-2">
              <span className="text-[10px] font-bold text-teal-600 mt-0.5">{i + 1}.</span>
              <p className="text-[11px] text-gray-600">{reason}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Suggested Support - PFZ */}
      <div className="px-4 py-3">
        <h4 className="text-[10px] font-bold text-navy-800 uppercase tracking-wider mb-2">
          {t('intel_suggestedSupport')}
        </h4>
        <div className="bg-teal-50 border border-teal-200 rounded-lg p-3">
          <div className="flex items-center justify-between mb-1">
            <h5 className="text-[12px] font-bold text-teal-700">PFZ-A</h5>
            <span className="text-[10px] text-teal-600">{nearestPFZ.distance} • Bearing: 242°</span>
          </div>
          <p className="text-[10px] text-teal-600 mb-2">High Yield Tuna/Sardine</p>
          <button className="w-full px-3 py-1.5 bg-teal-600 text-white text-[10px] font-semibold rounded-lg hover:bg-teal-700 transition-colors flex items-center justify-center gap-1">
            <Navigation size={10} />
            {t('intel_sendWaypoint')}
          </button>
        </div>
      </div>
    </div>
  );
}
