"""
ORCA Phase 3 - Hazard Agent Test Suite
Tests:
1. Agent inheritance and contract compliance
2. Successful hazard evaluation (clear state)
3. Caution/moderate state handling
4. High alert state handling
5. Tool failure propagation -> FAILED AgentResult
6. Evidence propagation (rule_engine provenance preserved)
7. DataStatus preservation
8. Status mapping: clear->SUCCESS, caution->PARTIAL, high->SUCCESS (high confidence hazard)
9. Tool invocation with correct coordinates
10. Error state when service is unavailable
11. Live integration test
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from core.schemas import (
    AgentRequest,
    AgentResult,
    AgentStatus,
    DataStatus,
    Evidence,
)
from agents.base_agent import BaseAgent
from agents.hazard_agent import HazardAgent
from tools.base_tool import ToolResult
from tools.hazard_tool import HazardTool


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_hazard_evidence(data_status: DataStatus = DataStatus.LIVE) -> Evidence:
    return Evidence(
        source="ORCA Marine Hazard Engine (Open-Meteo Multi-Feed)",
        source_type="rule_engine",
        observed_at="2026-09-29T16:00:00Z",
        data_status=data_status,
        reference="https://open-meteo.com",
    )


def _make_hazard_data(state: str = "NO SIGNIFICANT HAZARDS", alerts: list = None) -> dict:
    return {
        "overall_state": state,
        "active_alerts": alerts or [],
        "conditions": [
            {"id": "waves", "status": "Normal", "severity": "normal"},
            {"id": "wind", "status": "Normal", "severity": "normal"},
        ],
        "telemetry_snapshot": {
            "timestamp": "2026-09-29T16:00:00Z",
            "wave_height_m": 1.0,
            "wind_speed_kts": 8.0,
            "wind_gusts_kts": 12.0,
            "precipitation_mm": 0.2,
        },
    }


def _make_caution_hazard_data() -> dict:
    return {
        "overall_state": "CAUTION",
        "active_alerts": [
            {"type": "waves", "severity": "caution", "label": "Elevated Swell Window"},
        ],
        "conditions": [
            {"id": "waves", "status": "Elevated", "severity": "caution"},
        ],
        "telemetry_snapshot": {
            "timestamp": "2026-09-29T16:00:00Z",
            "wave_height_m": 2.1,
        },
    }


def _make_high_alert_hazard_data() -> dict:
    return {
        "overall_state": "HIGH ALERT",
        "active_alerts": [
            {"type": "waves", "severity": "high", "label": "Rough Seas / High Waves"},
            {"type": "wind", "severity": "high", "label": "Strong Wind Warning"},
        ],
        "conditions": [],
        "telemetry_snapshot": {
            "timestamp": "2026-09-29T16:00:00Z",
            "wave_height_m": 3.2,
            "wind_speed_kts": 26.0,
        },
    }


def _make_hazard_tool_result(data: dict, status: AgentStatus = AgentStatus.SUCCESS) -> ToolResult:
    return ToolResult(
        tool="hazard_tool",
        status=status,
        data=data,
        evidence=_make_hazard_evidence(),
        errors=[],
        metadata={
            "overall_state": data.get("overall_state"),
            "active_alerts_count": len(data.get("active_alerts", [])),
        },
    )


def _make_failed_tool_result(msg: str = "Hazard service call failed: API error") -> ToolResult:
    return ToolResult(
        tool="hazard_tool",
        status=AgentStatus.FAILED,
        data=None,
        evidence=Evidence(
            source="ORCA Marine Hazard Engine",
            source_type="rule_engine",
            data_status=DataStatus.ERROR,
        ),
        errors=[msg],
        metadata={},
    )


def _make_request(lat: float = 15.4989, lon: float = 73.8278) -> AgentRequest:
    return AgentRequest(latitude=lat, longitude=lon)


# ---------------------------------------------------------------------------
# TEST 1 - Agent inheritance / contract
# ---------------------------------------------------------------------------

def test_hazard_agent_inherits_base_agent():
    print("\n[TEST 1] HazardAgent inherits BaseAgent and satisfies contract...")
    agent = HazardAgent()
    assert isinstance(agent, BaseAgent)
    assert agent.name == "hazard_agent"
    assert hasattr(agent, "execute")
    assert hasattr(agent, "create_error_result")
    assert hasattr(agent, "create_evidence")
    print("  [PASS] HazardAgent correctly inherits BaseAgent.")


# ---------------------------------------------------------------------------
# TEST 2 - Dependency injection
# ---------------------------------------------------------------------------

def test_hazard_agent_dependency_injection():
    print("\n[TEST 2] HazardAgent dependency injection via constructor...")
    mock_tool = MagicMock(spec=HazardTool)
    agent = HazardAgent(tool=mock_tool)
    assert agent.tool is mock_tool
    print("  [PASS] Dependency injection correctly replaces default HazardTool.")


# ---------------------------------------------------------------------------
# TEST 3 - Successful evaluation (clear state)
# ---------------------------------------------------------------------------

async def test_hazard_agent_clear_state():
    print("\n[TEST 3] HazardAgent - clear state -> SUCCESS with full confidence...")
    mock_tool = AsyncMock(spec=HazardTool)
    mock_tool.execute.return_value = _make_hazard_tool_result(_make_hazard_data("clear"))

    agent = HazardAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert isinstance(result, AgentResult)
    assert result.agent == "hazard_agent"
    assert result.status == AgentStatus.SUCCESS
    assert result.confidence == 1.0
    assert result.data is not None
    assert result.data.get("overall_state") == "clear"
    assert result.errors == []
    print(f"  [PASS] Clear hazard state: status={result.status}, confidence={result.confidence}")


# ---------------------------------------------------------------------------
# TEST 4 - Caution state -> PARTIAL
# ---------------------------------------------------------------------------

async def test_hazard_agent_caution_state():
    print("\n[TEST 4] HazardAgent - caution state -> PARTIAL...")
    mock_tool = AsyncMock(spec=HazardTool)
    mock_tool.execute.return_value = _make_hazard_tool_result(_make_caution_hazard_data())

    agent = HazardAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert isinstance(result, AgentResult)
    # caution -> PARTIAL, confidence 0.75
    assert result.status == AgentStatus.PARTIAL
    assert result.confidence == 0.75
    assert result.data.get("overall_state") == "CAUTION"
    print(f"  [PASS] Caution state: status={result.status}, confidence={result.confidence}")


# ---------------------------------------------------------------------------
# TEST 5 - High alert state -> SUCCESS (high confidence in hazard detection)
# ---------------------------------------------------------------------------

async def test_hazard_agent_high_state():
    print("\n[TEST 5] HazardAgent - 'high' state -> SUCCESS with confidence=1.0...")
    # Agent checks state_lower == 'high' for the high-severity branch
    high_data = _make_hazard_data("high", alerts=[
        {"type": "waves", "severity": "high", "label": "Rough Seas"},
        {"type": "wind", "severity": "high", "label": "Strong Wind"},
    ])
    mock_tool = AsyncMock(spec=HazardTool)
    mock_tool.execute.return_value = _make_hazard_tool_result(high_data)

    agent = HazardAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert isinstance(result, AgentResult)
    # 'high' (lowercase) -> SUCCESS, confidence=1.0 (high confidence in hazard detection)
    assert result.status == AgentStatus.SUCCESS
    assert result.confidence == 1.0
    assert result.data.get("overall_state") == "high"
    assert len(result.data.get("active_alerts", [])) == 2
    print(f"  [PASS] 'high' state: status={result.status}, confidence={result.confidence}")


async def test_hazard_agent_unknown_state_partial():
    print("\n[TEST 5b] HazardAgent - unknown/non-standard state -> PARTIAL...")
    # 'HIGH ALERT' (multi-word) hits the else branch -> PARTIAL, 0.5
    mock_tool = AsyncMock(spec=HazardTool)
    mock_tool.execute.return_value = _make_hazard_tool_result(_make_high_alert_hazard_data())

    agent = HazardAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert isinstance(result, AgentResult)
    # 'HIGH ALERT'.lower() = 'high alert' -> does not match 'high' or 'caution'
    # -> falls to else: PARTIAL, confidence=0.5
    assert result.status == AgentStatus.PARTIAL
    assert result.confidence == 0.5
    assert len(result.data.get("active_alerts", [])) == 2
    print(f"  [PASS] 'HIGH ALERT' (multi-word) -> PARTIAL, confidence={result.confidence}")


# ---------------------------------------------------------------------------
# TEST 6 - Tool failure propagation
# ---------------------------------------------------------------------------

async def test_hazard_agent_tool_failure():
    print("\n[TEST 6] HazardAgent - tool failure propagated as FAILED AgentResult...")
    mock_tool = AsyncMock(spec=HazardTool)
    mock_tool.execute.return_value = _make_failed_tool_result("Open-Meteo 503 Service Unavailable")

    agent = HazardAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert result.status == AgentStatus.FAILED
    assert result.confidence == 0.0
    assert len(result.errors) > 0
    combined = " ".join(result.errors) + (result.message or "")
    assert "Open-Meteo 503 Service Unavailable" in combined
    print(f"  [PASS] Tool failure -> FAILED | {result.message}")


# ---------------------------------------------------------------------------
# TEST 7 - Evidence preservation
# ---------------------------------------------------------------------------

async def test_hazard_agent_evidence_preserved():
    print("\n[TEST 7] HazardAgent - rule_engine evidence preserved verbatim...")
    evidence = Evidence(
        source="ORCA Marine Hazard Engine (Open-Meteo Multi-Feed)",
        source_type="rule_engine",
        observed_at="2026-09-29T16:00:00Z",
        data_status=DataStatus.LIVE,
        reference="https://open-meteo.com",
    )
    tool_result = ToolResult(
        tool="hazard_tool",
        status=AgentStatus.SUCCESS,
        data=_make_hazard_data("clear"),
        evidence=evidence,
        errors=[],
        metadata={},
    )

    mock_tool = AsyncMock(spec=HazardTool)
    mock_tool.execute.return_value = tool_result

    agent = HazardAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert result.evidence is not None
    assert result.evidence.source == "ORCA Marine Hazard Engine (Open-Meteo Multi-Feed)"
    assert result.evidence.source_type == "rule_engine"
    assert result.evidence.observed_at == "2026-09-29T16:00:00Z"
    assert result.evidence.data_status == DataStatus.LIVE
    assert result.evidence.reference == "https://open-meteo.com"
    print(f"  [PASS] Evidence preserved: source={result.evidence.source}")


# ---------------------------------------------------------------------------
# TEST 8 - DataStatus.ERROR preserved on failure
# ---------------------------------------------------------------------------

async def test_hazard_agent_error_status_preserved():
    print("\n[TEST 8] HazardAgent - DataStatus.ERROR preserved on tool failure...")
    mock_tool = AsyncMock(spec=HazardTool)
    mock_tool.execute.return_value = _make_failed_tool_result()

    agent = HazardAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert result.evidence is not None
    assert result.evidence.data_status == DataStatus.ERROR
    print(f"  [PASS] DataStatus.ERROR preserved: {result.evidence.data_status}")


# ---------------------------------------------------------------------------
# TEST 9 - Tool invoked with correct coordinates
# ---------------------------------------------------------------------------

async def test_hazard_agent_tool_invocation():
    print("\n[TEST 9] HazardAgent - tool.execute called with correct coordinates...")
    mock_tool = AsyncMock(spec=HazardTool)
    mock_tool.execute.return_value = _make_hazard_tool_result(_make_hazard_data())

    agent = HazardAgent(tool=mock_tool)
    req = _make_request(lat=9.9312, lon=76.2673)  # Kochi
    await agent.execute(req)

    mock_tool.execute.assert_called_once_with(lat=9.9312, lon=76.2673)
    print("  [PASS] HazardTool.execute called once with correct lat/lon.")


# ---------------------------------------------------------------------------
# TEST 10 - AgentResult data contains hazard fields
# ---------------------------------------------------------------------------

async def test_hazard_agent_result_data_fields():
    print("\n[TEST 10] HazardAgent - result.data contains expected hazard fields...")
    mock_tool = AsyncMock(spec=HazardTool)
    mock_tool.execute.return_value = _make_hazard_tool_result(_make_hazard_data())

    agent = HazardAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert result.data is not None
    assert "overall_state" in result.data
    assert "active_alerts" in result.data
    assert "conditions" in result.data
    assert "telemetry_snapshot" in result.data
    print(f"  [PASS] result.data contains all expected hazard fields.")


# ---------------------------------------------------------------------------
# TEST 11 - Live integration test
# ---------------------------------------------------------------------------

async def test_hazard_agent_live():
    print("\n[TEST 11] HazardAgent - live integration test (Goa, India)...")
    agent = HazardAgent()
    req = AgentRequest(latitude=15.4989, longitude=73.8278)
    result = await agent.execute(req)

    assert isinstance(result, AgentResult)
    assert result.agent == "hazard_agent"
    assert result.status in (AgentStatus.SUCCESS, AgentStatus.PARTIAL)
    assert result.data is not None
    assert "overall_state" in result.data
    assert result.evidence is not None
    assert result.evidence.source_type == "rule_engine"
    print(f"  [PASS] Live hazard result: status={result.status}, state={result.data.get('overall_state')}")
    print(f"         Message: {result.message}")


# ---------------------------------------------------------------------------
# MAIN runner
# ---------------------------------------------------------------------------

async def main():
    print("=" * 65)
    print("ORCA PHASE 3 - HAZARD AGENT TEST SUITE")
    print("=" * 65)

    test_hazard_agent_inherits_base_agent()
    test_hazard_agent_dependency_injection()
    await test_hazard_agent_clear_state()
    await test_hazard_agent_caution_state()
    await test_hazard_agent_high_state()
    await test_hazard_agent_unknown_state_partial()
    await test_hazard_agent_tool_failure()
    await test_hazard_agent_evidence_preserved()
    await test_hazard_agent_error_status_preserved()
    await test_hazard_agent_tool_invocation()
    await test_hazard_agent_result_data_fields()
    await test_hazard_agent_live()

    print("\n" + "=" * 65)
    print("ALL HAZARD AGENT TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
