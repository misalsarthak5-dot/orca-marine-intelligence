"""
ORCA Route Agent — Phase 3 Domain Agent
Thin domain adapter: AgentRequest → RouteTool → AgentResult
Covers candidate marine navigation corridors, risk scores, and geofence clearance.
Does NOT implement a new routing algorithm — delegates entirely to RouteTool.
"""

from typing import Optional, List, Dict, Any
from agents.base_agent import BaseAgent
from core.schemas import AgentRequest, AgentResult, AgentStatus, DataStatus
from tools.route_tool import RouteTool


class RouteAgent(BaseAgent):
    """
    Domain agent for marine route corridor intelligence.
    Delegates to RouteTool → services.route_service.analyze_routes_service.
    Accepts destination coordinates from AgentRequest.destination_latitude/longitude.
    Accepts route-specific parameters from request.context.

    Context fields supported:
        context['destination_name']  → label for the destination (str, default 'Designated Target')
        context['time_window']       → forecast period ('current', 'tomorrow_morning', 'tomorrow')
        context['override_zones']    → explicit zone definitions for geofence test fixtures

    Does not invent route data, does not call route_service directly.
    """

    name: str = "route_agent"
    description: str = (
        "Generates candidate marine navigation corridors, evaluates environmental "
        "risk, geofence clearance, and produces explainable recommendations "
        "via RouteTool backed by services.route_service."
    )

    def __init__(self, tool: Optional[RouteTool] = None):
        super().__init__()
        self.tool = tool or RouteTool()

    async def execute(self, request: AgentRequest) -> AgentResult:
        """
        Execute marine route corridor intelligence.

        AgentRequest field usage:
            latitude              → origin latitude
            longitude             → origin longitude
            destination_latitude  → destination latitude (required)
            destination_longitude → destination longitude (required)
            timestamp             → used as time_window fallback if context not set
            context['destination_name']  → human-readable destination label
            context['time_window']       → 'current', 'tomorrow_morning', 'tomorrow'
            context['override_zones']    → geofence fixture list for testing

        Returns:
            AgentResult containing candidate corridors, risk scores, and recommendation.
        """
        origin_lat = request.latitude
        origin_lon = request.longitude
        dest_lat = request.destination_latitude
        dest_lon = request.destination_longitude

        # 1. Validate origin coordinates
        if not (-90.0 <= origin_lat <= 90.0 and -180.0 <= origin_lon <= 180.0):
            return self.create_error_result(
                error_message=f"Invalid origin coordinates: latitude={origin_lat}, longitude={origin_lon}",
                evidence=self.create_evidence(
                    source="ORCA Route Intelligence Engine",
                    source_type="rule_engine",
                    data_status=DataStatus.ERROR,
                ),
            )

        # 2. Validate destination is provided and valid
        if dest_lat is None or dest_lon is None:
            return self.create_error_result(
                error_message=(
                    "Route analysis requires destination_latitude and destination_longitude "
                    "in the AgentRequest. Neither can be None."
                ),
                evidence=self.create_evidence(
                    source="ORCA Route Intelligence Engine",
                    source_type="rule_engine",
                    data_status=DataStatus.ERROR,
                ),
            )

        if not (-90.0 <= dest_lat <= 90.0 and -180.0 <= dest_lon <= 180.0):
            return self.create_error_result(
                error_message=f"Invalid destination coordinates: latitude={dest_lat}, longitude={dest_lon}",
                evidence=self.create_evidence(
                    source="ORCA Route Intelligence Engine",
                    source_type="rule_engine",
                    data_status=DataStatus.ERROR,
                ),
            )

        # 3. Extract route-specific parameters from request.context
        destination_name: str = request.context.get("destination_name", "Designated Target")

        # Time window priority: context > timestamp field > default
        time_window: str = (
            request.context.get("time_window")
            or request.timestamp
            or "tomorrow_morning"
        )

        override_zones: Optional[List[Dict[str, Any]]] = request.context.get("override_zones")

        # 4. Delegate to RouteTool — do not call route_service directly
        tool_result = await self.tool.execute(
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            destination_lat=dest_lat,
            destination_lon=dest_lon,
            destination_name=destination_name,
            time_window=time_window,
            override_zones=override_zones,
        )

        # 5. Propagate tool failure cleanly
        if tool_result.status == AgentStatus.FAILED:
            error_msg = (
                tool_result.errors[0]
                if tool_result.errors
                else "Route analysis service failed"
            )
            return self.create_error_result(
                error_message=error_msg,
                errors=tool_result.errors,
                evidence=tool_result.evidence,
            )

        # 6. Preserve route data and evidence verbatim
        route_data = tool_result.data or {}
        evidence = tool_result.evidence

        routes = route_data.get("routes", [])
        recommended_id = route_data.get("recommended_route_id")
        route_count = len(routes)

        # 7. Assess completeness
        # If no routes were returned, the result is PARTIAL (service ran but produced nothing usable)
        if not routes:
            return AgentResult(
                agent=self.name,
                status=AgentStatus.PARTIAL,
                data=route_data,
                evidence=evidence,
                confidence=0.0,
                message=(
                    f"Route analysis completed for "
                    f"({origin_lat:.4f}, {origin_lon:.4f}) → "
                    f"({dest_lat:.4f}, {dest_lon:.4f}) "
                    f"but produced no viable corridors."
                ),
                errors=tool_result.errors,
            )

        # 8. Confidence: based on ratio of viable routes vs total
        viable_count = sum(
            1 for r in routes if r.get("overall_status") != "NOT_VIABLE"
        )
        confidence = round(viable_count / route_count, 2) if route_count > 0 else 0.0
        status = AgentStatus.SUCCESS if confidence > 0.0 else AgentStatus.PARTIAL

        # 9. Human-readable summary using real values only
        recommended = next((r for r in routes if r.get("id") == recommended_id), None)
        rec_name = recommended.get("name", recommended_id) if recommended else "None"
        rec_risk = recommended.get("risk_score", "?") if recommended else "?"

        message = (
            f"Route analysis: {route_count} corridor(s) evaluated "
            f"({origin_lat:.4f}, {origin_lon:.4f}) → "
            f"({dest_lat:.4f}, {dest_lon:.4f}), "
            f"time_window={time_window}. "
            f"Recommended: {rec_name} (risk_score={rec_risk}/100)."
        )

        return AgentResult(
            agent=self.name,
            status=status,
            data=route_data,
            evidence=evidence,
            confidence=confidence,
            message=message,
            errors=tool_result.errors,
        )
