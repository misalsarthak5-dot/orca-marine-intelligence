"""
ORCA Hazard Agent — Phase 3 Domain Agent
Thin domain adapter: AgentRequest → HazardTool → AgentResult
Covers marine hazards: waves, wind squalls, gusts, precipitation visibility.
Uses existing deterministic hazard logic without new thresholds.
"""

from typing import Optional
from agents.base_agent import BaseAgent
from core.schemas import AgentRequest, AgentResult, AgentStatus, DataStatus
from tools.hazard_tool import HazardTool


class HazardAgent(BaseAgent):
    """
    Domain agent for marine hazard evaluation and active alerts.
    Delegates to HazardTool → services.hazard_service.evaluate_hazards.
    Preserves existing hazard states and telemetry snapshots without new thresholds.
    """

    name: str = "hazard_agent"
    description: str = (
        "Evaluates marine hazards and active alerts "
        "(wave conditions, wind squalls, gusts, precipitation) "
        "using real telemetry via HazardTool."
    )

    def __init__(self, tool: Optional[HazardTool] = None):
        super().__init__()
        self.tool = tool or HazardTool()

    async def execute(self, request: AgentRequest) -> AgentResult:
        """
        Execute marine hazard evaluation.

        Args:
            request: AgentRequest with latitude and longitude.

        Returns:
            AgentResult containing hazard state, active alerts, and evidence.
        """
        lat = request.latitude
        lon = request.longitude

        # 1. Coordinate boundary guard
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return self.create_error_result(
                error_message=f"Invalid geographic coordinates: latitude={lat}, longitude={lon}",
                evidence=self.create_evidence(
                    source="ORCA Marine Hazard Engine",
                    source_type="rule_engine",
                    data_status=DataStatus.ERROR,
                ),
            )

        # 2. Delegate to HazardTool — do not call hazard_service directly
        tool_result = await self.tool.execute(lat=lat, lon=lon)

        # 3. Propagate tool failure cleanly
        if tool_result.status == AgentStatus.FAILED:
            error_msg = (
                tool_result.errors[0]
                if tool_result.errors
                else "Failed to evaluate marine hazards"
            )
            return self.create_error_result(
                error_message=error_msg,
                errors=tool_result.errors,
                evidence=tool_result.evidence,
            )

        # 4. Preserve hazard data and evidence verbatim
        hazard_data = tool_result.data or {}
        evidence = tool_result.evidence

        overall_state = hazard_data.get("overall_state", "UNKNOWN")
        active_alerts = hazard_data.get("active_alerts", [])
        alert_count = len(active_alerts)

        # 5. Map overall_state to confidence
        # 'clear' → full confidence in safe state
        # 'caution' → moderate confidence (marginal conditions)
        # 'high' → high confidence in hazardous state
        state_lower = (overall_state or "unknown").lower()
        if state_lower == "clear":
            confidence = 1.0
            status = AgentStatus.SUCCESS
        elif state_lower in ("caution", "moderate"):
            confidence = 0.75
            status = AgentStatus.PARTIAL
        elif state_lower == "high":
            confidence = 1.0  # High confidence in the hazard detection, not the safety
            status = AgentStatus.SUCCESS
        else:
            confidence = 0.5
            status = AgentStatus.PARTIAL

        # 6. Human-readable summary using real values only
        alert_labels = [a.get("type", "unknown") for a in active_alerts[:3]]
        alert_str = ", ".join(alert_labels) if alert_labels else "none"
        message = (
            f"Marine hazard evaluation at ({lat:.4f}, {lon:.4f}): "
            f"overall state={overall_state}, "
            f"{alert_count} active alert(s)"
            + (f" [{alert_str}]" if alert_labels else "")
            + "."
        )

        return AgentResult(
            agent=self.name,
            status=status,
            data=hazard_data,
            evidence=evidence,
            confidence=confidence,
            message=message,
            errors=[],
        )
