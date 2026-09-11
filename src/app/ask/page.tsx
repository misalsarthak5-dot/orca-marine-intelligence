'use client';

import React from 'react';
import AskOrca from '@/components/dashboard/AskOrca';
import { useLocation } from '@/lib/location';
import { useTranslation } from '@/lib/i18n';
import { MessageCircle, Shield, Sparkles, MapPin, AlertCircle, Compass } from 'lucide-react';

export default function AskPage() {
  const { selectedLocation } = useLocation();
  const { language } = useTranslation();

  return (
    <div className="p-4 space-y-4 max-w-5xl mx-auto">
      {/* Top Banner */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-teal-50 border border-teal-200 flex items-center justify-center text-teal-600">
              <MessageCircle size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold text-navy-900">Ask ORCA — Conversational Intelligence</h1>
                <span className="bg-teal-50 text-teal-700 text-[10px] font-bold px-2 py-0.5 rounded-full border border-teal-200">
                  Multilingual AI Agent
                </span>
              </div>
              <p className="text-[11px] text-gray-500 mt-0.5">
                Multi-agent decision support for Indian coastal waters. Ask questions in English, हिन्दी, or मराठी.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 bg-teal-50/60 border border-teal-200 px-3 py-1.5 rounded-xl">
            <MapPin size={13} className="text-teal-600" />
            <span className="text-xs font-semibold text-teal-900">
              Active Sector: <span className="font-bold">{selectedLocation.name}</span>
            </span>
          </div>
        </div>
      </div>

      {/* Main Conversational Interface */}
      <div>
        <AskOrca />
      </div>

      {/* Suggested Topics / Query Guidance */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="bg-white rounded-xl border border-gray-200 p-3.5 shadow-xs">
          <div className="flex items-center gap-2 mb-1.5 text-teal-700 font-bold text-xs">
            <Shield size={14} />
            <span>Fishing Safety & Weather</span>
          </div>
          <p className="text-[11px] text-gray-500 leading-relaxed">
            Evaluates wind gusts, wave swells, lightning probability, and generates an official safety recommendation.
          </p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-3.5 shadow-xs">
          <div className="flex items-center gap-2 mb-1.5 text-teal-700 font-bold text-xs">
            <Compass size={14} />
            <span>INCOIS PFZ Advisories</span>
          </div>
          <p className="text-[11px] text-gray-500 leading-relaxed">
            Queries 105 nationwide Potential Fishing Zones with exact distance, bearing, and landing centre proximity.
          </p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-3.5 shadow-xs">
          <div className="flex items-center gap-2 mb-1.5 text-teal-700 font-bold text-xs">
            <AlertCircle size={14} />
            <span>Hazards & Maritime Risk</span>
          </div>
          <p className="text-[11px] text-gray-500 leading-relaxed">
            Checks live high wave alerts, squalls, cyclone paths, and provides clear explanations of environmental risks.
          </p>
        </div>
      </div>
    </div>
  );
}
