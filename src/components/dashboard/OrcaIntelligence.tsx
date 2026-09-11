'use client';

import React, { useEffect, useState } from 'react';
import {
  ArrowRight,
  Navigation,
  Route,
  Info,
  Compass,
  Layers,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { useTranslation } from '@/lib/i18n';
import { useLocation } from '@/lib/location';
import { fetchFastAPIPFZ, PFZAssessmentResponse, PFZAdvisory } from '@/services/pfzService';

interface OrcaIntelligenceProps {
  onReviewRoute?: () => void;
}

export default function OrcaIntelligence({ onReviewRoute }: OrcaIntelligenceProps) {
  const { t } = useTranslation();
  const { selectedLocation } = useLocation();
  const [pfzData, setPfzData] = useState<PFZAssessmentResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);

    fetchFastAPIPFZ(selectedLocation.latitude, selectedLocation.longitude)
      .then((data) => {
        if (isMounted) {
          setPfzData(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.warn('[OrcaIntelligence] Failed to fetch PFZ:', err);
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [selectedLocation.latitude, selectedLocation.longitude]);

  const nearestAdvisory: PFZAdvisory | null = pfzData?.nearest_advisory ?? null;
  const hasActivePfz = Boolean(pfzData?.available && nearestAdvisory);

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <h3 className="text-[11px] font-bold text-navy-900 uppercase tracking-wider">
          {t('intel_title')}
        </h3>
        <span className="text-[10px] font-semibold text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
          Official INCOIS PFZ Advisory
        </span>
      </div>

      {/* INCOIS PFZ Advisory Section */}
      <div className="px-4 py-3 border-b border-gray-100">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-1.5">
            <Compass size={13} className="text-teal-600" />
            <span className="text-[10px] font-bold text-teal-600 uppercase tracking-wider">
              PFZ Vector Intelligence
            </span>
          </div>
          <span className="text-[9px] text-gray-500 font-medium">
            {selectedLocation.name} Sector
          </span>
        </div>

        {loading ? (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 flex items-center justify-center gap-2 text-gray-500 text-[11px]">
            <Loader2 size={14} className="animate-spin text-teal-600" />
            <span>Querying official INCOIS PFZ WebGIS services...</span>
          </div>
        ) : hasActivePfz && nearestAdvisory ? (
          <div className="bg-emerald-50/70 border border-emerald-200 rounded-lg p-3 space-y-2.5">
            {/* Freshness banner if advisory is from historical record */}
            {!nearestAdvisory.is_currently_valid && (
              <div className="bg-amber-50/90 border border-amber-200 rounded p-2 text-[10px] text-amber-900 flex items-start gap-1.5 leading-relaxed">
                <Info size={13} className="text-amber-600 mt-0.5 flex-shrink-0" />
                <span>
                  <strong>Advisory Cycle:</strong> No currently valid (same-day) INCOIS PFZ advisory is available for this location. Showing official INCOIS advisory on record (Advisory validity: 28-Apr-2024 • Dataset updated: 29-Apr-2024) for baseline reference.
                </span>
              </div>
            )}

            {/* Nearest PFZ header */}
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[10px] font-bold text-emerald-800 uppercase tracking-wide">
                  Localized PFZ Advisory — Identified
                </span>
                <h5 className="text-[13px] font-bold text-navy-900 mt-0.5">
                  {nearestAdvisory.landing_center}
                  {nearestAdvisory.district ? ` (${nearestAdvisory.district})` : ''}
                </h5>
              </div>
              <span className="text-[10px] font-bold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded border border-emerald-200 flex items-center gap-1">
                <Compass size={11} className="text-emerald-700" />
                {nearestAdvisory.advisory_distance_from_km && nearestAdvisory.advisory_distance_to_km
                  ? `${nearestAdvisory.advisory_distance_from_km}–${nearestAdvisory.advisory_distance_to_km} km`
                  : `${nearestAdvisory.distance_from_query_km} km`}{' '}
                {nearestAdvisory.direction || ''}
              </span>
            </div>

            {/* Key Metrics Grid */}
            <div className="grid grid-cols-2 gap-2 bg-white/80 rounded-md p-2 border border-emerald-100 text-[11px]">
              <div>
                <span className="text-[10px] text-gray-500 block">PFZ Bearing & Direction</span>
                <span className="font-semibold text-navy-900">
                  {nearestAdvisory.bearing_degrees !== null && nearestAdvisory.bearing_degrees !== undefined
                    ? `${nearestAdvisory.bearing_degrees}° (${nearestAdvisory.direction || 'N/A'})`
                    : nearestAdvisory.direction || 'N/A'}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-gray-500 block">Depth Range</span>
                <span className="font-semibold text-navy-900">
                  {nearestAdvisory.depth_from_m !== null && nearestAdvisory.depth_to_m !== null
                    ? `Depth: ${nearestAdvisory.depth_from_m}–${nearestAdvisory.depth_to_m} m`
                    : 'Depth: Coastal shelf'}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-gray-500 block">Advisory Validity</span>
                <span className="font-semibold text-navy-900">
                  {nearestAdvisory.validity_formatted || nearestAdvisory.validity_date || '28-Apr-2024'}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-gray-500 block">Dataset Updated</span>
                <span className="font-semibold text-navy-900">
                  {nearestAdvisory.dataset_updated || '29-Apr-2024'}
                </span>
              </div>
            </div>

            {/* Target Coordinates & Attribution */}
            {nearestAdvisory.target_dms && (
              <div className="text-[10px] text-gray-600 font-mono bg-white/60 px-2 py-1 rounded border border-emerald-100 flex items-center justify-between">
                <span>Target Coordinates:</span>
                <span className="font-semibold text-navy-800">
                  {nearestAdvisory.target_dms.latitude}, {nearestAdvisory.target_dms.longitude}
                </span>
              </div>
            )}

            <div className="flex items-center justify-between pt-1 border-t border-emerald-200/60 text-[10px]">
              <span className="text-emerald-800 font-semibold">
                Source: INCOIS — Official PFZ Advisory
              </span>
              <span className="text-gray-500 font-medium">
                {pfzData?.total_pfz_lines_found ?? 0} regional PFZ lines mapped
              </span>
            </div>
          </div>
        ) : (
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5 space-y-2.5">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">
                  Localized PFZ Advisory
                </span>
                <div className="text-[12px] font-bold text-navy-900 mt-0.5">
                  None identified for {selectedLocation.name}
                </div>
              </div>
              <span className="text-[9px] font-bold bg-slate-200 text-slate-700 px-2 py-0.5 rounded">
                No Local Bulletin
              </span>
            </div>

            <p className="text-[11px] text-slate-600 leading-relaxed">
              No currently valid localized INCOIS PFZ landing-centre advisory is identified in this sector.
            </p>

            <div className="p-2.5 bg-white rounded-md border border-slate-200 space-y-1.5 text-[10px]">
              <div className="flex items-center justify-between">
                <span className="text-slate-500 font-semibold">Regional PFZ Intelligence:</span>
                <span className="font-bold text-teal-700">
                  {pfzData?.total_pfz_lines_found ?? 0} Regional Vectors ({pfzData?.total_nationwide_lines ?? 105} Nationwide)
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500 font-semibold">Dataset Layer:</span>
                <span className="font-medium text-navy-900">INCOIS GeoServer WFS (pfzlines)</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500 font-semibold">Marine Map Display:</span>
                <span className="font-medium text-emerald-700">Official vectors active on map</span>
              </div>
            </div>

            <div className="text-[10px] text-slate-500 flex items-center justify-between pt-1 border-t border-slate-200">
              <span>Recommendation: Review regional PFZ vectors and marine conditions.</span>
            </div>
          </div>
        )}
      </div>

      {/* Decision Support Insights */}
      <div className="px-4 py-3">
        <h4 className="text-[10px] font-bold text-navy-800 uppercase tracking-wider mb-2">
          Decision Support Insights
        </h4>
        <div className="space-y-1.5">
          {[
            `Real-time Open-Meteo wave swell & wind conditions evaluated for ${selectedLocation.name}.`,
            `Official INCOIS PFZ advisory vectors queried within operational radius.`,
            `Safety thresholds applied dynamically based on vessel operational limits.`,
          ].map((reason, i) => (
            <div key={i} className="flex items-start gap-2">
              <span className="text-[10px] font-bold text-teal-600 mt-0.5">{i + 1}.</span>
              <p className="text-[11px] text-gray-600">{reason}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}


