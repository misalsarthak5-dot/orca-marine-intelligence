'use client';

import React, { useState, useCallback } from 'react';
import MarineMetrics from '@/components/dashboard/MarineMetrics';
import MarineMap from '@/components/dashboard/MarineMap';
import FishingSafetyAssessment from '@/components/dashboard/FishingSafetyAssessment';
import OrcaIntelligence from '@/components/dashboard/OrcaIntelligence';
import AskOrca from '@/components/dashboard/AskOrca';
import AlertsPanel from '@/components/dashboard/AlertsPanel';
import AgentNetwork from '@/components/dashboard/AgentNetwork';
import { MapLayerType } from '@/types';

export default function DashboardPage() {
  const [activeLayers, setActiveLayers] = useState<MapLayerType[]>(['pfz']);

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

  return (
    <div className="p-4 space-y-4">
      {/* Marine Metrics Row */}
      <MarineMetrics />

      {/* Map + Safety Assessment */}
      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-7">
          <MarineMap activeLayers={activeLayers} onToggleLayer={toggleLayer} />
        </div>
        <div className="col-span-5">
          <FishingSafetyAssessment
            onViewRiskMap={handleViewRiskMap}
          />
        </div>
      </div>

      {/* Ask ORCA — full width */}
      <AskOrca onLayerActivate={activateLayersFromQuery} />

      {/* Alerts + Intelligence + Agent Network */}
      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-5">
          <AlertsPanel />
        </div>
        <div className="col-span-3">
          <OrcaIntelligence onReviewRoute={handleReviewRoute} />
        </div>
        <div className="col-span-4">
          <AgentNetwork />
        </div>
      </div>
    </div>
  );
}
