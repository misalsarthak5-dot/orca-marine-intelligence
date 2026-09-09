'use client';

import React from 'react';
import { Map, Construction } from 'lucide-react';

export default function PlaceholderPage({
  title,
  description,
  icon: Icon = Construction,
}: {
  title: string;
  description: string;
  icon?: React.ElementType;
}) {
  return (
    <div className="flex items-center justify-center h-full min-h-[400px]">
      <div className="text-center max-w-md">
        <div className="w-14 h-14 rounded-2xl bg-teal-50 border border-teal-200 flex items-center justify-center mx-auto mb-4">
          <Icon size={24} className="text-teal-600" />
        </div>
        <h2 className="text-lg font-bold text-navy-900 mb-2">{title}</h2>
        <p className="text-sm text-gray-500 leading-relaxed mb-4">{description}</p>
        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-50 text-amber-700 text-xs font-medium rounded-full border border-amber-200">
          <Construction size={12} />
          Under Development — Phase 2+
        </span>
      </div>
    </div>
  );
}
