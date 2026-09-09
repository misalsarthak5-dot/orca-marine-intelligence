'use client';

import React from 'react';
import {
  User,
  Brain,
  Anchor,
  CloudSun,
  Waves,
  Map,
  ShieldAlert,
  BarChart3,
  FileText,
  CheckCircle2,
  Clock,
} from 'lucide-react';
import { useTranslation } from '@/lib/i18n';
import { agentNetwork } from '@/data/mockConversations';
import { AgentStatusType } from '@/types';

const iconMap: Record<string, React.ReactNode> = {
  user: <User size={14} />,
  brain: <Brain size={14} />,
  anchor: <Anchor size={14} />,
  cloudSun: <CloudSun size={14} />,
  waves: <Waves size={14} />,
  map: <Map size={14} />,
  shieldAlert: <ShieldAlert size={14} />,
  barChart3: <BarChart3 size={14} />,
  fileText: <FileText size={14} />,
};

const statusConfig: Record<AgentStatusType, { icon: React.ReactNode; color: string; bg: string; ring: string }> = {
  ready: {
    icon: <Clock size={8} />,
    color: 'text-gray-400',
    bg: 'bg-gray-100',
    ring: 'ring-gray-200',
  },
  processing: {
    icon: <div className="w-2 h-2 border border-teal-500 border-t-transparent rounded-full animate-spin" />,
    color: 'text-teal-500',
    bg: 'bg-teal-50',
    ring: 'ring-teal-200',
  },
  complete: {
    icon: <CheckCircle2 size={8} />,
    color: 'text-green-500',
    bg: 'bg-green-50',
    ring: 'ring-green-200',
  },
};

export default function AgentNetwork() {
  const { t } = useTranslation();

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-2.5 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain size={14} className="text-teal-600" />
          <h3 className="text-[10px] font-bold text-navy-900 uppercase tracking-wider">
            {t('agents_title')}
          </h3>
        </div>
        <div className="flex items-center gap-3 text-[10px] text-gray-400">
          <span>{t('agents_latency')}: 142ms</span>
          <span>{t('agents_freshness')}: 3m ago (INSAT-3DR)</span>
        </div>
      </div>

      {/* Agent grid */}
      <div className="px-4 py-3">
        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          {agentNetwork.map((agent) => {
            const config = statusConfig[agent.status];
            return (
              <div
                key={agent.id}
                className="flex flex-col items-center gap-1.5 flex-shrink-0 group cursor-default"
              >
                <div className={`relative w-9 h-9 rounded-lg ${config.bg} ring-1 ${config.ring} flex items-center justify-center transition-all group-hover:shadow-sm`}>
                  <span className={config.color}>{iconMap[agent.icon]}</span>
                  <span className={`absolute -bottom-0.5 -right-0.5 ${config.color}`}>
                    {config.icon}
                  </span>
                </div>
                <span className="text-[8px] font-bold text-gray-500 uppercase tracking-wider text-center leading-tight max-w-[50px]">
                  {agent.shortName}
                </span>
              </div>
            );
          })}
        </div>

        {/* Bottom status bar */}
        <div className="mt-2.5 pt-2 border-t border-gray-100 flex flex-wrap gap-x-2 gap-y-0.5">
          {agentNetwork.map((agent) => (
            <span key={agent.id} className="text-[9px] text-gray-400">
              ✓ {agent.name}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
