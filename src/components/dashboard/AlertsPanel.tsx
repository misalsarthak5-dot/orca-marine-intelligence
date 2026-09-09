'use client';

import React from 'react';
import { AlertTriangle, Zap, Waves, MapPin, ExternalLink } from 'lucide-react';
import { useTranslation } from '@/lib/i18n';
import { getAlerts } from '@/services/marineDataService';

const alertIconMap: Record<string, React.ReactNode> = {
  lightning: <Zap size={14} />,
  waves: <Waves size={14} />,
};

const severityConfig: Record<string, { dot: string; bg: string; border: string }> = {
  critical: { dot: 'bg-red-500', bg: 'bg-red-50', border: 'border-red-200' },
  warning: { dot: 'bg-amber-500', bg: 'bg-amber-50', border: 'border-amber-200' },
  info: { dot: 'bg-blue-500', bg: 'bg-blue-50', border: 'border-blue-200' },
};

export default function AlertsPanel() {
  const alerts = getAlerts();
  const { t } = useTranslation();

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle size={14} className="text-amber-500" />
          <h3 className="text-[12px] font-bold text-navy-900">{t('alerts_title')}</h3>
        </div>
        <span className="inline-flex items-center gap-1 bg-red-100 text-red-700 text-[10px] font-bold px-2 py-0.5 rounded-full">
          {alerts.length} {t('alerts_active')}
        </span>
      </div>

      {/* Alert list */}
      {alerts.length > 0 ? (
        <div className="divide-y divide-gray-100">
          {alerts.map((alert) => {
            const config = severityConfig[alert.severity] || severityConfig.info;
            return (
              <div key={alert.id} className="px-4 py-3 flex items-start gap-3 hover:bg-gray-50 transition-colors">
                <span className={`w-2.5 h-2.5 rounded-full ${config.dot} mt-1 flex-shrink-0 animate-pulse-dot`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <h4 className="text-[12px] font-semibold text-navy-900 flex items-center gap-1.5">
                      {alertIconMap[alert.type]}
                      {alert.title}
                    </h4>
                    <button className="text-[10px] text-teal-600 font-medium hover:text-teal-700 flex items-center gap-0.5">
                      {t('alerts_viewOnMap')}
                      <ExternalLink size={9} />
                    </button>
                  </div>
                  <p className="text-[11px] text-gray-500 mt-0.5">{alert.description}</p>
                  <div className="flex items-center gap-3 mt-1.5">
                    <span className="text-[10px] text-gray-400 flex items-center gap-1">
                      <MapPin size={9} />
                      {alert.distance}
                    </span>
                    <span className="text-[10px] text-gray-400">Valid until {alert.validUntil}</span>
                    <span className="text-[10px] text-teal-600 font-medium">{alert.source}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="px-4 py-6 text-center">
          <p className="text-[12px] text-green-600 font-medium flex items-center justify-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-green-500" />
            {t('alerts_noAlerts')}
          </p>
        </div>
      )}
    </div>
  );
}
