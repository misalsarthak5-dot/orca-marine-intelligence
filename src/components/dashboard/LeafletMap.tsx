import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { LocationState, useLocation } from '@/lib/location';
import { MapLayerType } from '@/types';
import { fetchFastAPIPFZ, PFZAssessmentResponse, PFZAdvisory, PFZLineFeature } from '@/services/pfzService';

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
  return `
    <div style="font-family:Inter,sans-serif;padding:3px;min-width:145px;line-height:1.4;">
      <div style="font-weight:700;font-size:10px;color:#0d9488;text-transform:uppercase;letter-spacing:0.5px;">Selected Assessment Point</div>
      <div style="font-weight:700;font-size:13px;color:#0a1628;margin-top:2px;">${loc.name}</div>
      <div style="font-size:11px;color:#475569;font-family:monospace;margin-top:2px;font-weight:600;">
        ${loc.latitude.toFixed(2)}°N, ${loc.longitude.toFixed(2)}°E
      </div>
    </div>
  `;
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

export default function LeafletMap({ selectedLocation, activeLayers, onMapReady, hazardCode = 'caution' }: LeafletMapProps) {
  const { selectPointFromMap, liveData } = useLocation();
  const mapRef = useRef<L.Map | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const layerGroupsRef = useRef<Record<string, L.LayerGroup>>({});
  const selectionMarkerRef = useRef<L.Marker | null>(null);
  const selectedLocationRef = useRef(selectedLocation);

  useEffect(() => {
    selectedLocationRef.current = selectedLocation;
  }, [selectedLocation]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const initialCenter: [number, number] = [
      selectedLocationRef.current.latitude,
      selectedLocationRef.current.longitude,
    ];

    // Initialize map
    const map = L.map(containerRef.current, {
      center: initialCenter,
      zoom: DEFAULT_ZOOM,
      zoomControl: false,
      attributionControl: false,
    });

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

    // Initial selected assessment point marker
    const marker = L.marker(initialCenter, {
      icon: createSelectionIcon(),
      zIndexOffset: 10000,
    });
    marker.bindPopup(buildAssessmentPopup(selectedLocationRef.current));
    marker.addTo(map);
    selectionMarkerRef.current = marker;

    // Map click event listener for location selection
    map.on('click', async (e: L.LeafletMouseEvent) => {
      await selectPointFromMap(e.latlng.lat, e.latlng.lng);
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

    return () => {
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

        // 2. Render Active Landing Centre Advisories
        if (data.active_advisories && data.active_advisories.length > 0) {
          data.active_advisories.forEach((adv) => {
            const lcLat = adv.lc_coordinates.latitude;
            const lcLon = adv.lc_coordinates.longitude;

            // Landing centre marker
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

    // Immediately close any open popups (e.g. Mumbai PFZ popups) so they never linger
    map.closePopup();

    const targetPos: [number, number] = [selectedLocation.latitude, selectedLocation.longitude];

    // Smoothly fly to the selected location
    map.flyTo(targetPos, 10, { duration: 1.2 });

    // Ensure map renders correctly after location change
    setTimeout(() => map.invalidateSize(), 300);

    const popupHtml = buildAssessmentPopup(selectedLocation);

    if (selectionMarkerRef.current) {
      selectionMarkerRef.current.setLatLng(targetPos);
      selectionMarkerRef.current.setPopupContent(popupHtml);
    } else {
      const marker = L.marker(targetPos, {
        icon: createSelectionIcon(),
        zIndexOffset: 10000,
      });
      marker.bindPopup(popupHtml);
      marker.addTo(map);
      selectionMarkerRef.current = marker;
    }
  }, [selectedLocation]);

  return (
    <div
      ref={containerRef}
      className="absolute inset-0"
      style={{ zIndex: 1 }}
    />
  );
}
