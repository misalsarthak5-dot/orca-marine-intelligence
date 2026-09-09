'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Map,
  MessageCircle,
  Ship,
  AlertTriangle,
  Brain,
  History,
  Settings,
  HelpCircle,
  Waves,
  Wifi,
} from 'lucide-react';
import { useTranslation } from '@/lib/i18n';
import { TranslationStrings } from '@/types';

interface NavItem {
  labelKey: keyof TranslationStrings;
  href: string;
  icon: React.ReactNode;
  badge?: number;
}

const mainNavItems: NavItem[] = [
  { labelKey: 'nav_dashboard', href: '/dashboard', icon: <LayoutDashboard size={18} /> },
  { labelKey: 'nav_liveMap', href: '/live-map', icon: <Map size={18} /> },
  { labelKey: 'nav_askOrca', href: '/ask', icon: <MessageCircle size={18} /> },
  { labelKey: 'nav_fleet', href: '/fleet', icon: <Ship size={18} /> },
  { labelKey: 'nav_alerts', href: '/alerts', icon: <AlertTriangle size={18} />, badge: 2 },
  { labelKey: 'nav_intelligence', href: '/intelligence', icon: <Brain size={18} /> },
  { labelKey: 'nav_history', href: '/history', icon: <History size={18} /> },
];

const bottomNavItems: NavItem[] = [
  { labelKey: 'nav_settings', href: '/settings', icon: <Settings size={18} /> },
  { labelKey: 'nav_support', href: '/support', icon: <HelpCircle size={18} /> },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { t } = useTranslation();

  const isActive = (href: string) => pathname === href || pathname.startsWith(href + '/');

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-[200px] bg-white border-r border-gray-200 flex flex-col z-40">
      {/* Logo */}
      <div className="px-4 py-4 border-b border-gray-100">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-teal-600 flex items-center justify-center">
            <Waves size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-navy-900 tracking-tight leading-none">ORCA</h1>
            <p className="text-[10px] text-gray-500 font-medium tracking-wide uppercase mt-0.5">Oceanic Intelligence</p>
          </div>
        </div>
      </div>

      {/* Main navigation */}
      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        {mainNavItems.map((item) => {
          const active = isActive(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-colors duration-150 group relative ${
                active
                  ? 'bg-teal-50 text-teal-700 border-l-[3px] border-teal-600 pl-[9px]'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-navy-800'
              }`}
            >
              <span className={active ? 'text-teal-600' : 'text-gray-400 group-hover:text-gray-600'}>{item.icon}</span>
              <span>{t(item.labelKey)}</span>
              {item.badge && (
                <span className="ml-auto bg-red-500 text-white text-[10px] font-bold w-4.5 h-4.5 rounded-full flex items-center justify-center">
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Bottom navigation */}
      <div className="px-2 py-2 border-t border-gray-100 space-y-0.5">
        {bottomNavItems.map((item) => {
          const active = isActive(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-colors duration-150 ${
                active
                  ? 'bg-teal-50 text-teal-700'
                  : 'text-gray-500 hover:bg-gray-50 hover:text-navy-800'
              }`}
            >
              <span className="text-gray-400">{item.icon}</span>
              <span>{t(item.labelKey)}</span>
            </Link>
          );
        })}
      </div>

      {/* Connection status */}
      <div className="px-3 py-3 border-t border-gray-100">
        <div className="flex items-center gap-2 text-[11px]">
          <Wifi size={12} className="text-green-500" />
          <span className="text-gray-500">ISRO BHUVAN</span>
          <span className="ml-auto inline-flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse-dot" />
            <span className="text-green-600 font-medium">LIVE</span>
          </span>
        </div>
      </div>
    </aside>
  );
}
