'use client';

import React from 'react';
import { Bell, User, Clock, Shield, Globe } from 'lucide-react';
import { useTranslation } from '@/lib/i18n';
import { useLocation } from '@/lib/location';
import { Language } from '@/types';

const languages: { code: Language; label: string }[] = [
  { code: 'en', label: 'EN' },
  { code: 'hi', label: 'हिंदी' },
  { code: 'mr', label: 'मराठी' },
];

export default function Header() {
  const { language, setLanguage, t } = useTranslation();
  const { selectedLocation, safetyAssessment, lastUpdated, isLoading } = useLocation();

  const isHigh = safetyAssessment?.riskLevel === 'high';
  const isCaution = safetyAssessment?.riskLevel === 'moderate';

  const riskBadgeClass = isHigh
    ? 'bg-red-100 text-red-700'
    : isCaution
    ? 'bg-amber-100 text-amber-700'
    : 'bg-green-100 text-green-700';

  const riskBadgeText = isHigh ? 'HIGH RISK' : isCaution ? 'CAUTION' : 'LOW RISK';
  const riskScore = isHigh ? '78 / 100' : isCaution ? '48 / 100' : '18 / 100';

  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center px-5 gap-4 z-30">
      {/* Left: Greeting */}
      <div className="flex-shrink-0 min-w-0">
        <div className="flex items-baseline gap-2">
          <h2 className="text-sm font-semibold text-navy-900 truncate">{t('header_greeting')}</h2>
          <span className="text-[11px] text-gray-400 flex items-center gap-1">
            <Clock size={11} />
            {lastUpdated ? lastUpdated : '09:42 IST'} | UTC+5:30
          </span>
        </div>
        <p className="text-[11px] text-gray-500 truncate">
          {selectedLocation.name} • {t('header_subtitle')}
        </p>
      </div>

      {/* Center: Fishing Safety Banner */}
      <div className="flex-1 flex justify-center">
        <div className="inline-flex items-center gap-2.5 bg-teal-50 border border-teal-200 rounded-lg px-4 py-1.5">
          <Shield size={14} className="text-teal-600 flex-shrink-0" />
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-bold text-teal-700 uppercase tracking-wide">{t('header_fishingSafety')}</span>
            <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase ${riskBadgeClass}`}>
              {riskBadgeText}
            </span>
            <span className="text-[10px] text-navy-600 font-semibold">{riskScore}</span>
          </div>
          <div className="border-l border-teal-200 pl-2.5 ml-1">
            <p className="text-[10px] text-gray-500">{selectedLocation.name} • {t('header_validTomorrow')}</p>
          </div>
        </div>
      </div>

      {/* Right: Controls */}
      <div className="flex items-center gap-3 flex-shrink-0">
        {/* Last updated */}
        <span className="text-[10px] text-gray-400 font-mono">
          {t('header_lastUpdated')}: {isLoading ? 'Updating...' : (lastUpdated || '09:42 IST')}
        </span>

        {/* Language selector */}
        <div className="flex items-center gap-0.5 bg-gray-100 rounded-md p-0.5">
          {languages.map((lang) => (
            <button
              key={lang.code}
              onClick={() => setLanguage(lang.code)}
              className={`px-2 py-1 text-[11px] font-medium rounded transition-colors ${
                language === lang.code
                  ? 'bg-white text-navy-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {lang.label}
            </button>
          ))}
        </div>

        {/* Notification bell */}
        <button className="relative p-1.5 rounded-lg hover:bg-gray-100 transition-colors">
          <Bell size={16} className="text-gray-500" />
          <span className="absolute top-0.5 right-0.5 w-2 h-2 bg-red-500 rounded-full" />
        </button>

        {/* User avatar */}
        <button className="w-7 h-7 rounded-full bg-navy-100 flex items-center justify-center hover:bg-navy-200 transition-colors">
          <User size={14} className="text-navy-600" />
        </button>
      </div>
    </header>
  );
}
