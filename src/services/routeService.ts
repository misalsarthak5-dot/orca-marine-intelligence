import { RouteRecommendation, AvoidZone } from '@/types';

/**
 * Route Intelligence Service
 * Route analysis requires selecting origin and destination coordinates.
 * Dynamic Route Intelligence endpoint: /api/routes/analyze
 */
export function getRecommendedRoute(originName: string = 'Origin', destName: string = 'Destination'): RouteRecommendation {
  return {
    id: 'route-pending',
    name: 'Route Analysis Pending',
    description: `Route intelligence between ${originName} and ${destName} requires destination selection.`,
    waypoints: [],
    avoidZones: [],
    safeCorridorPath: [],
    estimatedRisk: 'low',
    estimatedDistance: '--',
    estimatedTime: '--',
  };
}

export function getAvoidanceZones(): AvoidZone[] {
  return [];
}

