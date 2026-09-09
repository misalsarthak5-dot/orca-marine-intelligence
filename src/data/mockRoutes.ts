import { RouteRecommendation, AvoidZone } from '@/types';

export const avoidZones: AvoidZone[] = [
  {
    id: 'avoid-1',
    label: 'High-Wave Zone',
    reason: 'Elevated wave conditions (2.0–2.4 m) expected 14:00–17:30 IST',
    boundary: [
      [18.75, 72.35],
      [18.75, 72.50],
      [18.85, 72.50],
      [18.85, 72.35],
    ],
    severity: 'warning',
  },
  {
    id: 'avoid-2',
    label: 'Lightning Alert Region',
    reason: 'Convective activity detected, lightning risk until 14:30 IST',
    boundary: [
      [18.90, 72.85],
      [18.90, 73.00],
      [19.00, 73.00],
      [19.00, 72.85],
    ],
    severity: 'warning',
  },
  {
    id: 'avoid-3',
    label: 'Restricted / Geofenced Area',
    reason: 'Naval exercise zone — temporary restricted area',
    boundary: [
      [19.05, 72.70],
      [19.05, 72.80],
      [19.12, 72.80],
      [19.12, 72.70],
    ],
    severity: 'critical',
  },
];

export const recommendedRoute: RouteRecommendation = {
  id: 'route-1',
  name: 'Recommended Safe Corridor',
  description:
    'Optimized route avoiding high-wave zone and restricted areas. Estimated 2° port deviation from direct path.',
  waypoints: [
    {
      id: 'wp-start',
      label: 'Mumbai Harbor (Start)',
      coordinates: [18.9398, 72.8347],
      type: 'start',
    },
    {
      id: 'wp-1',
      label: 'Waypoint Alpha',
      coordinates: [18.92, 72.75],
      type: 'waypoint',
    },
    {
      id: 'wp-2',
      label: 'Waypoint Beta',
      coordinates: [18.88, 72.60],
      type: 'waypoint',
    },
    {
      id: 'wp-3',
      label: 'Waypoint Gamma',
      coordinates: [18.85, 72.48],
      type: 'waypoint',
    },
    {
      id: 'wp-dest',
      label: 'PFZ Alpha (Destination)',
      coordinates: [18.85, 72.45],
      type: 'destination',
    },
  ],
  avoidZones,
  safeCorridorPath: [
    [18.9398, 72.8347],
    [18.93, 72.80],
    [18.92, 72.75],
    [18.90, 72.68],
    [18.88, 72.60],
    [18.86, 72.53],
    [18.85, 72.48],
    [18.85, 72.45],
  ],
  estimatedRisk: 'low',
  estimatedDistance: '34 km',
  estimatedTime: '~2h 15m',
};
