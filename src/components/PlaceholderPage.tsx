'use client';

import React from 'react';
import { Info } from 'lucide-react';

export default function PlaceholderPage({
  title,
  description,
  icon: Icon = Info,
}: {
  title: string;
  description: string;
  icon?: React.ElementType;
}) {
  return (
    <div className="flex items-center justify-center h-full min-h-[400px] p-6">
      <div className="text-center max-w-md bg-white rounded-2xl border border-gray-200 p-8 shadow-xs">
        <div className="w-14 h-14 rounded-2xl bg-teal-50 border border-teal-200 flex items-center justify-center mx-auto mb-4">
          <Icon size={24} className="text-teal-600" />
        </div>
        <h2 className="text-lg font-bold text-navy-900 mb-2">{title}</h2>
        <p className="text-sm text-gray-500 leading-relaxed">{description}</p>
      </div>
    </div>
  );
}
