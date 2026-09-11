'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Wifi, WifiOff, AlertTriangle, RefreshCw, CheckCircle2, Clock } from 'lucide-react';
import { connectivityService, ConnectivityState } from '@/services/connectivityService';
import { formatAge, formatTimestampIST } from '@/utils/freshness';

export function ConnectivityStatusBadge() {
  const [state, setState] = useState<ConnectivityState>(connectivityService.getState());
  const [isOpen, setIsOpen] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const unsubscribe = connectivityService.subscribe((newState) => {
      setState(newState);
    });

    // Close popover on outside click
    const handleClickOutside = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);

    return () => {
      unsubscribe();
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleRetry = async () => {
    setIsRetrying(true);
    try {
      await connectivityService.triggerRecovery();
    } finally {
      setTimeout(() => {
        setIsRetrying(false);
      }, 600);
    }
  };

  const statusConfig = {
    ONLINE: {
      bg: 'bg-emerald-50 border-emerald-200 text-emerald-800 hover:bg-emerald-100',
      dot: 'bg-emerald-500',
      pulse: 'bg-emerald-400',
      label: 'LIVE DATA',
      icon: Wifi,
      badgeText: 'Connected',
    },
    LIMITED: {
      bg: 'bg-amber-50 border-amber-200 text-amber-800 hover:bg-amber-100',
      dot: 'bg-amber-500',
      pulse: 'bg-amber-400',
      label: 'LIMITED CONNECTIVITY',
      icon: AlertTriangle,
      badgeText: 'Using Verified Cache',
    },
    OFFLINE: {
      bg: 'bg-rose-50 border-rose-200 text-rose-800 hover:bg-rose-100',
      dot: 'bg-rose-500',
      pulse: 'bg-rose-400',
      label: 'OFFLINE',
      icon: WifiOff,
      badgeText: 'Offline Cache',
    },
  }[state.status];

  const Icon = statusConfig.icon;
  const syncTimeStr = state.lastSuccessfulSync ? formatTimestampIST(state.lastSuccessfulSync) : 'None';
  const syncAgeStr = state.lastSuccessfulSync ? formatAge(state.lastSuccessfulSync) : 'N/A';

  return (
    <div className="relative inline-block text-left" ref={popoverRef}>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Connectivity status menu"
        aria-expanded={isOpen}
        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold tracking-wide border transition-all duration-200 shadow-2xs cursor-pointer ${statusConfig.bg}`}
      >
        <span className="relative flex h-2 w-2">
          {state.status === 'ONLINE' && (
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${statusConfig.pulse}`} />
          )}
          <span className={`relative inline-flex rounded-full h-2 w-2 ${statusConfig.dot}`} />
        </span>
        <span className="uppercase text-[10px] font-bold">{statusConfig.label}</span>
      </button>

      {/* Popover Details */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-72 origin-top-right rounded-xl bg-white border border-gray-200 shadow-xl ring-1 ring-black/5 z-[2000] p-3.5 space-y-3 animate-in fade-in zoom-in-95 duration-150">
          <div className="flex items-center justify-between pb-2 border-b border-gray-100">
            <div className="flex items-center gap-1.5">
              <Icon size={14} className={state.status === 'ONLINE' ? 'text-emerald-600' : state.status === 'LIMITED' ? 'text-amber-600' : 'text-rose-600'} />
              <span className="text-[12px] font-bold text-navy-900">Connectivity Status</span>
            </div>
            <span
              className={`text-[9px] font-bold px-2 py-0.5 rounded-full border ${
                state.status === 'ONLINE'
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : state.status === 'LIMITED'
                  ? 'bg-amber-50 text-amber-700 border-amber-200'
                  : 'bg-rose-50 text-rose-700 border-rose-200'
              }`}
            >
              {statusConfig.badgeText}
            </span>
          </div>

          <div className="space-y-2 text-[11px]">
            <div className="flex justify-between items-center text-gray-600">
              <span>Internet Connection:</span>
              <span className="font-semibold text-navy-800 flex items-center gap-1">
                {state.isOffline ? (
                  <>
                    <WifiOff size={11} className="text-rose-500" /> Disconnected
                  </>
                ) : (
                  <>
                    <CheckCircle2 size={11} className="text-emerald-500" /> Connected
                  </>
                )}
              </span>
            </div>

            <div className="flex justify-between items-center text-gray-600">
              <span>Live Marine Telemetry:</span>
              <span className="font-semibold text-navy-800">
                {state.status === 'ONLINE' ? 'Active' : state.status === 'LIMITED' ? 'Using Cache' : 'Unavailable'}
              </span>
            </div>

            <div className="flex justify-between items-center text-gray-600">
              <span className="flex items-center gap-1">
                <Clock size={11} className="text-gray-400" /> Last Live Sync:
              </span>
              <span className="font-semibold text-navy-800" title={`Timestamp: ${syncTimeStr}`}>
                {syncTimeStr} ({syncAgeStr})
              </span>
            </div>

            {state.activeReason && (
              <div className="p-2 rounded-lg bg-gray-50 border border-gray-100 text-[10px] text-gray-600 leading-relaxed">
                {state.activeReason}
              </div>
            )}
          </div>

          <div className="pt-1 flex items-center justify-between">
            <button
              onClick={handleRetry}
              disabled={isRetrying}
              className="w-full flex items-center justify-center gap-1.5 py-1.5 px-3 bg-teal-600 hover:bg-teal-700 active:bg-teal-800 text-white rounded-lg text-[11px] font-semibold transition-colors disabled:opacity-60 cursor-pointer shadow-xs"
            >
              <RefreshCw size={12} className={isRetrying ? 'animate-spin' : ''} />
              <span>{isRetrying ? 'Syncing Telemetry...' : 'Reconnect & Refresh'}</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
