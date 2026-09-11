import { HazardAssessment } from '@/types';
import { FASTAPI_BASE_URL } from '@/config/api';

export async function fetchFastAPIHazards(lat: number, lon: number): Promise<HazardAssessment> {
  if (lat === undefined || lon === undefined || isNaN(lat) || isNaN(lon)) {
    throw new Error('Coordinates (latitude, longitude) must be explicitly provided.');
  }

  const endpoint = `${FASTAPI_BASE_URL}/api/hazards?latitude=${lat}&longitude=${lon}`;

  try {
    const res = await fetch(endpoint, {
      cache: 'no-store',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (res.ok) {
      const data = await res.json();
      return data as HazardAssessment;
    }
  } catch (err) {
    console.warn(`[hazardService] FastAPI /api/hazards unreachable (${err}). Showing unavailable state.`);
  }

  // Honest unavailable state when FastAPI is disconnected
  return {
    coordinates: { latitude: lat, longitude: lon },
    overall_state: 'CAUTION',
    overall_code: 'caution',
    headline: 'Unable to connect to ORCA hazard intelligence service',
    active_conditions_count: 0,
    active_alerts: [],
    conditions: [
      {
        id: 'waves',
        name: 'Wave Conditions',
        icon: 'waves',
        value: '--',
        unit: 'm',
        status: 'Data unavailable',
        severity: 'unavailable',
        is_active: false,
        threshold: 'Normal: ≤1.8m | Elevated: 1.8–2.5m | High: >2.5m',
        explanation: 'Live wave telemetry unavailable from data services.',
      },
      {
        id: 'wind',
        name: 'Wind & Gusts',
        icon: 'wind',
        value: '--',
        unit: 'kts',
        status: 'Data unavailable',
        severity: 'unavailable',
        is_active: false,
        threshold: 'Normal: ≤15 kts | Caution: 15–22 kts | High: >22 kts',
        explanation: 'Live wind telemetry unavailable from data services.',
      },
      {
        id: 'precipitation',
        name: 'Precipitation & Visibility',
        icon: 'rain',
        value: '--',
        unit: 'mm',
        status: 'Data unavailable',
        severity: 'unavailable',
        is_active: false,
        threshold: 'Clear: ≤1.0mm | Elevated: 1.0–5.0mm | Heavy: >5.0mm',
        explanation: 'Live precipitation telemetry unavailable from data services.',
      },
      {
        id: 'lightning',
        name: 'Lightning Activity',
        icon: 'lightning',
        value: 'Unavailable',
        unit: '',
        status: 'Data unavailable',
        severity: 'unavailable',
        is_active: false,
        threshold: 'IMD Radar Nowcast',
        explanation: 'No real-time lightning detection sensor stream connected for this coastal sector. Verify local radar nowcasts before departure.',
      },
      {
        id: 'cyclone',
        name: 'Cyclone & Severe Storm',
        icon: 'cyclone',
        value: 'Unavailable',
        unit: '',
        status: 'Data unavailable',
        severity: 'unavailable',
        is_active: false,
        threshold: 'IMD / RSMC Bulletins',
        explanation: 'Regional cyclone bulletin feed disconnected. Verify official IMD warnings.',
      },
    ],
    disclaimer: 'ORCA provides AI-assisted decision support based on available environmental data. Always check official marine weather warnings and local authority advisories before venturing to sea.',
  };
}
