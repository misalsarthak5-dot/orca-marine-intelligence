import { recommendedRoute } from '@/data/mockRoutes';
import { avoidZones } from '@/data/mockRoutes';
import { RouteRecommendation, AvoidZone } from '@/types';

export function getRecommendedRoute(): RouteRecommendation {
  return recommendedRoute;
}

export function getAvoidanceZones(): AvoidZone[] {
  return avoidZones;
}
