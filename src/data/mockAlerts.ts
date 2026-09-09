import { MarineAlert } from '@/types';

export const marineAlerts: MarineAlert[] = [
  {
    id: 'alert-1',
    type: 'lightning',
    severity: 'warning',
    title: 'Lightning Risk Spike',
    description:
      'Convective cloud mass moving NW at 12 kts. Valid until 14:00 IST.',
    location: '18 km southeast',
    distance: '18 km SE',
    validUntil: '14:30 IST',
    source: 'IMD Nowcast',
    coordinates: [18.95, 72.95],
  },
  {
    id: 'alert-2',
    type: 'waves',
    severity: 'warning',
    title: 'Elevated Swell Window',
    description:
      '1.8m – 2.3m seas forecast between 15:00 and 18:00 IST on the outer shelf.',
    location: 'Outer shelf',
    distance: 'Outer shelf',
    validUntil: '18:00 IST',
    source: 'INCOIS Ocean Buoy',
    coordinates: [18.80, 72.50],
  },
];

export const evidenceSources = [
  {
    id: 'ev-1',
    name: 'INCOIS Ocean Buoy 23',
    type: 'ocean' as const,
    provider: 'INCOIS',
    timestamp: '09:30 IST',
    description: 'Real-time oceanographic buoy observations',
  },
  {
    id: 'ev-2',
    name: 'IMD High-Res WRF',
    type: 'weather' as const,
    provider: 'IMD',
    timestamp: '06:00 IST',
    description: 'High-resolution weather forecast model',
  },
  {
    id: 'ev-3',
    name: 'ICG Marine Advisory',
    type: 'advisory' as const,
    provider: 'Indian Coast Guard',
    timestamp: '08:00 IST',
    description: 'Official marine safety advisory',
  },
  {
    id: 'ev-4',
    name: 'Sentinel-3 Chlorophyll',
    type: 'satellite' as const,
    provider: 'Copernicus / ESA',
    timestamp: '05:45 IST',
    description: 'Satellite-derived chlorophyll concentration',
  },
  {
    id: 'ev-5',
    name: 'ISRO Oceansat-3',
    type: 'satellite' as const,
    provider: 'ISRO',
    timestamp: '06:15 IST',
    description: 'Ocean colour and SST observation',
  },
];
