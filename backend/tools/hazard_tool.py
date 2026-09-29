"""
ORCA Hazard Tool
Thin adapter wrapping existing services.hazard_service.evaluate_hazards.
Provides standardized ToolResult with transparent hazard evaluation and telemetry snapshots.
"""

from typing import Optional
from tools.base_tool import BaseTool, ToolResult
from core.schemas import AgentStatus, DataStatus
from services.hazard_service import evaluate_hazards


class HazardTool(BaseTool):
    """
    Adapter for marine hazards and alerts.
    Directly invokes services.hazard_service.evaluate_hazards.
    """

    name: str = "hazard_tool"
    description: str = (
        "Evaluates marine hazards and active alerts for coastal points "
        "(wave conditions, wind squalls, gusts, precipitation visibility) "
        "using real telemetry without fake or synthesized alerts."
    )

    async def execute(self, lat: float, lon: float, **kwargs) -> ToolResult:
        """
        Execute marine hazard evaluation.

        Args:
            lat: Latitude (-90 to 90)
            lon: Longitude (-180 to 180)

        Returns:
            ToolResult containing overall hazard state, active alerts, conditions, and snapshot.
        """
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return self.create_error_result(
                error_message=f"Invalid coordinates: lat={lat}, lon={lon}",
                evidence=self.create_evidence(
                    source="ORCA Marine Hazard Engine",
                    source_type="rule_engine",
                    data_status=DataStatus.ERROR,
                ),
            )

        try:
            raw_data = await evaluate_hazards(lat=lat, lon=lon)
        except Exception as e:
            return self.create_error_result(
                error_message=f"Hazard service call failed: {str(e)}",
                errors=[str(e)],
                evidence=self.create_evidence(
                    source="ORCA Marine Hazard Engine",
                    source_type="rule_engine",
                    data_status=DataStatus.ERROR,
                ),
            )

        snapshot = raw_data.get("telemetry_snapshot", {})
        observed_at = snapshot.get("timestamp")

        evidence = self.create_evidence(
            source="ORCA Marine Hazard Engine (Open-Meteo Multi-Feed)",
            source_type="rule_engine",
            observed_at=observed_at,
            data_status=DataStatus.LIVE,
            reference="https://open-meteo.com",
        )

        return ToolResult(
            tool=self.name,
            status=AgentStatus.SUCCESS,
            data=raw_data,
            evidence=evidence,
            errors=[],
            metadata={
                "overall_state": raw_data.get("overall_state"),
                "active_alerts_count": len(raw_data.get("active_alerts", [])),
            },
        )
