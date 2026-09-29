"""
ORCA Weather Tool
Thin adapter wrapping existing services.weather_service.get_weather_data.
Provides standardized ToolResult with Open-Meteo provenance.
"""

from typing import Optional, Callable, Any
from tools.base_tool import BaseTool, ToolResult
from core.schemas import AgentStatus, DataStatus
from services.weather_service import get_weather_data


class WeatherTool(BaseTool):
    """
    Adapter for atmospheric weather data.
    Directly invokes services.weather_service.get_weather_data.
    """

    name: str = "weather_tool"
    description: str = (
        "Retrieves live atmospheric weather conditions "
        "(temperature, wind speed, gusts, direction, humidity, precipitation) "
        "and hourly forecasts from Open-Meteo."
    )

    async def execute(
        self,
        lat: float,
        lon: float,
        fetch_fn: Optional[Callable[..., Any]] = None,
        **kwargs,
    ) -> ToolResult:
        """
        Execute atmospheric weather retrieval.

        Args:
            lat: Latitude (-90 to 90)
            lon: Longitude (-180 to 180)
            fetch_fn: Optional callable overriding weather service retrieval

        Returns:
            ToolResult containing raw service dictionary and Evidence grounding.
        """
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return self.create_error_result(
                error_message=f"Invalid coordinates: lat={lat}, lon={lon}",
                evidence=self.create_evidence(
                    source="Open-Meteo Forecast API",
                    source_type="api",
                    data_status=DataStatus.ERROR,
                    reference="https://open-meteo.com/en/docs",
                ),
            )

        caller = fetch_fn or get_weather_data
        try:
            raw_data = await caller(lat=lat, lon=lon)
        except Exception as e:
            return self.create_error_result(
                error_message=f"Failed to retrieve atmospheric weather data: {str(e)}",
                errors=[str(e)],
                evidence=self.create_evidence(
                    source="Open-Meteo Forecast API",
                    source_type="api",
                    data_status=DataStatus.ERROR,
                    reference="https://open-meteo.com/en/docs",
                ),
            )

        current = raw_data.get("current", {})
        observed_at = current.get("time")

        evidence = self.create_evidence(
            source="Open-Meteo Forecast API",
            source_type="api",
            observed_at=observed_at,
            data_status=DataStatus.LIVE,
            reference="https://open-meteo.com/en/docs",
        )

        return ToolResult(
            tool=self.name,
            status=AgentStatus.SUCCESS,
            data=raw_data,
            evidence=evidence,
            errors=[],
            metadata={"source": raw_data.get("source", "Open-Meteo")},
        )
