"""
ORCA Chlorophyll Agent — Phase 3.5 Domain Agent
Thin domain adapter: AgentRequest → ChlorophyllTool → AgentResult
Covers satellite ocean-color chlorophyll-a data.
Preserves LIVE / UNAVAILABLE / CACHED / STALE states without fabricating data.
"""

from typing import Optional
from agents.base_agent import BaseAgent
from core.schemas import AgentRequest, AgentResult, AgentStatus, DataStatus
from tools.chlorophyll_tool import ChlorophyllTool


class ChlorophyllAgent(BaseAgent):
    """
    Domain agent for satellite chlorophyll-a ocean color intelligence.
    Delegates to ChlorophyllTool → services.chlorophyll_service.get_chlorophyll_data.
    Preserves NASA Earthdata / INCOIS provenance, timestamp, and availability state.

    CRITICAL RULE:
    Never fabricates chlorophyll values. If satellite source is not connected or
    credentials are not configured, returns DataStatus.UNAVAILABLE and AgentStatus.PARTIAL.
    """

    name: str = "chlorophyll_agent"
    description: str = (
        "Retrieves satellite ocean-color chlorophyll-a concentration "
        "and data readiness status via ChlorophyllTool."
    )

    def __init__(self, tool: Optional[ChlorophyllTool] = None):
        super().__init__()
        self.tool = tool or ChlorophyllTool()

    async def execute(self, request: AgentRequest) -> AgentResult:
        """
        Execute satellite chlorophyll retrieval.

        Args:
            request: AgentRequest with latitude and longitude.

        Returns:
            AgentResult containing chlorophyll payload, provenance, and status.
        """
        lat = request.latitude
        lon = request.longitude

        # 1. Coordinate boundary guard
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return self.create_error_result(
                error_message=f"Invalid geographic coordinates: latitude={lat}, longitude={lon}",
                evidence=self.create_evidence(
                    source="NASA Ocean Color / MODIS-Aqua",
                    source_type="satellite",
                    data_status=DataStatus.ERROR,
                    reference="https://oceancolor.gsfc.nasa.gov",
                ),
            )

        # 2. Delegate to ChlorophyllTool — do not call chlorophyll_service directly
        tool_result = await self.tool.execute(lat=lat, lon=lon)

        # 3. Propagate tool failure cleanly
        if tool_result.status == AgentStatus.FAILED:
            error_msg = (
                tool_result.errors[0]
                if tool_result.errors
                else "Failed to retrieve satellite chlorophyll data"
            )
            return self.create_error_result(
                error_message=error_msg,
                errors=tool_result.errors,
                evidence=tool_result.evidence,
            )

        # 4. Extract data and evidence
        chl_data = tool_result.data or {}
        evidence = tool_result.evidence
        available = chl_data.get("available", False)

        # 5. Determine confidence (propagating tool/service confidence if provided)
        if tool_result.metadata and "confidence" in tool_result.metadata:
            confidence = float(tool_result.metadata["confidence"])
        elif "confidence" in chl_data:
            confidence = float(chl_data["confidence"])
        elif available and chl_data.get("value") is not None:
            confidence = 1.0
        elif available:
            confidence = 0.8
        else:
            confidence = 0.5

        # 6. Map status and construct informative summary
        if tool_result.status == AgentStatus.PARTIAL or not available:
            status = AgentStatus.PARTIAL
            msg_reason = chl_data.get(
                "message",
                "Chlorophyll-a data source is not connected or credentials not configured."
            )
            message = f"Satellite chlorophyll-a unavailable for ({lat:.4f}, {lon:.4f}). {msg_reason}"
        else:
            status = AgentStatus.SUCCESS
            val = chl_data.get("value")
            unit = chl_data.get("unit", "mg/m³")
            val_str = f"{val} {unit}" if val is not None else "granule identified"
            message = (
                f"Chlorophyll-a observation at ({lat:.4f}, {lon:.4f}): {val_str}. "
                f"Source: {chl_data.get('source', 'NASA Ocean Color')}."
            )

        return AgentResult(
            agent=self.name,
            status=status,
            data=chl_data,
            evidence=evidence,
            confidence=confidence,
            message=message,
            errors=tool_result.errors,
        )
