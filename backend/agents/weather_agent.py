"""
ORCA Weather Agent
Domain agent for atmospheric weather, wind, gusts, and precipitation telemetry.
Delegates to WeatherTool, which adapts existing Open-Meteo weather service.
"""

from typing import Optional
from agents.base_agent import BaseAgent
from core.schemas import AgentRequest, AgentResult, AgentStatus, DataStatus
from tools.weather_tool import WeatherTool
from services.weather_service import get_weather_data


class WeatherAgent(BaseAgent):
    """
    Domain-specific agent executing atmospheric weather retrieval and validation.
    Delegates to WeatherTool -> services.weather_service.get_weather_data.
    Grounds output in standardized AgentResult with full evidence provenance.
    """

    name: str = "weather_agent"
    description: str = (
        "Retrieves and validates live atmospheric weather conditions "
        "(temperature, wind speed, gusts, direction, humidity, precipitation) "
        "and hourly forecasts via WeatherTool."
    )

    def __init__(self, tool: Optional[WeatherTool] = None):
        super().__init__()
        self.tool = tool or WeatherTool()

    async def execute(self, request: AgentRequest) -> AgentResult:
        """
        Execute weather retrieval for the coordinates provided in request.

        Args:
            request: AgentRequest containing latitude and longitude.

        Returns:
            AgentResult containing validated weather data, evidence record, and confidence.
        """
        lat = request.latitude
        lon = request.longitude

        # 1. Geographic boundary validation
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            error_msg = f"Invalid geographic coordinates: latitude={lat}, longitude={lon}"
            return self.create_error_result(
                error_message=error_msg,
                evidence=self.create_evidence(
                    source="Open-Meteo Forecast API",
                    source_type="api",
                    data_status=DataStatus.ERROR,
                    reference="https://open-meteo.com/en/docs",
                ),
            )

        # 2. Delegate execution to WeatherTool (passing get_weather_data for seamless adapter coupling)
        tool_result = await self.tool.execute(lat=lat, lon=lon, fetch_fn=get_weather_data)

        if tool_result.status == AgentStatus.FAILED:
            error_msg = tool_result.errors[0] if tool_result.errors else "Failed to retrieve atmospheric weather data"
            return self.create_error_result(
                error_message=error_msg,
                errors=tool_result.errors,
                evidence=tool_result.evidence,
            )

        weather_data = tool_result.data or {}
        evidence = tool_result.evidence

        # 3. Assess telemetry completeness for confidence score
        current = weather_data.get("current", {})
        required_fields = ["temperature", "wind_speed", "wind_direction", "precipitation"]
        present_count = sum(1 for f in required_fields if current.get(f) is not None)
        confidence = round(present_count / len(required_fields), 2)

        # Determine agent status
        if confidence == 1.0:
            status = AgentStatus.SUCCESS
        elif confidence > 0.0:
            status = AgentStatus.PARTIAL
        else:
            status = AgentStatus.FAILED

        temp_val = current.get("temperature")
        wind_val = current.get("wind_speed")
        wind_comp = current.get("wind_direction_compass", "")
        summary = (
            f"Atmospheric weather at ({lat:.4f}, {lon:.4f}): "
            f"{temp_val}°C, wind {wind_val} kn {wind_comp}."
        )

        return AgentResult(
            agent=self.name,
            status=status,
            data=weather_data,
            evidence=evidence,
            confidence=confidence,
            message=summary,
            errors=[],
        )
