'use client';

import React, { useState, useCallback } from 'react';
import MarineMetrics from '@/components/dashboard/MarineMetrics';
import MarineMap from '@/components/dashboard/MarineMap';
import FishingSafetyAssessment from '@/components/dashboard/FishingSafetyAssessment';
import MarineHazardsAlerts from '@/components/dashboard/MarineHazardsAlerts';
import MarineEnvironmentalIntelligence from '@/components/dashboard/MarineEnvironmentalIntelligence';
import OrcaIntelligence from '@/components/dashboard/OrcaIntelligence';
import AskOrca from '@/components/dashboard/AskOrca';
import AgentNetwork from '@/components/dashboard/AgentNetwork';
import { MapLayerType } from '@/types';

export default function DashboardPage() {
  const [activeLayers, setActiveLayers] = useState<MapLayerType[]>(['pfz']);
  // Track hazard code so map layer can reflect live severity
  const [hazardCode, setHazardCode] = useState<'clear' | 'caution' | 'high'>('clear');

  const toggleLayer = useCallback((layer: MapLayerType) => {
    setActiveLayers((prev) =>
      prev.includes(layer) ? prev.filter((l) => l !== layer) : [...prev, layer]
    );
  }, []);

  const activateLayersFromQuery = useCallback((layers: MapLayerType[]) => {
    setActiveLayers((prev) => {
      const newLayers = new Set([...prev, ...layers]);
      return Array.from(newLayers);
    });
  }, []);

  const handleViewRiskMap = useCallback(() => {
    setActiveLayers((prev) => {
      const newLayers = new Set([...prev, 'risk' as MapLayerType]);
      return Array.from(newLayers);
    });
  }, []);

  const handleReviewRoute = useCallback(() => {
    setActiveLayers((prev) => {
      const newLayers = new Set([...prev, 'route' as MapLayerType, 'risk' as MapLayerType]);
      return Array.from(newLayers);
    });
  }, []);

  const handleShowHazardsOnMap = useCallback(() => {
    setActiveLayers((prev) => {
      const newLayers = new Set([...prev, 'hazards' as MapLayerType]);
      return Array.from(newLayers);
    });
    const mapEl = document.getElementById('orca-marine-map');
    if (mapEl) {
      mapEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, []);

  const handleShowSSTOnMap = useCallback(() => {
    setActiveLayers((prev) => {
      const newLayers = new Set([...prev, 'sst' as MapLayerType]);
      return Array.from(newLayers);
    });
    const mapEl = document.getElementById('orca-marine-map');
    if (mapEl) {
      mapEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, []);

  return (
    <div className="p-4 space-y-4">
      {/* ── Row 1: Marine Metrics ── */}
      <MarineMetrics />

      {/* ── Row 2: Map + Safety Assessment ── */}
      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-7">
          <MarineMap activeLayers={activeLayers} onToggleLayer={toggleLayer} hazardCode={hazardCode} />
        </div>
        <div className="col-span-5">
          <FishingSafetyAssessment onViewRiskMap={handleViewRiskMap} />
        </div>
      </div>

      {/* ── Row 3: Marine Hazards & Alerts ── */}
      <MarineHazardsAlerts onShowOnMap={handleShowHazardsOnMap} onHazardCode={setHazardCode} />

      {/* ── Row 4: Marine Environmental Intelligence ── */}
      <MarineEnvironmentalIntelligence onShowSSTOnMap={handleShowSSTOnMap} />

      {/* ── Row 5: Ask ORCA — full width ── */}
      <AskOrca onLayerActivate={activateLayersFromQuery} />

      {/* ── Row 6: Intelligence + Agent Network ── */}
      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-5">
          <OrcaIntelligence onReviewRoute={handleReviewRoute} />
        </div>
        <div className="col-span-7">
          <AgentNetwork />
        </div>
      </div>
    </div>
  );
}
