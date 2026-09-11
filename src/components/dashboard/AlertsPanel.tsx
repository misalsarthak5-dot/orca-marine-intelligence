'use client';

import React from 'react';
import MarineHazardsAlerts from './MarineHazardsAlerts';

interface AlertsPanelProps {
  onShowOnMap?: () => void;
}

export default function AlertsPanel({ onShowOnMap }: AlertsPanelProps) {
  return <MarineHazardsAlerts onShowOnMap={onShowOnMap} />;
}
