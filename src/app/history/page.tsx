'use client';

import React from 'react';
import { History, MessageCircle, Info } from 'lucide-react';
import Link from 'next/link';

export default function HistoryPage() {
  return (
    <div className="p-4 space-y-4 max-w-4xl mx-auto">
      <div className="bg-white rounded-xl border border-gray-200 p-8 shadow-xs text-center">
        <div className="w-14 h-14 rounded-2xl bg-teal-50 border border-teal-200 flex items-center justify-center mx-auto mb-4 text-teal-600">
          <History size={28} />
        </div>
        <h1 className="text-xl font-bold text-navy-900 mb-2">Query &amp; Activity History</h1>
        <p className="text-sm text-gray-500 max-w-md mx-auto leading-relaxed mb-6">
          Conversational queries and oceanographic assessments are currently processed in real-time within your active browser session.
        </p>

        <div className="inline-flex items-center gap-2 px-4 py-2 bg-teal-50 border border-teal-200 rounded-xl text-xs font-semibold text-teal-800">
          <Info size={14} className="text-teal-600 flex-shrink-0" />
          <span>To ask questions or analyze coastal sectors, visit Ask ORCA.</span>
        </div>

        <div className="mt-6">
          <Link
            href="/ask"
            className="inline-flex items-center gap-2 px-4 py-2 bg-teal-600 text-white rounded-xl text-xs font-bold hover:bg-teal-700 transition-colors shadow-xs"
          >
            <MessageCircle size={14} />
            Open Ask ORCA
          </Link>
        </div>
      </div>
    </div>
  );
}
