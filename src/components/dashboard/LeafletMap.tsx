import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { LocationState, useLocation } from '@/lib/location';
import { MapLayerType, CandidateRoute, GeofenceZone } from '@/types';
import { fetchFastAPIPFZ, PFZAssessmentResponse, PFZAdvisory, PFZLineFeature } from '@/services/pfzService';
import { fetchFastAPIGeofences } from '@/services/geofenceService';

export interface MapControls {
  zoomIn: () => void;
  zoomOut: () => void;
  recenter: () => void;
}

interface LeafletMapProps {
  selectedLocation: LocationState;
  activeLayers: MapLayerType[];
  onMapReady?: (controls: MapControls) => void;
  /** Reflects real-time hazard severity from the Marine Hazards card */
  hazardCode?: 'clear' | 'caution' | 'high';
  /** Candidate route corridors from Route Intelligence */
  routes?: CandidateRoute[];
  recommendedRouteId?: string;
  selectedRouteId?: string;
  onSelectRoute?: (routeId: string) => void;
  destination?: { latitude: number; longitude: number; name: string };
  onMapClickCoordinates?: (lat: number, lon: number) => void;
}

const DEFAULT_ZOOM = 10;

function getSstColor(temp: number): { hex: string; bgRgba: string; label: string } {
  if (temp < 24) return { hex: '#3b82f6', bgRgba: 'rgba(59,130,246,0.18)', label: 'Cool Waters' };
  if (temp < 27) return { hex: '#06b6d4', bgRgba: 'rgba(6,182,212,0.18)', label: 'Moderate' };
  if (temp < 29) return { hex: '#f59e0b', bgRgba: 'rgba(245,158,11,0.20)', label: 'Warm Waters' };
  if (temp < 31) return { hex: '#f97316', bgRgba: 'rgba(249,115,22,0.22)', label: 'Very Warm' };
  return { hex: '#ef4444', bgRgba: 'rgba(239,68,68,0.25)', label: 'Elevated SST' };
}

function buildSstPopup(loc: LocationState, sst: number | null | undefined): string {
  const sstText = sst !== null && sst !== undefined && !isNaN(sst) ? `${sst.toFixed(1)} °C` : 'Telemetry pending';
  const info = sst !== null && sst !== undefined && !isNaN(sst) ? getSstColor(sst) : { hex: '#0d9488', bgRgba: '', label: 'Observation' };
  return `
    <div style="font-family:Inter,sans-serif;padding:4px;min-width:180px;line-height:1.4;">
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="font-size:12px;">🌡️</span>
        <span style="font-weight:700;font-size:10px;color:${info.hex};text-transform:uppercase;letter-spacing:0.5px;">Sea Surface Temperature</span>
      </div>
      <div style="font-weight:700;font-size:13px;color:#0a1628;margin-top:2px;">${loc.name}</div>
      <div style="font-size:17px;font-weight:900;color:#0a1628;margin-top:4px;">
        ${sstText}
      </div>
      <div style="font-size:10px;color:#475569;font-family:monospace;margin-top:2px;font-weight:600;">
        ${loc.latitude.toFixed(2)}°N, ${loc.longitude.toFixed(2)}°E
      </div>
      <div style="font-size:10px;color:#0d9488;margin-top:6px;font-weight:600;background:#f0fdfa;padding:3px 6px;border-radius:4px;border:1px solid #ccfbf1;">
        Point Observation / Model • Source: Open-Meteo Marine
      </div>
    </div>
  `;
}

function createSstIcon(sst: number | null | undefined) {
  const temp = sst !== null && sst !== undefined && !isNaN(sst) ? sst : 28.0;
  const info = getSstColor(temp);
  const label = sst !== null && sst !== undefined && !isNaN(sst) ? `${sst.toFixed(1)}°C` : 'SST';
  return L.divIcon({
    className: 'orca-sst-marker',
    html: `
      <div style="position:relative;width:48px;height:48px;display:flex;align-items:center;justify-content:center;">
        <div style="position:absolute;width:48px;height:48px;background:${info.bgRgba};border-radius:50%;animation:ping 3s cubic-bezier(0,0,0.2,1) infinite;"></div>
        <div style="background:${info.hex};color:#ffffff;border:2px solid #ffffff;border-radius:12px;padding:2px 6px;box-shadow:0 2px 8px rgba(0,0,0,0.3);font-size:10px;font-weight:800;font-family:Inter,sans-serif;white-space:nowrap;z-index:2;display:flex;align-items:center;gap:2px;">
          <span>🌡️</span>
          <span>${label}</span>
        </div>
      </div>
    `,
    iconSize: [48, 48],
    iconAnchor: [24, 24],
    popupAnchor: [0, -24],
  });
}

function buildAssessmentPopup(loc: LocationState): string {
  const harborText = loc.harborRef || 'ORCA Coast Origin';
  return `
    <div style="font-family:Inter,sans-serif;padding:4px;min-width:170px;line-height:1.4;">
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="font-size:12px;">⚓</span>
        <span style="font-weight:700;font-size:10px;color:#0d9488;text-transform:uppercase;letter-spacing:0.5px;">Coastal Origin</span>
      </div>
      <div style="font-weight:700;font-size:13px;color:#0a1628;margin-top:2px;">${loc.name}</div>
      <div style="font-size:10px;color:#0284c7;font-weight:600;margin-top:2px;">${harborText}</div>
      <div style="font-size:11px;color:#475569;font-family:monospace;margin-top:3px;font-weight:600;">
        ${loc.latitude.toFixed(4)}°N, ${loc.longitude.toFixed(4)}°E
      </div>
      <div style="font-size:10px;color:#059669;margin-top:5px;font-weight:600;background:#f0fdf4;padding:2px 6px;border-radius:4px;border:1px solid #bbf7d0;">
        Active Operational Anchor
      </div>
    </div>
  `;
}

function createOriginIcon(name: string, harborRef?: string) {
  const label = name.replace(' Coast', '');
  return L.divIcon({
    className: 'orca-origin-marker',
    html: `
      <div style="position:relative;display:flex;align-items:center;gap:5px;">
        <div style="position:relative;width:32px;height:32px;display:flex;align-items:center;justify-content:center;">
          <div style="position:absolute;width:32px;height:32px;background:rgba(13,148,136,0.35);border-radius:50%;animation:ping 2.5s cubic-bezier(0,0,0.2,1) infinite;"></div>
          <div style="width:24px;height:24px;background:#0d9488;border:2.5px solid #ffffff;border-radius:50%;box-shadow:0 2px 8px rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;color:#ffffff;font-size:11px;font-weight:bold;z-index:2;">
            ⚓
          </div>
        </div>
        <div style="background:rgba(10,22,40,0.9);backdrop-filter:blur(4px);color:#ffffff;border:1px solid rgba(255,255,255,0.25);border-radius:6px;padding:2px 6px;font-size:10px;font-weight:700;font-family:Inter,sans-serif;white-space:nowrap;box-shadow:0 2px 6px rgba(0,0,0,0.3);display:flex;align-items:center;gap:3px;">
          <span style="color:#2dd4bf;">⚓</span> ${label}
        </div>
      </div>
    `,
    iconSize: [140, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -16],
  });
}

function createDestinationIcon(name: string, isPfz: boolean = false) {
  const badgeLabel = isPfz ? 'PFZ Target' : 'Route Target';
  const badgeColor = isPfz ? '#10b981' : '#f87171';
  return L.divIcon({
    className: 'orca-dest-marker',
    html: `
      <div style="position:relative;display:flex;align-items:center;gap:5px;">
        <div style="position:relative;width:34px;height:34px;display:flex;align-items:center;justify-content:center;">
          <div style="position:absolute;width:34px;height:34px;background:rgba(239,68,68,0.35);border-radius:50%;animation:ping 2.5s cubic-bezier(0,0,0.2,1) infinite;"></div>
          <div style="width:26px;height:26px;background:#dc2626;border:2.5px solid #ffffff;border-radius:50%;box-shadow:0 2px 8px rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;color:#ffffff;font-size:12px;font-weight:bold;z-index:2;">
            🎯
          </div>
        </div>
        <div style="background:rgba(10,22,40,0.9);backdrop-filter:blur(4px);color:#ffffff;border:1px solid rgba(255,255,255,0.25);border-radius:6px;padding:2px 6px;font-size:10px;font-weight:700;font-family:Inter,sans-serif;white-space:nowrap;box-shadow:0 2px 6px rgba(0,0,0,0.3);display:flex;align-items:center;gap:3px;">
          <span style="color:${badgeColor};">${badgeLabel}:</span> ${name}
        </div>
      </div>
    `,
    iconSize: [170, 34],
    iconAnchor: [17, 17],
    popupAnchor: [0, -17],
  });
}

function createSelectionIcon() {
  return L.divIcon({
    className: 'orca-selected-marker',
    html: `
      <div style="position:relative;width:36px;height:36px;display:flex;align-items:center;justify-content:center;">
        <div style="position:absolute;width:36px;height:36px;background:rgba(13,148,136,0.35);border-radius:50%;animation:ping 2s cubic-bezier(0,0,0.2,1) infinite;"></div>
        <div style="width:24px;height:24px;background:#0d9488;border:3px solid #ffffff;border-radius:50%;box-shadow:0 3px 12px rgba(0,0,0,0.45);display:flex;align-items:center;justify-content:center;z-index:2;">
          <div style="width:8px;height:8px;background:#ffffff;border-radius:50%;"></div>
        </div>
      </div>
    `,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
    popupAnchor: [0, -18],
  });
}

function buildHazardPopup(loc: LocationState, severity: string = 'caution'): string {
  const severityLabel = severity === 'high' ? 'HIGH ALERT' : severity === 'clear' ? 'NO SIGNIFICANT HAZARDS' : 'CAUTION';
  const severityColor = severity === 'high' ? '#dc2626' : severity === 'clear' ? '#059669' : '#d97706';
  return `
    <div style="font-family:Inter,sans-serif;padding:4px;min-width:170px;line-height:1.4;">
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="font-size:12px;">${severity === 'clear' ? '✅' : severity === 'high' ? '🔴' : '⚠️'}</span>
        <span style="font-weight:700;font-size:10px;color:${severityColor};text-transform:uppercase;letter-spacing:0.5px;">${severityLabel}</span>
      </div>
      <div style="font-weight:700;font-size:13px;color:#0a1628;margin-top:2px;">${loc.name}</div>
      <div style="font-size:11px;color:#475569;font-family:monospace;margin-top:2px;font-weight:600;">
        ${loc.latitude.toFixed(2)}°N, ${loc.longitude.toFixed(2)}°E
      </div>
      <div style="font-size:10px;color:#0d9488;margin-top:6px;font-weight:600;background:#f0fdfa;padding:3px 6px;border-radius:4px;border:1px solid #ccfbf1;">
        Monitored Coastal Sector • Open-Meteo
      </div>
    </div>
  `;
}

function createHazardIcon(severity: 'clear' | 'caution' | 'high' = 'caution') {
  const bg = severity === 'high' ? '#dc2626' : severity === 'clear' ? '#059669' : '#d97706';
  const pulse = severity === 'high' ? 'rgba(220,38,38,0.3)' : severity === 'clear' ? 'rgba(5,150,105,0.25)' : 'rgba(217,119,6,0.3)';
  const icon = severity === 'clear' ? '✓' : '⚠';
  return L.divIcon({
    className: 'orca-hazard-marker',
    html: `
      <div style="position:relative;width:34px;height:34px;display:flex;align-items:center;justify-content:center;">
        <div style="position:absolute;width:34px;height:34px;background:${pulse};border-radius:50%;animation:ping 2.5s cubic-bezier(0,0,0.2,1) infinite;"></div>
        <div style="width:26px;height:26px;background:${bg};border:2px solid #ffffff;border-radius:50%;box-shadow:0 2px 8px rgba(0,0,0,0.35);display:flex;align-items:center;justify-content:center;color:#ffffff;font-size:13px;font-weight:bold;z-index:2;">
          ${icon}
        </div>
      </div>
    `,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
    popupAnchor: [0, -17],
  });
}

function buildIncoisPfzLinePopup(line: PFZLineFeature): string {
  return `
    <div style="font-family:Inter,sans-serif;padding:4px;min-width:190px;line-height:1.4;">
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="font-size:12px;">🌊</span>
        <span style="font-weight:700;font-size:10px;color:#059669;text-transform:uppercase;letter-spacing:0.5px;">Potential Fishing Zone (PFZ Line)</span>
      </div>
      <div style="font-weight:700;font-size:13px;color:#0a1628;margin-top:2px;">UID: ${line.uid || 'INCOIS-PFZ'}</div>
      <div style="font-size:11px;color:#334155;margin-top:2px;">
        <strong>Sector/State:</strong> ${line.state_name || 'Coastal Sector'}
      </div>
      <div style="font-size:11px;color:#334155;">
        <strong>Advisory:</strong> Julian Day ${line.julian_day ?? '—'}, ${line.year ?? '—'}
      </div>
      <div style="font-size:11px;color:#334155;">
        <strong>Front Type:</strong> ${line.category || 'Thermal / Ocean Color Front'}
      </div>
      ${line.length_km ? `<div style="font-size:11px;color:#334155;"><strong>Line Length:</strong> ${line.length_km} km</div>` : ''}
      <div style="font-size:11px;color:#334155;">
        <strong>Distance from location:</strong> ${line.distance_km} km
      </div>
      <div style="font-size:10px;color:#059669;margin-top:6px;font-weight:600;background:#ecfdf5;padding:3px 6px;border-radius:4px;border:1px solid #a7f3d0;">
        Source: INCOIS — Official PFZ Lines WFS
      </div>
    </div>
  `;
}

function buildIncoisLandingCentrePopup(advisory: PFZAdvisory): string {
  const distRange = advisory.advisory_distance_from_km && advisory.advisory_distance_to_km
    ? `${advisory.advisory_distance_from_km}–${advisory.advisory_distance_to_km} km`
    : `${advisory.distance_from_query_km} km`;
  const depthRange = advisory.depth_from_m !== null && advisory.depth_to_m !== null
    ? `${advisory.depth_from_m}–${advisory.depth_to_m} m`
    : 'Coastal shelf';

  return `
    <div style="font-family:Inter,sans-serif;padding:4px;min-width:210px;line-height:1.4;">
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="font-size:12px;">📍</span>
        <span style="font-weight:700;font-size:10px;color:#059669;text-transform:uppercase;letter-spacing:0.5px;">INCOIS Landing Centre Advisory</span>
      </div>
      <div style="font-weight:700;font-size:13px;color:#0a1628;margin-top:2px;">${advisory.landing_center}</div>
      ${advisory.district ? `<div style="font-size:10px;color:#64748b;font-weight:600;">${advisory.district}${advisory.sector ? ` • ${advisory.sector}` : ''}</div>` : ''}
      <div style="margin-top:4px;padding:4px 6px;background:#f0fdf4;border-radius:4px;border:1px solid #bbf7d0;">
        <div style="font-size:11px;color:#166534;font-weight:700;">
          PFZ Vector: ${distRange} ${advisory.direction || ''} ${advisory.bearing_degrees !== null && advisory.bearing_degrees !== undefined ? `(${advisory.bearing_degrees}° Bearing)` : ''}
        </div>
        <div style="font-size:11px;color:#166534;margin-top:2px;">
          Depth Range: ${depthRange}
        </div>
      </div>
      ${advisory.target_dms ? `
        <div style="font-size:10px;color:#334155;margin-top:4px;font-family:monospace;">
          Target DMS: ${advisory.target_dms.latitude}, ${advisory.target_dms.longitude}
        </div>
      ` : ''}
      <div style="font-size:10px;color:#475569;margin-top:3px;">
        <strong>Advisory Validity:</strong> ${advisory.validity_formatted || advisory.validity_date || '28-Apr-2024'}
      </div>
      <div style="font-size:10px;color:#475569;">
        <strong>Dataset Updated:</strong> ${advisory.dataset_updated || '29-Apr-2024'}
      </div>
      <div style="font-size:10px;color:#059669;margin-top:6px;font-weight:600;background:#ecfdf5;padding:3px 6px;border-radius:4px;border:1px solid #a7f3d0;">
        Source: INCOIS — Official PFZ Advisory
      </div>
    </div>
  `;
}

function createLandingCentreIcon(name: string, distFromQuery: number) {
  return L.divIcon({
    className: 'orca-lc-marker',
    html: `
      <div style="position:relative;display:flex;align-items:center;gap:4px;">
        <div style="width:22px;height:22px;background:#059669;border:2px solid #ffffff;border-radius:50%;box-shadow:0 2px 6px rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center;color:#ffffff;font-size:10px;font-weight:bold;">
          ⚓
        </div>
        <div style="background:rgba(10,22,40,0.85);backdrop-filter:blur(4px);color:#ffffff;border:1px solid rgba(255,255,255,0.2);border-radius:4px;padding:1px 5px;font-size:9px;font-weight:600;font-family:Inter,sans-serif;white-space:nowrap;box-shadow:0 1px 4px rgba(0,0,0,0.25);">
          ${name} (${distFromQuery}km)
        </div>
      </div>
    `,
    iconSize: [120, 24],
    iconAnchor: [11, 12],
    popupAnchor: [0, -12],
  });
}

function buildGeofencePopup(zone: GeofenceZone): string {
  return `
    <div style="font-family:Inter,sans-serif;padding:4px;min-width:180px;line-height:1.4;">
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="font-size:12px;">⛔</span>
        <span style="font-weight:700;font-size:10px;color:#dc2626;text-transform:uppercase;letter-spacing:0.5px;">Restricted Maritime Zone</span>
      </div>
      <div style="font-weight:700;font-size:13px;color:#0a1628;margin-top:2px;">${zone.name}</div>
      <div style="font-size:11px;color:#64748b;margin-top:2px;">
        <strong>Type:</strong> ${zone.zone_type || 'Restricted Area'}
      </div>
      ${zone.authority ? `<div style="font-size:11px;color:#64748b;"><strong>Authority:</strong> ${zone.authority}</div>` : ''}
      <div style="font-size:10px;color:#dc2626;margin-top:6px;font-weight:600;background:#fef2f2;padding:3px 6px;border-radius:4px;border:1px solid #fecaca;">
        Avoidance Required • Official Maritime Restriction
      </div>
    </div>
  `;
}

function buildRoutePopup(route: CandidateRoute, isRecommended: boolean): string {
  const badgeColor = route.risk_level === 'LOW' ? '#059669' : route.risk_level === 'CAUTION' ? '#d97706' : '#dc2626';
  const badgeBg = route.risk_level === 'LOW' ? '#ecfdf5' : route.risk_level === 'CAUTION' ? '#fffbeb' : '#fef2f2';

  const restrStatus = route.restriction_status || 'UNAVAILABLE';
  const restrLabel = restrStatus === 'RESTRICTED' ? 'RESTRICTED' : restrStatus === 'CLEAR' ? 'GEOFENCE CLEAR' : 'GEOFENCE UNAVAILABLE';
  const restrColor = restrStatus === 'RESTRICTED' ? '#dc2626' : restrStatus === 'CLEAR' ? '#059669' : '#64748b';
  const restrBg = restrStatus === 'RESTRICTED' ? '#fef2f2' : restrStatus === 'CLEAR' ? '#ecfdf5' : '#f1f5f9';

  const overallStatus = route.overall_status || 'ENVIRONMENTAL_ANALYSIS_ONLY';
  const overallLabel = overallStatus === 'VIABLE' ? 'VIABLE' : overallStatus === 'NOT_VIABLE' ? 'NOT VIABLE' : 'ENV. ANALYSIS ONLY';
  const overallBg = overallStatus === 'VIABLE' ? '#059669' : overallStatus === 'NOT_VIABLE' ? '#dc2626' : '#334155';

  return `
    <div style="font-family:Inter,sans-serif;padding:6px;min-width:230px;line-height:1.4;">
      <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">
        <span style="font-weight:800;font-size:13px;color:#0a1628;">${route.name}</span>
        ${isRecommended ? '<span style="background:#0d9488;color:#fff;font-size:9px;font-weight:800;padding:2px 6px;border-radius:4px;text-transform:uppercase;letter-spacing:0.5px;">RECOMMENDED</span>' : ''}
      </div>
      <div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px;margin-top:6px;">
        <span style="background:${badgeBg};color:${badgeColor};border:1px solid ${badgeColor};font-size:10px;font-weight:700;padding:2px 6px;border-radius:5px;">
          Risk: ${route.risk_score}/100 • ${route.risk_level}
        </span>
        <span style="background:${restrBg};color:${restrColor};border:1px solid ${restrColor};font-size:10px;font-weight:700;padding:2px 6px;border-radius:5px;">
          ${restrLabel}
        </span>
        <span style="background:${overallBg};color:#ffffff;font-size:9px;font-weight:800;padding:2px 6px;border-radius:5px;">
          ${overallLabel}
        </span>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px;font-size:11px;background:#f8fafc;padding:7px;border-radius:6px;border:1px solid #e2e8f0;">
        <div>
          <span style="color:#64748b;font-size:9px;font-weight:600;text-transform:uppercase;display:block;">Distance</span>
          <strong style="color:#0f172a;font-size:12px;">${route.distance_km} km</strong>
        </div>
        <div>
          <span style="color:#64748b;font-size:9px;font-weight:600;text-transform:uppercase;display:block;">Est. Transit</span>
          <strong style="color:#0f172a;font-size:12px;">${route.estimated_time_hours} hrs</strong>
        </div>
        <div>
          <span style="color:#64748b;font-size:9px;font-weight:600;text-transform:uppercase;display:block;">Peak Waves</span>
          <strong style="color:#0f172a;font-size:12px;">${route.conditions?.peak_wave_m ?? '—'} m</strong>
        </div>
        <div>
          <span style="color:#64748b;font-size:9px;font-weight:600;text-transform:uppercase;display:block;">Peak Wind</span>
          <strong style="color:#0f172a;font-size:12px;">${route.conditions?.peak_wind_kt ?? '—'} kts</strong>
        </div>
      </div>
      <div style="font-size:10px;color:#475569;margin-top:7px;line-height:1.35;">
        ${route.description}
      </div>
      ${route.geofence_note ? `<div style="font-size:9px;color:#64748b;margin-top:4px;font-style:italic;">${route.geofence_note}</div>` : ''}
    </div>
  `;
}

export default function LeafletMap({
  selectedLocation,
  activeLayers,
  onMapReady,
  hazardCode = 'caution',
  routes,
  recommendedRouteId,
  selectedRouteId,
  onSelectRoute,
  destination,
  onMapClickCoordinates,
}: LeafletMapProps) {
  const { selectPointFromMap, liveData } = useLocation();
  const mapRef = useRef<L.Map | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const layerGroupsRef = useRef<Record<string, L.LayerGroup>>({});
  const selectionMarkerRef = useRef<L.Marker | null>(null);
  const selectedLocationRef = useRef(selectedLocation);
  const routePolylinesRef = useRef<Record<string, L.Polyline>>({});
  const onMapClickCoordinatesRef = useRef(onMapClickCoordinates);

  useEffect(() => {
    selectedLocationRef.current = selectedLocation;
  }, [selectedLocation]);

  useEffect(() => {
    onMapClickCoordinatesRef.current = onMapClickCoordinates;
  }, [onMapClickCoordinates]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const initialCenter: [number, number] = [
      selectedLocationRef.current.latitude,
      selectedLocationRef.current.longitude,
    ];

    const initialZoom = selectedLocationRef.current.mapZoom || DEFAULT_ZOOM;

    // Initialize map
    const map = L.map(containerRef.current, {
      center: initialCenter,
      zoom: initialZoom,
      zoomControl: false,
      attributionControl: false,
    });

    // Dedicated route pane with zIndex 550 (above overlayPane 400, below markerPane 600)
    // Ensures route polylines are strictly visible above SST halos, hazard circles, and PFZ lines.
    const routePane = map.createPane('routePane');
    routePane.style.zIndex = '550';

    // Connect CARTO basemap with API key from environment variable
    const cartoApiKey = process.env.NEXT_PUBLIC_CARTO_API_KEY;
    const basemapUrl = cartoApiKey
      ? `https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png?key=${encodeURIComponent(cartoApiKey)}`
      : 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';

    L.tileLayer(basemapUrl, {
      subdomains: 'abcd',
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>, &copy; <a href="https://carto.com/attributions">CARTO</a>',
    }).addTo(map);

    // Initial selected assessment point marker (Origin marker)
    const marker = L.marker(initialCenter, {
      icon: createOriginIcon(selectedLocationRef.current.name, selectedLocationRef.current.harborRef),
      zIndexOffset: 10000,
    });
    marker.bindPopup(buildAssessmentPopup(selectedLocationRef.current));
    marker.addTo(map);
    selectionMarkerRef.current = marker;

    // Map click event listener for location selection or destination picking
    map.on('click', async (e: L.LeafletMouseEvent) => {
      if (onMapClickCoordinatesRef.current) {
        onMapClickCoordinatesRef.current(e.latlng.lat, e.latlng.lng);
      } else {
        await selectPointFromMap(e.latlng.lat, e.latlng.lng);
      }
    });

    mapRef.current = map;

    // Ensure tiles render correctly after mount
    setTimeout(() => map.invalidateSize(), 200);

    if (onMapReady) {
      onMapReady({
        zoomIn: () => map.zoomIn(),
        zoomOut: () => map.zoomOut(),
        recenter: () => {
          const loc = selectedLocationRef.current;
          map.flyTo([loc.latitude, loc.longitude], DEFAULT_ZOOM, { duration: 1.0 });
          if (selectionMarkerRef.current) {
            selectionMarkerRef.current.openPopup();
          }
        },
      });
    }

    // Dynamic layer groups
    layerGroupsRef.current['pfz'] = L.layerGroup();
    layerGroupsRef.current['risk'] = L.layerGroup();
    layerGroupsRef.current['geofence'] = L.layerGroup();
    layerGroupsRef.current['route'] = L.layerGroup();
    layerGroupsRef.current['weather'] = L.layerGroup();
    layerGroupsRef.current['sst'] = L.layerGroup();
    layerGroupsRef.current['chlorophyll'] = L.layerGroup();
    layerGroupsRef.current['hazards'] = L.layerGroup();

    // Event listener for external fit-bounds trigger (e.g. from "View Routes on Map")
    const handleFitBoundsEvent = (e: any) => {
      if (!mapRef.current) return;
      const coords = e.detail?.coordinates as [number, number][] | undefined;
      if (coords && coords.length > 1) {
        const bounds = L.latLngBounds(coords);
        mapRef.current.fitBounds(bounds, { padding: [50, 50], maxZoom: 12 });
      }
    };
    window.addEventListener('orca:fit-route-bounds', handleFitBoundsEvent);

    return () => {
      window.removeEventListener('orca:fit-route-bounds', handleFitBoundsEvent);
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Toggle layers based on activeLayers prop
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    Object.entries(layerGroupsRef.current).forEach(([key, layer]) => {
      const shouldShow = activeLayers.includes(key as MapLayerType);
      if (shouldShow) {
        if (!map.hasLayer(layer)) {
          layer.addTo(map);
        }
      } else {
        if (map.hasLayer(layer)) {
          map.removeLayer(layer);
        }
      }
    });
  }, [activeLayers]);

  // Dynamically update Hazards layer marker for active location
  useEffect(() => {
    const hazardsLayer = layerGroupsRef.current['hazards'];
    if (!hazardsLayer) return;

    hazardsLayer.clearLayers();

    if (activeLayers.includes('hazards')) {
      const targetPos: [number, number] = [selectedLocation.latitude, selectedLocation.longitude];

      // Sector perimeter color varies by hazard severity
      const circleColor = hazardCode === 'high' ? '#dc2626' : hazardCode === 'clear' ? '#059669' : '#d97706';
      const fillColor = hazardCode === 'high' ? '#ef4444' : hazardCode === 'clear' ? '#10b981' : '#f59e0b';

      // Sector perimeter circle
      const sectorCircle = L.circle(targetPos, {
        radius: 4500,
        color: circleColor,
        fillColor: fillColor,
        fillOpacity: 0.12,
        weight: 1.5,
        dashArray: '6,6',
      });
      sectorCircle.bindPopup(buildHazardPopup(selectedLocation, hazardCode));
      sectorCircle.addTo(hazardsLayer);

      // Warning marker
      const hazardMarker = L.marker(targetPos, {
        icon: createHazardIcon(hazardCode),
        zIndexOffset: 9500,
      });
      hazardMarker.bindPopup(buildHazardPopup(selectedLocation, hazardCode));
      hazardMarker.addTo(hazardsLayer);
    }
  }, [selectedLocation, activeLayers, hazardCode]);

  // Dynamically update SST layer marker for active location and real Open-Meteo SST
  useEffect(() => {
    const sstLayer = layerGroupsRef.current['sst'];
    if (!sstLayer) return;

    sstLayer.clearLayers();

    if (activeLayers.includes('sst')) {
      const sst = liveData?.current.seaSurfaceTemperature ?? null;
      const targetPos: [number, number] = [selectedLocation.latitude, selectedLocation.longitude];
      const info = sst !== null && sst !== undefined && !isNaN(sst) ? getSstColor(sst) : { hex: '#0d9488', bgRgba: 'rgba(13,148,136,0.18)', label: 'Observation' };

      // SST thermal observation halo around location
      const haloCircle = L.circle(targetPos, {
        radius: 6000,
        color: info.hex,
        fillColor: info.hex,
        fillOpacity: 0.15,
        weight: 1.5,
      });
      haloCircle.bindPopup(buildSstPopup(selectedLocation, sst));
      haloCircle.addTo(sstLayer);

      // SST Marker
      const sstMarker = L.marker(targetPos, {
        icon: createSstIcon(sst),
        zIndexOffset: 9200,
      });
      sstMarker.bindPopup(buildSstPopup(selectedLocation, sst));
      sstMarker.addTo(sstLayer);
    }
  }, [selectedLocation, activeLayers, liveData]);

  // Dynamically update Geofence / Restriction layer for active location
  useEffect(() => {
    const geofenceLayer = layerGroupsRef.current['geofence'];
    if (!geofenceLayer) return;

    geofenceLayer.clearLayers();

    if (!activeLayers.includes('geofence')) return;

    let isMounted = true;

    fetchFastAPIGeofences(selectedLocation.latitude, selectedLocation.longitude)
      .then((data) => {
        if (!isMounted) return;
        const map = mapRef.current;

        if (data.zones && data.zones.length > 0) {
          data.zones.forEach((zone) => {
            const geoJsonLayer = L.geoJSON(zone.geometry as any, {
              style: {
                color: '#dc2626',
                fillColor: '#ef4444',
                fillOpacity: 0.22,
                weight: 2,
                dashArray: '5,5',
              },
            });
            geoJsonLayer.bindPopup(buildGeofencePopup(zone));
            geoJsonLayer.addTo(geofenceLayer);
          });
        }

        if (map && activeLayers.includes('geofence') && !map.hasLayer(geofenceLayer)) {
          geofenceLayer.addTo(map);
        }
      })
      .catch((err) => {
        console.warn('[LeafletMap] Failed to render Geofence layer:', err);
      });

    return () => {
      isMounted = false;
    };
  }, [selectedLocation, activeLayers]);

  // Dynamically update real INCOIS PFZ layer (Lines & Landing Centre Advisories) for active location
  useEffect(() => {
    const pfzLayer = layerGroupsRef.current['pfz'];
    if (!pfzLayer) return;

    pfzLayer.clearLayers();

    if (!activeLayers.includes('pfz')) return;

    let isMounted = true;

    fetchFastAPIPFZ(selectedLocation.latitude, selectedLocation.longitude)
      .then((data) => {
        if (!isMounted) return;
        const map = mapRef.current;

        // 1. Render Real INCOIS PFZ Lines (MultiLineString / LineString GeoJSON across Indian coastline)
        const linesToRender = (data.nationwide_pfz_lines && data.nationwide_pfz_lines.length > 0)
          ? data.nationwide_pfz_lines
          : (data.pfz_lines || []);

        if (linesToRender.length > 0) {
          linesToRender.forEach((line) => {
            const geoJsonLayer = L.geoJSON(line.geometry as any, {
              style: {
                color: '#10b981', // vibrant emerald
                weight: 3.5,
                opacity: 0.9,
                lineCap: 'round',
                lineJoin: 'round',
              },
            });

            geoJsonLayer.bindPopup(buildIncoisPfzLinePopup(line));
            geoJsonLayer.on('click', (e) => {
              L.DomEvent.stopPropagation(e);
            });
            geoJsonLayer.on('mouseover', function (this: any) {
              if (this.setStyle) {
                this.setStyle({ weight: 5.5, color: '#34d399' });
              }
            });
            geoJsonLayer.on('mouseout', function (this: any) {
              if (this.setStyle) {
                this.setStyle({ weight: 3.5, color: '#10b981' });
              }
            });

            geoJsonLayer.addTo(pfzLayer);
          });
        }

        // 2. Render Active Landing Centre Advisories as reference
        if (data.active_advisories && data.active_advisories.length > 0) {
          data.active_advisories.forEach((adv) => {
            const lcLat = adv.lc_coordinates.latitude;
            const lcLon = adv.lc_coordinates.longitude;

            // Landing centre reference marker
            const lcMarker = L.marker([lcLat, lcLon], {
              icon: createLandingCentreIcon(adv.landing_center, adv.distance_from_query_km),
              zIndexOffset: 9400,
            });
            lcMarker.bindPopup(buildIncoisLandingCentrePopup(adv));
            lcMarker.on('click', (e) => {
              L.DomEvent.stopPropagation(e);
            });
            lcMarker.addTo(pfzLayer);

            // If bearing degrees available, draw advisory vector line
            if (adv.bearing_degrees !== null && adv.bearing_degrees !== undefined) {
              const rayDistKm = adv.advisory_distance_to_km || adv.advisory_distance_from_km || 25;
              const rad = (adv.bearing_degrees * Math.PI) / 180;
              const endLat = lcLat + (rayDistKm / 111.0) * Math.cos(rad);
              const endLon = lcLon + (rayDistKm / (111.0 * Math.cos((lcLat * Math.PI) / 180))) * Math.sin(rad);

              const rayPoly = L.polyline([[lcLat, lcLon], [endLat, endLon]], {
                color: '#059669',
                weight: 2,
                dashArray: '5,5',
                opacity: 0.65,
              });
              rayPoly.bindPopup(buildIncoisLandingCentrePopup(adv));
              rayPoly.addTo(pfzLayer);
            }
          });
        }

        // Ensure layer is displayed if active
        if (map && activeLayers.includes('pfz') && !map.hasLayer(pfzLayer)) {
          pfzLayer.addTo(map);
        }
      })
      .catch((err) => {
        console.warn('[LeafletMap] Failed to render INCOIS PFZ layer:', err);
      });

    return () => {
      isMounted = false;
    };
  }, [selectedLocation, activeLayers]);

  // Update map view and selection marker whenever selectedLocation changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    // Close any open popups so they don't linger across location switches
    map.closePopup();

    const targetPos: [number, number] = [selectedLocation.latitude, selectedLocation.longitude];
    const zoomLevel = selectedLocation.mapZoom || 10;

    // Smoothly fly to the selected location if not in a route view with active bounds
    if (!routes || routes.length === 0) {
      map.flyTo(targetPos, zoomLevel, { duration: 1.2 });
    }

    // Ensure map renders correctly after location change
    setTimeout(() => map.invalidateSize(), 300);

    const popupHtml = buildAssessmentPopup(selectedLocation);

    if (selectionMarkerRef.current) {
      selectionMarkerRef.current.setLatLng(targetPos);
      selectionMarkerRef.current.setIcon(createOriginIcon(selectedLocation.name, selectedLocation.harborRef));
      selectionMarkerRef.current.setPopupContent(popupHtml);
    } else {
      const marker = L.marker(targetPos, {
        icon: createOriginIcon(selectedLocation.name, selectedLocation.harborRef),
        zIndexOffset: 10000,
      });
      marker.bindPopup(popupHtml);
      marker.addTo(map);
      selectionMarkerRef.current = marker;
    }
  }, [selectedLocation, routes]);

  // Dynamic Route Corridors, Origin & Destination Markers on dedicated routePane (zIndex 550)
  useEffect(() => {
    const routeLayer = layerGroupsRef.current['route'];
    const map = mapRef.current;
    if (!routeLayer || !map) return;

    routeLayer.clearLayers();
    routePolylinesRef.current = {};

    const isRouteLayerActive = activeLayers.includes('route');
    if (!isRouteLayerActive || !routes || routes.length === 0) {
      return;
    }

    const allCorridorLatLngs: [number, number][] = [];

    // 1. Origin Departure Marker
    const originPos: [number, number] = [selectedLocation.latitude, selectedLocation.longitude];
    allCorridorLatLngs.push(originPos);

    const originMarker = L.marker(originPos, {
      icon: createOriginIcon(selectedLocation.name, selectedLocation.harborRef),
      zIndexOffset: 9600,
    });
    originMarker.bindPopup(`
      <div style="font-family:Inter,sans-serif;padding:4px;min-width:160px;">
        <div style="color:#0d9488;font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:0.5px;">Departure Origin</div>
        <div style="font-weight:700;font-size:13px;color:#0a1628;margin-top:2px;">${selectedLocation.name}</div>
        <div style="font-size:10px;color:#0284c7;font-weight:600;margin-top:2px;">${selectedLocation.harborRef || 'ORCA Coast Origin'}</div>
        <div style="font-size:10px;color:#64748b;font-family:monospace;margin-top:2px;">
          ${selectedLocation.latitude.toFixed(4)}°N, ${selectedLocation.longitude.toFixed(4)}°E
        </div>
      </div>
    `);
    originMarker.addTo(routeLayer);

    // 2. Destination Target Marker
    if (destination && destination.latitude && destination.longitude) {
      const destPos: [number, number] = [destination.latitude, destination.longitude];
      allCorridorLatLngs.push(destPos);

      const isPfzTarget = Boolean(destination.name.includes('PFZ') || destination.name.includes('INCOIS'));

      const destMarker = L.marker(destPos, {
        icon: createDestinationIcon(destination.name, isPfzTarget),
        zIndexOffset: 9700,
      });
      destMarker.bindPopup(`
        <div style="font-family:Inter,sans-serif;padding:4px;min-width:180px;">
          <div style="color:${isPfzTarget ? '#059669' : '#dc2626'};font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:0.5px;">
            ${isPfzTarget ? 'Official INCOIS PFZ Target' : 'Selected Route Destination'}
          </div>
          <div style="font-weight:700;font-size:13px;color:#0a1628;margin-top:2px;">${destination.name}</div>
          <div style="font-size:10px;color:#64748b;font-family:monospace;margin-top:2px;">
            ${destination.latitude.toFixed(4)}°N, ${destination.longitude.toFixed(4)}°E
          </div>
        </div>
      `);
      destMarker.addTo(routeLayer);
    }

    // 3. Render ALL 3 Candidate Route Corridors onto dedicated routePane
    routes.forEach((r) => {
      const isRec = r.id === recommendedRouteId;
      const isSel = r.id === selectedRouteId;
      
      // Strict coordinate order: Leaflet expects [latitude, longitude]
      const latlngs: [number, number][] = r.coordinates.map((c) => [c[0], c[1]]);
      allCorridorLatLngs.push(...latlngs);

      // Distinct styling:
      // Recommended: Thick solid line (#0d9488)
      // Alternative corridors: Thinner dashed lines (#0284c7 for Northern, #7c3aed for Southern)
      let corridorColor = '#0d9488';
      if (!isRec) {
        if (r.id === 'route_2') corridorColor = '#0284c7'; // Northern Corridor (Cyan/Sky)
        else if (r.id === 'route_3') corridorColor = '#7c3aed'; // Southern Corridor (Violet/Indigo)
        else corridorColor = r.risk_level === 'LOW' ? '#10b981' : r.risk_level === 'CAUTION' ? '#f59e0b' : '#ef4444';
      }

      const routeWeight = isRec ? (isSel ? 6.5 : 5.5) : (isSel ? 4.5 : 3.5);
      const routeOpacity = isRec ? 0.95 : (isSel ? 0.9 : 0.75);

      // Render outer glow for recommended route
      if (isRec) {
        const glowPoly = L.polyline(latlngs, {
          pane: 'routePane',
          color: '#2dd4bf',
          weight: routeWeight + 4,
          opacity: 0.35,
          lineCap: 'round',
          lineJoin: 'round',
        });
        glowPoly.addTo(routeLayer);
      }

      // Main corridor polyline
      const poly = L.polyline(latlngs, {
        pane: 'routePane',
        color: corridorColor,
        weight: routeWeight,
        opacity: routeOpacity,
        dashArray: isRec ? undefined : '7, 8',
        lineCap: 'round',
        lineJoin: 'round',
      });

      // Bind detailed interactive popup
      poly.bindPopup(buildRoutePopup(r, isRec));

      // User interaction: click to select route & show popup
      poly.on('click', (e) => {
        L.DomEvent.stopPropagation(e);
        onSelectRoute?.(r.id);
        poly.openPopup(e.latlng);
      });

      poly.on('mouseover', function (this: any) {
        if (this.setStyle) {
          this.setStyle({ weight: routeWeight + 2, opacity: 1.0 });
        }
      });

      poly.on('mouseout', function (this: any) {
        if (this.setStyle) {
          this.setStyle({ weight: routeWeight, opacity: routeOpacity });
        }
      });

      poly.addTo(routeLayer);
      routePolylinesRef.current[r.id] = poly;
    });

    // Auto-fit bounds on route load or update (DO NOT automatically open popup)
    if (allCorridorLatLngs.length > 1) {
      const bounds = L.latLngBounds(allCorridorLatLngs);
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 12 });
    }

    if (!map.hasLayer(routeLayer)) {
      routeLayer.addTo(map);
    }
  }, [routes, recommendedRouteId, selectedRouteId, destination, activeLayers, selectedLocation, onSelectRoute]);

  return (
    <div
      ref={containerRef}
      className="absolute inset-0"
      style={{ zIndex: 1 }}
    />
  );
}
