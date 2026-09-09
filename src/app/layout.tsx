import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

export const metadata: Metadata = {
  title: 'ORCA — Oceanic Reasoning & Collaborative Agents',
  description:
    'Agentic AI-Powered Marine Intelligence & Conversational Decision Support Platform. From ocean data to actionable intelligence.',
  keywords: 'marine intelligence, fishing safety, PFZ, ocean data, ISRO, SIH 2026',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`h-full antialiased ${inter.variable}`}>
      <body className={`min-h-full bg-slate-50 text-slate-900 ${inter.className}`}>
        {children}
      </body>
    </html>
  );
}
