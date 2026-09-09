'use client';

import React from 'react';
import { LanguageProvider } from '@/lib/i18n';
import Sidebar from '@/components/layout/Sidebar';
import Header from '@/components/layout/Header';

export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <LanguageProvider>
      <div className="flex h-screen overflow-hidden">
        <Sidebar />
        <div className="flex-1 ml-[200px] flex flex-col overflow-hidden">
          <Header />
          <main className="flex-1 overflow-y-auto">{children}</main>
        </div>
      </div>
    </LanguageProvider>
  );
}
