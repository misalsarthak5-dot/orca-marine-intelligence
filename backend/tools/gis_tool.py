"""
ORCA GIS Tool
Thin adapter wrapping existing services.geofence_service functionality.
Provides spatial point-in-polygon, line intersection, and maritime restriction zone evaluation.
"""

from typing import Optional, List, Dict, Any
from tools.base_tool import BaseTool, ToolResult
from core.schemas import AgentStatus, DataStatus
from services.geofence_service import (
    get_active_geofences,
    evaluate_route_geofences,
    point_in_polygon,
    check_route_intersects_geometry,
)


class GISTool(BaseTool):
    """
    Adapter for GIS & Geofencing spatial intelligence.
    Wraps services.geofence_service functions:
      - get_active_geofences
      - evaluate_route_geofences
      - spatial geometry checks
    """

    name: str = "gis_tool"
    description: str = (
        "Performs spatial reasoning and maritime restriction evaluation, "
        "including point-in-polygon tests, corridor geometry intersection checks, "
        "and querying official active geofence layers."
    )

    async def execute(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radius_km: float = 250.0,
        route_coords: Optional[List[List[float]]] = None,
        override_zones: Optional[List[Dict[str, Any]]] = None,
        operation: str = "query_zones",
        **kwargs,
    ) -> ToolResult:
        """
        Execute GIS/geofence query or route intersection evaluation.

        Args:
            lat: Latitude (for zone querying)
            lon: Longitude (for zone querying)
            radius_km: Radius in km
            route_coords: List of [lat, lon] waypoints (for route clearance check)
            override_zones: Optional explicit zone definitions
            operation: 'query_zones' or 'evaluate_route'

        Returns:
            ToolResult containing GIS verdict and provenance metadata.
        """
        try:
            if operation == "evaluate_route" and route_coords:
                eval_result = evaluate_route_geofences(route_coords, override_zones=override_zones)
                
                # Determine data status based on restriction availability
                data_status = (
                    DataStatus.LIVE
                    if override_zones is not None
                    else DataStatus.UNAVAILABLE
                )

                evidence = self.create_evidence(
                    source="ORCA Geofencing & Spatial Engine",
                    source_type="rule_engine",
                    data_status=data_status,
                )

                return ToolResult(
                    tool=self.name,
                    status=AgentStatus.SUCCESS,
                    data=eval_result,
                    evidence=evidence,
                    errors=[],
                    metadata={"operation": "evaluate_route"},
                )

            # Default: query active geofences near coordinates
            if lat is None or lon is None:
                return self.create_error_result(
                    error_message="Coordinates (lat, lon) are required to query active geofences.",
                    evidence=self.create_evidence(
                        source="ORCA Geofencing Engine",
                        source_type="rule_engine",
                        data_status=DataStatus.ERROR,
                    ),
                )

            raw_data = await get_active_geofences(lat=lat, lon=lon, radius_km=radius_km)
            evidence = self.create_evidence(
                source="Official Government Gazette / INCOIS WFS",
                source_type="ogc_wfs",
                data_status=DataStatus.UNAVAILABLE,  # Honest upstream reporting
                reference="https://www.incois.gov.in",
            )

            return ToolResult(
                tool=self.name,
                status=AgentStatus.SUCCESS,
                data=raw_data,
                evidence=evidence,
                errors=[],
                metadata={
                    "operation": "query_zones",
                    "status": raw_data.get("status", "UNAVAILABLE"),
                    "total_zones": raw_data.get("total_zones_found", 0),
                },
            )

        except Exception as e:
            return self.create_error_result(
                error_message=f"GIS tool operation failed: {str(e)}",
                errors=[str(e)],
                evidence=self.create_evidence(
                    source="ORCA Geofencing & Spatial Engine",
                    source_type="rule_engine",
                    data_status=DataStatus.ERROR,
                ),
            )
