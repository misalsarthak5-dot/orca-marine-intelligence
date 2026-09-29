"""
ORCA Route Tool
Thin adapter wrapping existing services.route_service.analyze_routes_service.
Provides standardized ToolResult with candidate corridors, sampled telemetry, and risk scores.
"""

from typing import Optional, List, Dict, Any
from tools.base_tool import BaseTool, ToolResult
from core.schemas import AgentStatus, DataStatus
from services.route_service import analyze_routes_service


class RouteTool(BaseTool):
    """
    Adapter for candidate route corridor intelligence and risk analysis.
    Directly invokes services.route_service.analyze_routes_service.
    """

    name: str = "route_tool"
    description: str = (
        "Generates candidate marine navigation corridors, samples real-time "
        "and forecasted telemetry along waypoints, calculates risk scores, "
        "evaluates geofence clearance, and produces an explainable recommendation."
    )

    async def execute(
        self,
        origin_lat: float,
        origin_lon: float,
        destination_lat: float,
        destination_lon: float,
        destination_name: str = "Designated Target",
        time_window: str = "tomorrow_morning",
        override_zones: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> ToolResult:
        """
        Execute candidate route corridor intelligence and risk assessment.

        Args:
            origin_lat: Starting port/coastal latitude
            origin_lon: Starting port/coastal longitude
            destination_lat: Target destination/PFZ latitude
            destination_lon: Target destination/PFZ longitude
            destination_name: Target label
            time_window: 'current', 'tomorrow_morning', or 'tomorrow'
            override_zones: Optional geofence test fixtures

        Returns:
            ToolResult containing candidate corridors, risk scores, and recommendation.
        """
        if not (-90.0 <= origin_lat <= 90.0 and -180.0 <= origin_lon <= 180.0):
            return self.create_error_result(
                error_message=f"Invalid origin coordinates: lat={origin_lat}, lon={origin_lon}",
                evidence=self.create_evidence(
                    source="ORCA Route Intelligence Engine",
                    source_type="rule_engine",
                    data_status=DataStatus.ERROR,
                ),
            )

        if not (-90.0 <= destination_lat <= 90.0 and -180.0 <= destination_lon <= 180.0):
            return self.create_error_result(
                error_message=f"Invalid destination coordinates: lat={destination_lat}, lon={destination_lon}",
                evidence=self.create_evidence(
                    source="ORCA Route Intelligence Engine",
                    source_type="rule_engine",
                    data_status=DataStatus.ERROR,
                ),
            )

        try:
            raw_data = await analyze_routes_service(
                origin_lat=origin_lat,
                origin_lon=origin_lon,
                destination_lat=destination_lat,
                destination_lon=destination_lon,
                destination_name=destination_name,
                time_window=time_window,
                override_zones=override_zones,
            )
        except Exception as e:
            return self.create_error_result(
                error_message=f"Route service call failed: {str(e)}",
                errors=[str(e)],
                evidence=self.create_evidence(
                    source="ORCA Route Intelligence Engine",
                    source_type="rule_engine",
                    data_status=DataStatus.ERROR,
                ),
            )

        evidence = self.create_evidence(
            source="ORCA Route Intelligence Engine (Multi-Source Feeds)",
            source_type="rule_engine",
            data_status=DataStatus.LIVE,
            reference="Open-Meteo & INCOIS WebGIS",
        )

        return ToolResult(
            tool=self.name,
            status=AgentStatus.SUCCESS,
            data=raw_data,
            evidence=evidence,
            errors=[],
            metadata={
                "routes_count": len(raw_data.get("routes", [])),
                "recommended_route_id": raw_data.get("recommended_route_id"),
                "time_window": raw_data.get("time_window"),
            },
        )
