/**
 * ORCA — Potential Fishing Zone (PFZ) Frontend Service
 * 
 * Communicates with ORCA FastAPI backend to retrieve verified official INCOIS
 * Potential Fishing Zones (PFZ), Landing Centre Advisories, and Satellite PFZ Lines.
 * 
 * Provenance: Indian National Centre for Ocean Information Services (INCOIS)
 * Ministry of Earth Sciences, Government of India.
 */

import { FASTAPI_BASE_URL } from '@/config/api';

export interface PFZCoordinates {
  latitude: number;
  longitude: number;
}

export interface PFZAdvisory {
  id: string;
  landing_center: string;
  district?: string;
  sector?: string;
  lc_coordinates: PFZCoordinates;
  distance_from_query_km: number;
  advisory_distance_from_km?: number | null;
  advisory_distance_to_km?: number | null;
  direction?: string;
  bearing_degrees?: number | null;
  depth_from_m?: number | null;
  depth_to_m?: number | null;
  target_dms?: {
    latitude: string;
    longitude: string;
  };
  forecast_date?: string | null;
  validity_date?: string | null;
  validity_formatted?: string | null;
  is_currently_valid?: boolean;
  validity_status?: string;
  updated_date?: string | null;
  dataset_updated?: string;
  forecast_issue_id?: string | number | null;
  status: string;
  source: string;
}

export interface PFZLineFeature {
  uid: string;
  state_name?: string;
  category?: string;
  julian_day?: number | null;
  year?: number | null;
  length_km?: number | null;
  distance_km: number;
  geometry: {
    type: 'MultiLineString' | 'LineString';
    coordinates: number[][][] | number[][];
  };
  source: string;
}

export interface PFZAssessmentResponse {
  available: boolean;
  advisory_available?: boolean;
  advisory_message?: string;
  is_currently_valid: boolean;
  source: string;
  source_type: string;
  query_coordinates: PFZCoordinates;
  search_radius_km: number;
  nearest_advisory: PFZAdvisory | null;
  total_active_advisories_found: number;
  active_advisories: PFZAdvisory[];
  total_pfz_lines_found: number;
  pfz_lines: PFZLineFeature[];
  regional_pfz_lines?: PFZLineFeature[];
  total_regional_lines?: number;
  nationwide_pfz_lines?: PFZLineFeature[];
  total_nationwide_lines?: number;
  advisory_metadata: {
    authority: string;
    ministry: string;
    service_type: string;
    dataset_updated?: string;
    dataset_layer?: string;
    is_currently_valid?: boolean;
    localized_advisory_status?: string;
    regional_vectors_status?: string;
    validity_date?: string | null;
    validity_formatted?: string | null;
    validity_status?: string;
    pfz_lines_run?: string | null;
  };
  provenance_note: string;
}

/**
 * Fetches real INCOIS Potential Fishing Zones (PFZ) assessment from the ORCA backend.
 */
export async function fetchFastAPIPFZ(
  lat: number,
  lon: number,
  radiusKm: number = 250
): Promise<PFZAssessmentResponse> {
  try {
    const res = await fetch(
      `${FASTAPI_BASE_URL}/api/pfz?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}&radius_km=${encodeURIComponent(radiusKm)}`,
      {
        headers: { 'Accept': 'application/json' },
        cache: 'no-store',
      }
    );

    if (!res.ok) {
      throw new Error(`PFZ service HTTP ${res.status}: ${res.statusText}`);
    }

    const data: PFZAssessmentResponse = await res.json();
    return data;
  } catch (err) {
    console.warn('[PFZ Service] Unable to reach backend PFZ endpoint:', err);
    return {
      available: false,
      advisory_available: false,
      advisory_message: 'PFZ data temporarily unavailable. Verify backend connection.',
      is_currently_valid: false,
      source: 'INCOIS',
      source_type: 'Official PFZ Advisory',
      query_coordinates: { latitude: lat, longitude: lon },
      search_radius_km: radiusKm,
      nearest_advisory: null,
      total_active_advisories_found: 0,
      active_advisories: [],
      total_pfz_lines_found: 0,
      pfz_lines: [],
      nationwide_pfz_lines: [],
      total_nationwide_lines: 0,
      advisory_metadata: {
        authority: 'Indian National Centre for Ocean Information Services (INCOIS)',
        ministry: 'Ministry of Earth Sciences, Govt. of India',
        service_type: 'Multi-Mission Satellite Ocean Color & SST Thermal Fronts',
        dataset_updated: 'Unavailable',
        is_currently_valid: false,
        validity_formatted: 'Connection Unavailable',
        validity_status: 'UNAVAILABLE',
      },
      provenance_note: 'Backend PFZ service currently unreachable. Verify FastAPI server status.',
    };
  }
}
