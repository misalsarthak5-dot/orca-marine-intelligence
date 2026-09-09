import { marineConditions } from '@/data/mockMarineData';
import { pfzZones, nearestPFZ } from '@/data/mockPFZData';
import { marineAlerts, evidenceSources } from '@/data/mockAlerts';
import { MarineCondition, PFZZone, MarineAlert, EvidenceSource } from '@/types';
export { getLiveOrcaMarineData, mapToMarineConditions } from './orcaDataService';

export function getMarineConditions(): MarineCondition[] {
  return marineConditions;
}

export function getPFZZones(): PFZZone[] {
  return pfzZones;
}

export function getNearestPFZ(): PFZZone {
  return nearestPFZ;
}

export function getAlerts(): MarineAlert[] {
  return marineAlerts;
}

export function getEvidenceSources(): EvidenceSource[] {
  return evidenceSources;
}
