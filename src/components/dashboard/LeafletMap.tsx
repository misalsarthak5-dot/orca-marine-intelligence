'use client';

import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { MapLayerType } from '@/types';
import { pfzZones } from '@/data/mockPFZData';
import { avoidZones, recommendedRoute } from '@/data/mockRoutes';
import { marineAlerts } from '@/data/mockAlerts';

export interface MapControls {
  zoomIn: () => void;
  zoomOut: () => void;
  recenter: () => void;
}

interface LeafletMapProps {
  activeLayers: MapLayerType[];
  onMapReady?: (controls: MapControls) => void;
}

// Mumbai center coordinates
const MUMBAI_CENTER: [number, number] = [18.94, 72.84];
const DEFAULT_ZOOM = 11;

// Vessel position
const VESSEL_POS: [number, number] = [18.9398, 72.8347];

export default function LeafletMap({ activeLayers, onMapReady }: LeafletMapProps) {
  const mapRef = useRef<L.Map | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const layerGroupsRef = useRef<Record<string, L.LayerGroup>>({});

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    // Initialize map
    const map = L.map(containerRef.current, {
      center: MUMBAI_CENTER,
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

    mapRef.current = map;

    if (onMapReady) {
      onMapReady({
        zoomIn: () => map.zoomIn(),
        zoomOut: () => map.zoomOut(),
        recenter: () => map.setView(MUMBAI_CENTER, DEFAULT_ZOOM),
      });
    }

    // ── Create layer groups ──────────────────────────────

    // Vessel marker
    const vesselIcon = L.divIcon({
      html: `<div style="width:28px;height:28px;background:#0d9488;border:3px solid white;border-radius:50%;box-shadow:0 2px 8px rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center;">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><path d="M2 21c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1 .6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/><path d="M19.38 20A11.6 11.6 0 0 0 21 14l-9-4-9 4c0 2.9.94 5.34 2.81 7.76"/><path d="M19 13V7a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v6"/><path d="M12 10v-4"/></svg>
      </div>`,
      className: '',
      iconSize: [28, 28],
      iconAnchor: [14, 14],
    });
    
    const vesselMarker = L.marker(VESSEL_POS, { icon: vesselIcon });
    vesselMarker.bindPopup(`
      <div style="font-family:Inter,sans-serif;">
        <div style="font-weight:700;font-size:12px;color:#0a1628;margin-bottom:4px;">INS-SAGAR-04</div>
        <div style="font-size:10px;color:#64748b;">Autonomous Drift Netter • in Sector 4</div>
        <div style="font-size:10px;color:#64748b;margin-top:4px;">Draft: 2.4m | Fuel: 84% | Status: Safe</div>
      </div>
    `);
    vesselMarker.addTo(map);

    // PFZ Layer
    const pfzLayer = L.layerGroup();
    pfzZones.forEach((zone) => {
      const color = zone.probability === 'high' ? '#22c55e' : '#eab308';
      const fillOpacity = zone.probability === 'high' ? 0.25 : 0.15;
      
      L.polygon(zone.boundary as [number, number][], {
        color,
        weight: 2,
        fillColor: color,
        fillOpacity,
        dashArray: zone.probability === 'medium' ? '5,5' : undefined,
      })
        .bindPopup(`
          <div style="font-family:Inter,sans-serif;">
            <div style="font-weight:700;font-size:12px;color:#0a1628;">${zone.name}</div>
            <div style="font-size:10px;color:#64748b;margin-top:2px;">Distance: ${zone.distance} | SST: ${zone.sst}</div>
            <div style="font-size:10px;color:#64748b;">Chlorophyll: ${zone.chlorophyll} | Risk: ${zone.marineRisk}</div>
            <div style="font-size:10px;color:#16a34a;margin-top:4px;font-weight:600;">${zone.recommendation}</div>
          </div>
        `)
        .addTo(pfzLayer);
      
      // PFZ label
      L.marker(zone.coordinates as [number, number], {
        icon: L.divIcon({
          html: `<div style="background:${color};color:white;font-size:9px;font-weight:700;padding:2px 6px;border-radius:4px;white-space:nowrap;font-family:Inter,sans-serif;box-shadow:0 1px 3px rgba(0,0,0,0.2);">${zone.name}</div>`,
          className: '',
          iconAnchor: [20, 10],
        }),
      }).addTo(pfzLayer);
    });
    layerGroupsRef.current['pfz'] = pfzLayer;

    // Risk layer
    const riskLayer = L.layerGroup();
    avoidZones.forEach((zone) => {
      const color = zone.severity === 'critical' ? '#ef4444' : '#f59e0b';
      L.polygon(zone.boundary as [number, number][], {
        color,
        weight: 2,
        fillColor: color,
        fillOpacity: 0.2,
        dashArray: '4,4',
      })
        .bindPopup(`
          <div style="font-family:Inter,sans-serif;">
            <div style="font-weight:700;font-size:12px;color:#dc2626;">${zone.label}</div>
            <div style="font-size:10px;color:#64748b;margin-top:2px;">${zone.reason}</div>
          </div>
        `)
        .addTo(riskLayer);
    });
    layerGroupsRef.current['risk'] = riskLayer;

    // Geofence layer
    const geofenceLayer = L.layerGroup();
    // Naval restricted zone
    L.polygon(avoidZones[2].boundary as [number, number][], {
      color: '#8b5cf6',
      weight: 2,
      fillColor: '#8b5cf6',
      fillOpacity: 0.1,
      dashArray: '8,4',
    })
      .bindPopup(`<div style="font-family:Inter,sans-serif;font-weight:700;font-size:12px;color:#7c3aed;">Restricted Zone — Naval Exercise</div>`)
      .addTo(geofenceLayer);
    layerGroupsRef.current['geofence'] = geofenceLayer;

    // Route layer
    const routeLayer = L.layerGroup();
    L.polyline(recommendedRoute.safeCorridorPath as [number, number][], {
      color: '#0d9488',
      weight: 3,
      opacity: 0.8,
      dashArray: '10,6',
    })
      .bindPopup(`
        <div style="font-family:Inter,sans-serif;">
          <div style="font-weight:700;font-size:12px;color:#0d9488;">Safe Corridor</div>
          <div style="font-size:10px;color:#64748b;margin-top:2px;">Distance: ${recommendedRoute.estimatedDistance} | ETA: ${recommendedRoute.estimatedTime}</div>
        </div>
      `)
      .addTo(routeLayer);

    // Route waypoints
    recommendedRoute.waypoints.forEach((wp) => {
      const dotColor = wp.type === 'start' ? '#0d9488' : wp.type === 'destination' ? '#22c55e' : '#64748b';
      L.circleMarker(wp.coordinates as [number, number], {
        radius: wp.type === 'waypoint' ? 4 : 6,
        color: dotColor,
        fillColor: dotColor,
        fillOpacity: 1,
        weight: 2,
      })
        .bindPopup(`<div style="font-family:Inter,sans-serif;font-weight:600;font-size:11px;">${wp.label}</div>`)
        .addTo(routeLayer);
    });
    layerGroupsRef.current['route'] = routeLayer;

    // Weather layer (simple markers for alerts)
    const weatherLayer = L.layerGroup();
    marineAlerts.forEach((alert) => {
      if (alert.coordinates) {
        const color = alert.severity === 'critical' ? '#ef4444' : '#f59e0b';
        L.circleMarker(alert.coordinates as [number, number], {
          radius: 16,
          color,
          fillColor: color,
          fillOpacity: 0.15,
          weight: 1.5,
        })
          .bindPopup(`
            <div style="font-family:Inter,sans-serif;">
              <div style="font-weight:700;font-size:12px;color:${color};">⚠ ${alert.title}</div>
              <div style="font-size:10px;color:#64748b;margin-top:2px;">${alert.description}</div>
            </div>
          `)
          .addTo(weatherLayer);
      }
    });
    layerGroupsRef.current['weather'] = weatherLayer;

    // SST layer (heatmap-like overlay)
    const sstLayer = L.layerGroup();
    // Simulate SST gradient with overlapping circles
    const sstPoints: [number, number, string][] = [
      [18.80, 72.50, 'rgba(255,120,50,0.12)'],
      [18.90, 72.70, 'rgba(255,140,60,0.10)'],
      [19.00, 72.80, 'rgba(255,160,70,0.08)'],
      [18.85, 72.45, 'rgba(255,100,40,0.14)'],
    ];
    sstPoints.forEach(([lat, lng, color]) => {
      L.circle([lat, lng], {
        radius: 8000,
        color: 'transparent',
        fillColor: color,
        fillOpacity: 1,
      }).addTo(sstLayer);
    });
    layerGroupsRef.current['sst'] = sstLayer;

    // Chlorophyll layer
    const chlorophyllLayer = L.layerGroup();
    const chlPoints: [number, number, string][] = [
      [18.85, 72.45, 'rgba(34,197,94,0.15)'],
      [18.70, 72.25, 'rgba(34,197,94,0.10)'],
      [19.15, 72.60, 'rgba(34,197,94,0.08)'],
    ];
    chlPoints.forEach(([lat, lng, color]) => {
      L.circle([lat, lng], {
        radius: 6000,
        color: 'transparent',
        fillColor: color,
        fillOpacity: 1,
      }).addTo(chlorophyllLayer);
    });
    layerGroupsRef.current['chlorophyll'] = chlorophyllLayer;

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
      if (activeLayers.includes(key as MapLayerType)) {
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

  return (
    <div
      ref={containerRef}
      className="absolute inset-0"
      style={{ zIndex: 1 }}
    />
  );
}
