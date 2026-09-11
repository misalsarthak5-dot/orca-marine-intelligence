'use client';

import React from 'react';
import FishingSafetyAssessment from '@/components/dashboard/FishingSafetyAssessment';
import OrcaIntelligence from '@/components/dashboard/OrcaIntelligence';
import MarineEnvironmentalIntelligence from '@/components/dashboard/MarineEnvironmentalIntelligence';
import AgentNetwork from '@/components/dashboard/AgentNetwork';
import { useLocation } from '@/lib/location';
import { Brain, MapPin, Database, GitBranch, ShieldCheck } from 'lucide-react';

export default function IntelligencePage() {
  const { selectedLocation, setSelectedLocation, locationsList } = useLocation();

  return (
    <div className="p-4 space-y-4 max-w-7xl mx-auto">
      {/* Top Banner */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-teal-50 border border-teal-200 flex items-center justify-center text-teal-600">
              <Brain size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold text-navy-900">ORCA Reasoning &amp; Intelligence</h1>
                <span className="bg-teal-50 text-teal-700 text-[10px] font-bold px-2 py-0.5 rounded-full border border-teal-200">
                  Agentic AI System
                </span>
              </div>
              <p className="text-[11px] text-gray-500 mt-0.5">
                Transparent multi-agent reasoning: What ORCA knows from live ocean feeds, how agents synthesize risk, and why actions are recommended.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-xs font-semibold text-gray-500 flex items-center gap-1">
              <MapPin size={12} className="text-teal-600" />
              Active Sector:
            </label>
            <select
              value={selectedLocation.name}
              onChange={(e) => {
                const found = locationsList.find((l) => l.name === e.target.value);
                if (found) setSelectedLocation(found);
              }}
              aria-label="Select Coastal Sector"
              className="text-xs font-bold text-navy-900 bg-gray-50 border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-teal-500/30 cursor-pointer"
            >
              {locationsList.map((loc) => (
                <option key={loc.name} value={loc.name}>
                  {loc.name} ({loc.latitude.toFixed(1)}°N, {loc.longitude.toFixed(1)}°E)
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* 3 Pillars of ORCA Reasoning */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="bg-white rounded-xl border border-gray-200 p-3.5 shadow-xs flex items-start gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 flex-shrink-0 mt-0.5">
            <Database size={16} />
          </div>
          <div>
            <h3 className="text-xs font-bold text-navy-900">1. What ORCA Knows</h3>
            <p className="text-[11px] text-gray-500 mt-0.5 leading-relaxed">
              Official INCOIS PFZ vectors, Open-Meteo wave swell &amp; wind models, ISRO Bhuvan satellite telemetry, and coastal landing points.
            </p>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-3.5 shadow-xs flex items-start gap-3">
          <div className="w-8 h-8 rounded-lg bg-teal-50 border border-teal-200 flex items-center justify-center text-teal-600 flex-shrink-0 mt-0.5">
            <GitBranch size={16} />
          </div>
          <div>
            <h3 className="text-xs font-bold text-navy-900">2. How ORCA Reasons</h3>
            <p className="text-[11px] text-gray-500 mt-0.5 leading-relaxed">
              Autonomous micro-agents cross-examine safety thresholds, oceanic fronts, thermal gradients, and severe weather indicators.
            </p>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-3.5 shadow-xs flex items-start gap-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 flex-shrink-0 mt-0.5">
            <ShieldCheck size={16} />
          </div>
          <div>
            <h3 className="text-xs font-bold text-navy-900">3. Why ORCA Recommends</h3>
            <p className="text-[11px] text-gray-500 mt-0.5 leading-relaxed">
              Explainable verdicts with verified evidence, confidence ratings, threshold breakdowns, and actionable multilingual advisories.
            </p>
          </div>
        </div>
      </div>

      {/* Row 1: Safety Assessment + PFZ Vector Intelligence */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-6">
          <FishingSafetyAssessment />
        </div>
        <div className="lg:col-span-6">
          <OrcaIntelligence />
        </div>
      </div>

      {/* Row 2: Marine Environmental Intelligence */}
      <div>
        <MarineEnvironmentalIntelligence />
      </div>

      {/* Row 3: Multi-Agent Network Status */}
      <div>
        <AgentNetwork />
      </div>
    </div>
  );
}
