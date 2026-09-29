"""
ORCA GIS Agent — Phase 3 Domain Agent
Thin domain adapter: AgentRequest → GISTool → AgentResult
Covers spatial GIS / geofence queries and route corridor intersection evaluation.
Preserves honest UNAVAILABLE states — never fabricates polygon data.
"""

from typing import Optional, List, Dict, Any
from agents.base_agent import BaseAgent
from core.schemas import AgentRequest, AgentResult, AgentStatus, DataStatus
from tools.gis_tool import GISTool


class GISAgent(BaseAgent):
    """
    Domain agent for GIS and geofence spatial intelligence.
    Delegates to GISTool → services.geofence_service.
    Preserves UNAVAILABLE states transparently — does not replace missing
    official data with guessed or synthesized geofences.
    """

    name: str = "gis_agent"
    description: str = (
        "Performs spatial reasoning and maritime restriction evaluation: "
        "point-in-polygon tests, route corridor intersection checks, "
        "and official geofence zone queries via GISTool."
    )

    def __init__(self, tool: Optional[GISTool] = None):
        super().__init__()
        self.tool = tool or GISTool()

    async def execute(self, request: AgentRequest) -> AgentResult:
        """
        Execute GIS / geofence query or route evaluation.

        AgentRequest field usage:
            latitude, longitude  → origin point for zone query
            context['operation']     → 'query_zones' (default) or 'evaluate_route'
            context['radius_km']     → search radius override (default 250.0)
            context['route_coords']  → list of [lat, lon] for route clearance check
            context['override_zones'] → explicit zone definitions for test fixtures

        Returns:
            AgentResult containing GIS verdict, evidence, and honest data status.
        """
        lat = request.latitude
        lon = request.longitude

        # Extract GIS-specific parameters from context
        operation = request.context.get("operation", "query_zones")
        radius_km = float(request.context.get("radius_km", 250.0))
        route_coords: Optional[List[List[float]]] = request.context.get("route_coords")
        override_zones: Optional[List[Dict[str, Any]]] = request.context.get("override_zones")

        # 1. For zone queries, coordinates are required
        if operation == "query_zones":
            if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                return self.create_error_result(
                    error_message=f"Invalid geographic coordinates: latitude={lat}, longitude={lon}",
                    evidence=self.create_evidence(
                        source="ORCA Geofencing Engine",
                        source_type="rule_engine",
                        data_status=DataStatus.ERROR,
                    ),
                )

        # 2. For route evaluation, route_coords are required
        if operation == "evaluate_route" and not route_coords:
            return self.create_error_result(
                error_message="Route evaluation requires 'route_coords' in request context.",
                evidence=self.create_evidence(
                    source="ORCA Geofencing Engine",
                    source_type="rule_engine",
                    data_status=DataStatus.ERROR,
                ),
            )

        # 3. Delegate to GISTool — do not call geofence_service directly
        tool_result = await self.tool.execute(
            lat=lat,
            lon=lon,
            radius_km=radius_km,
            route_coords=route_coords,
            override_zones=override_zones,
            operation=operation,
        )

        # 4. Propagate tool failure cleanly
        if tool_result.status == AgentStatus.FAILED:
            error_msg = (
                tool_result.errors[0]
                if tool_result.errors
                else "GIS tool operation failed"
            )
            return self.create_error_result(
                error_message=error_msg,
                errors=tool_result.errors,
                evidence=tool_result.evidence,
            )

        # 5. Preserve GIS data and evidence verbatim
        gis_data = tool_result.data or {}
        evidence = tool_result.evidence

        # 6. Map GIS status to agent status and confidence
        # Critically: UNAVAILABLE is not a failure — it is an honest disclosure
        # that official polygon data has not been loaded.
        data_status = evidence.data_status if evidence else DataStatus.UNAVAILABLE
        if data_status == DataStatus.UNAVAILABLE:
            # Honest state: no official geofence data available
            status = AgentStatus.PARTIAL
            confidence = 0.5
            zones_count = gis_data.get("total_zones_found", 0)
            message = (
                f"GIS geofence query at ({lat:.4f}, {lon:.4f}): "
                f"official restriction zone data unavailable "
                f"(no authoritative source integrated). "
                f"{zones_count} zones found (structural check only)."
            )
        elif data_status == DataStatus.LIVE:
            status = AgentStatus.SUCCESS
            confidence = 1.0
            zones_count = gis_data.get("total_zones_found", 0)
            restriction_status = gis_data.get("status", "")
            message = (
                f"GIS evaluation ({operation}) at ({lat:.4f}, {lon:.4f}): "
                f"{zones_count} zone(s) evaluated, restriction_status={restriction_status}."
            )
        else:
            status = AgentStatus.PARTIAL
            confidence = 0.5
            message = (
                f"GIS evaluation ({operation}) completed with data_status={data_status.value}."
            )

        return AgentResult(
            agent=self.name,
            status=status,
            data=gis_data,
            evidence=evidence,
            confidence=confidence,
            message=message,
            errors=tool_result.errors,
        )
