"""
ORCA Marine Tool
Thin adapter wrapping existing services.marine_service.get_marine_data.
Provides standardized ToolResult with Open-Meteo Marine provenance.
"""

from typing import Optional
from tools.base_tool import BaseTool, ToolResult
from core.schemas import AgentStatus, DataStatus
from services.marine_service import get_marine_data


class MarineTool(BaseTool):
    """
    Adapter for oceanographic marine data.
    Directly invokes services.marine_service.get_marine_data.
    """

    name: str = "marine_tool"
    description: str = (
        "Retrieves live oceanographic telemetry "
        "(wave height, wave direction, wave period, swell wave height, swell period, sea surface temperature SST) "
        "and hourly forecasts from Open-Meteo Marine API."
    )

    async def execute(self, lat: float, lon: float, **kwargs) -> ToolResult:
        """
        Execute oceanographic marine telemetry retrieval.

        Args:
            lat: Latitude (-90 to 90)
            lon: Longitude (-180 to 180)

        Returns:
            ToolResult containing raw marine dictionary and Evidence grounding.
        """
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return self.create_error_result(
                error_message=f"Invalid coordinates: lat={lat}, lon={lon}",
                evidence=self.create_evidence(
                    source="Open-Meteo Marine API",
                    source_type="api",
                    data_status=DataStatus.ERROR,
                    reference="https://open-meteo.com/en/docs/marine-weather-api",
                ),
            )

        try:
            raw_data = await get_marine_data(lat=lat, lon=lon)
        except Exception as e:
            return self.create_error_result(
                error_message=f"Marine service call failed: {str(e)}",
                errors=[str(e)],
                evidence=self.create_evidence(
                    source="Open-Meteo Marine API",
                    source_type="api",
                    data_status=DataStatus.ERROR,
                    reference="https://open-meteo.com/en/docs/marine-weather-api",
                ),
            )

        current = raw_data.get("current", {})
        observed_at = current.get("time")

        evidence = self.create_evidence(
            source="Open-Meteo Marine API",
            source_type="api",
            observed_at=observed_at,
            data_status=DataStatus.LIVE,
            reference="https://open-meteo.com/en/docs/marine-weather-api",
        )

        return ToolResult(
            tool=self.name,
            status=AgentStatus.SUCCESS,
            data=raw_data,
            evidence=evidence,
            errors=[],
            metadata={"source": raw_data.get("source", "Open-Meteo")},
        )
