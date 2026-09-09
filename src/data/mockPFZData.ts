import { PFZZone } from '@/types';

export const pfzZones: PFZZone[] = [
  {
    id: 'pfz-alpha',
    name: 'PFZ Alpha',
    coordinates: [18.85, 72.45],
    boundary: [
      [18.82, 72.40],
      [18.82, 72.50],
      [18.88, 72.50],
      [18.88, 72.40],
    ],
    distance: '32 km',
    sst: '28.2°C',
    sstStatus: 'Suitable',
    chlorophyll: '1.4 mg/m³',
    chlorophyllStatus: 'High',
    marineRisk: 'low',
    probability: 'high',
    recommendation: 'This zone currently shows favourable conditions.',
  },
  {
    id: 'pfz-beta',
    name: 'PFZ Beta',
    coordinates: [18.70, 72.25],
    boundary: [
      [18.67, 72.20],
      [18.67, 72.30],
      [18.73, 72.30],
      [18.73, 72.20],
    ],
    distance: '48 km',
    sst: '27.8°C',
    sstStatus: 'Suitable',
    chlorophyll: '1.1 mg/m³',
    chlorophyllStatus: 'Moderate',
    marineRisk: 'low',
    probability: 'medium',
    recommendation: 'Moderate chlorophyll levels. Conditions are suitable but not optimal.',
  },
  {
    id: 'pfz-gamma',
    name: 'PFZ Gamma',
    coordinates: [19.15, 72.60],
    boundary: [
      [19.12, 72.55],
      [19.12, 72.65],
      [19.18, 72.65],
      [19.18, 72.55],
    ],
    distance: '55 km',
    sst: '28.6°C',
    sstStatus: 'Suitable',
    chlorophyll: '0.9 mg/m³',
    chlorophyllStatus: 'Moderate',
    marineRisk: 'moderate',
    probability: 'medium',
    recommendation: 'Suitable SST but moderate conditions. Monitor weather closely.',
  },
];

export const nearestPFZ = pfzZones[0];
