'use client';

import React from 'react';
import { HelpCircle, PhoneCall, Globe, BookOpen, ShieldCheck, Waves } from 'lucide-react';

export default function SupportPage() {
  return (
    <div className="p-4 space-y-4 max-w-4xl mx-auto">
      {/* Header */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-xs flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-teal-50 border border-teal-200 flex items-center justify-center text-teal-600">
          <HelpCircle size={20} />
        </div>
        <div>
          <h1 className="text-base font-bold text-navy-900">Support &amp; Marine Assistance</h1>
          <p className="text-[11px] text-gray-500 mt-0.5">
            Operational resources, coastal emergency hotlines, and official oceanographic portals.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Emergency Contacts */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-xs space-y-3">
          <div className="flex items-center gap-2 pb-2 border-b border-gray-100">
            <PhoneCall size={16} className="text-rose-600" />
            <h2 className="text-xs font-bold text-navy-900 uppercase tracking-wider">
              Maritime Emergency Lines
            </h2>
          </div>

          <div className="space-y-2 text-xs">
            <div className="p-3 bg-rose-50/60 rounded-lg border border-rose-200">
              <div className="font-bold text-rose-950">Indian Coast Guard (ICG) SAR</div>
              <div className="text-[11px] text-rose-800 mt-0.5">National Maritime Search &amp; Rescue Toll-Free</div>
              <div className="text-base font-mono font-bold text-rose-900 mt-1">1554</div>
            </div>

            <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
              <div className="font-bold text-navy-900">National Disaster Management (NDRF)</div>
              <div className="text-[11px] text-gray-600 mt-0.5">National Emergency Helpline</div>
              <div className="text-base font-mono font-bold text-navy-900 mt-1">1070 / 112</div>
            </div>
          </div>
        </div>

        {/* Official Portals */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-xs space-y-3">
          <div className="flex items-center gap-2 pb-2 border-b border-gray-100">
            <Globe size={16} className="text-teal-600" />
            <h2 className="text-xs font-bold text-navy-900 uppercase tracking-wider">
              Official Geospatial Portals
            </h2>
          </div>

          <div className="space-y-2 text-xs">
            <a
              href="https://www.incois.gov.in"
              target="_blank"
              rel="noopener noreferrer"
              className="p-3 bg-gray-50 hover:bg-teal-50 rounded-lg border border-gray-200 block transition-colors"
            >
              <div className="font-bold text-navy-900">INCOIS WebGIS &amp; PFZ Services</div>
              <div className="text-[11px] text-gray-500 mt-0.5">Indian National Centre for Ocean Information Services</div>
              <div className="text-[10px] text-teal-700 font-mono mt-1">incois.gov.in</div>
            </a>

            <a
              href="https://mausam.imd.gov.in"
              target="_blank"
              rel="noopener noreferrer"
              className="p-3 bg-gray-50 hover:bg-teal-50 rounded-lg border border-gray-200 block transition-colors"
            >
              <div className="font-bold text-navy-900">India Meteorological Department (IMD)</div>
              <div className="text-[11px] text-gray-500 mt-0.5">Marine Weather &amp; Cyclone Warning Division</div>
              <div className="text-[10px] text-teal-700 font-mono mt-1">mausam.imd.gov.in</div>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
