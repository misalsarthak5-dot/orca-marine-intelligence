"""
ORCA Marine Agent — Phase 3 Domain Agent
Thin domain adapter: AgentRequest → MarineTool → AgentResult
Covers oceanographic telemetry: SST, wave height, swell, wave period.
Delegates entirely to MarineTool; does not call marine_service directly.
"""

from typing import Optional
from agents.base_agent import BaseAgent
from core.schemas import AgentRequest, AgentResult, AgentStatus, DataStatus
from tools.marine_tool import MarineTool


class MarineAgent(BaseAgent):
    """
    Domain agent for oceanographic marine telemetry.
    Delegates to MarineTool → services.marine_service.get_marine_data.
    Preserves Open-Meteo provenance, evidence, and data status without fabrication.
    """

    name: str = "marine_agent"
    description: str = (
        "Retrieves and validates live oceanographic conditions "
        "(wave height, wave period, swell, sea surface temperature) "
        "via MarineTool backed by Open-Meteo Marine API."
    )

    def __init__(self, tool: Optional[MarineTool] = None):
        super().__init__()
        self.tool = tool or MarineTool()

    async def execute(self, request: AgentRequest) -> AgentResult:
        """
        Execute oceanographic marine telemetry retrieval.

        Args:
            request: AgentRequest with latitude and longitude.

        Returns:
            AgentResult containing marine conditions, evidence, and confidence.
        """
        lat = request.latitude
        lon = request.longitude

        # 1. Coordinate boundary guard (Pydantic already validates range,
        #    but the tool also checks — explicit check here for clean messaging)
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return self.create_error_result(
                error_message=f"Invalid geographic coordinates: latitude={lat}, longitude={lon}",
                evidence=self.create_evidence(
                    source="Open-Meteo Marine API",
                    source_type="api",
                    data_status=DataStatus.ERROR,
                    reference="https://open-meteo.com/en/docs/marine-weather-api",
                ),
            )

        # 2. Delegate to MarineTool — do not call marine_service directly
        tool_result = await self.tool.execute(lat=lat, lon=lon)

        # 3. Propagate tool failure cleanly
        if tool_result.status == AgentStatus.FAILED:
            error_msg = (
                tool_result.errors[0]
                if tool_result.errors
                else "Failed to retrieve oceanographic marine telemetry"
            )
            return self.create_error_result(
                error_message=error_msg,
                errors=tool_result.errors,
                evidence=tool_result.evidence,
            )

        # 4. Extract and validate payload completeness
        marine_data = tool_result.data or {}
        evidence = tool_result.evidence
        current = marine_data.get("current", {})

        # Key oceanographic fields checked for completeness scoring
        required_fields = [
            "wave_height",
            "wave_direction",
            "wave_period",
            "sea_surface_temperature",
        ]
        present_count = sum(
            1 for f in required_fields if current.get(f) is not None
        )
        confidence = round(present_count / len(required_fields), 2)

        if confidence == 1.0:
            status = AgentStatus.SUCCESS
        elif confidence > 0.0:
            status = AgentStatus.PARTIAL
        else:
            status = AgentStatus.FAILED

        # 5. Human-readable summary using real values only
        wave_h = current.get("wave_height")
        sst = current.get("sea_surface_temperature")
        wind_wave = current.get("wind_wave_height")
        summary = (
            f"Marine telemetry at ({lat:.4f}, {lon:.4f}): "
            f"wave height={wave_h} m, "
            f"SST={sst} °C"
            + (f", wind wave={wind_wave} m" if wind_wave is not None else "")
            + "."
        )

        return AgentResult(
            agent=self.name,
            status=status,
            data=marine_data,
            evidence=evidence,
            confidence=confidence,
            message=summary,
            errors=[],
        )
