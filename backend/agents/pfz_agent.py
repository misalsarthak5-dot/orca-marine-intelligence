"""
ORCA PFZ Agent — Phase 3 Domain Agent
Thin domain adapter: AgentRequest → PFZTool → AgentResult
Covers INCOIS Potential Fishing Zones advisories.
Preserves LIVE/CACHED/STALE/UNAVAILABLE state from tool without collapsing truth.
"""

from typing import Optional
from agents.base_agent import BaseAgent
from core.schemas import AgentRequest, AgentResult, AgentStatus, DataStatus
from tools.pfz_tool import PFZTool


class PFZAgent(BaseAgent):
    """
    Domain agent for INCOIS Potential Fishing Zones (PFZ) intelligence.
    Delegates to PFZTool → services.pfz_service.get_pfz_assessment.
    Preserves INCOIS WFS provenance, reference layer date, and availability state.

    IMPORTANT: This agent never describes data as "today's official PFZ" unless
    the underlying tool/service establishes that — provenance is forwarded verbatim.
    """

    name: str = "pfz_agent"
    description: str = (
        "Retrieves INCOIS Potential Fishing Zones (PFZ) advisories "
        "including landing centre references, distance, bearing, depth ranges, "
        "and satellite frontal line geometry via PFZTool."
    )

    def __init__(self, tool: Optional[PFZTool] = None):
        super().__init__()
        self.tool = tool or PFZTool()

    async def execute(self, request: AgentRequest) -> AgentResult:
        """
        Execute INCOIS PFZ assessment.

        Args:
            request: AgentRequest with latitude, longitude, and optional
                     context['radius_km'] for search radius override.

        Returns:
            AgentResult containing PFZ payload, INCOIS provenance, and status.
        """
        lat = request.latitude
        lon = request.longitude

        # Optional radius override via request context
        radius_km = float(request.context.get("radius_km", 250.0))

        # 1. Coordinate boundary guard
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return self.create_error_result(
                error_message=f"Invalid geographic coordinates: latitude={lat}, longitude={lon}",
                evidence=self.create_evidence(
                    source="INCOIS WebGIS GeoServer WFS",
                    source_type="ogc_wfs",
                    data_status=DataStatus.ERROR,
                    reference="https://www.incois.gov.in",
                ),
            )

        # 2. Delegate to PFZTool — do not call pfz_service directly
        tool_result = await self.tool.execute(lat=lat, lon=lon, radius_km=radius_km)

        # 3. Propagate tool failure cleanly
        if tool_result.status == AgentStatus.FAILED:
            error_msg = (
                tool_result.errors[0]
                if tool_result.errors
                else "Failed to retrieve INCOIS PFZ advisories"
            )
            return self.create_error_result(
                error_message=error_msg,
                errors=tool_result.errors,
                evidence=tool_result.evidence,
            )

        # 4. Preserve PFZ data and INCOIS provenance verbatim
        pfz_data = tool_result.data or {}
        evidence = tool_result.evidence  # INCOIS WFS evidence forwarded as-is

        available = pfz_data.get("available", False)
        total_advisories = pfz_data.get("total_active_advisories_found", 0)
        nearest = pfz_data.get("nearest_advisory")

        # 5. Map tool status to agent status
        # PARTIAL tool result (no PFZ available) → PARTIAL agent result, not FAILED.
        # UNAVAILABLE data is not a fabrication error — it is an honest state.
        if tool_result.status == AgentStatus.PARTIAL:
            # PFZ data unavailable for this location — preserve the PARTIAL truth
            status = AgentStatus.PARTIAL
            confidence = 0.5
            message = (
                f"No active INCOIS PFZ advisories found within {radius_km:.0f} km "
                f"of ({lat:.4f}, {lon:.4f}). Conditions may be outside seasonal advisory coverage."
            )
        else:
            status = AgentStatus.SUCCESS
            confidence = 1.0
            ref_date = evidence.observed_at if evidence else None
            message = (
                f"INCOIS PFZ assessment: {total_advisories} active advisory(ies) "
                f"within {radius_km:.0f} km of ({lat:.4f}, {lon:.4f})"
                + (f", reference layer: {ref_date}" if ref_date else "")
                + (
                    f". Nearest: {nearest['landing_center']} ({nearest.get('distance_from_query_km', '?'):.1f} km)."
                    if nearest and isinstance(nearest, dict)
                    else "."
                )
            )

        return AgentResult(
            agent=self.name,
            status=status,
            data=pfz_data,
            evidence=evidence,
            confidence=confidence,
            message=message,
            errors=tool_result.errors,
        )
