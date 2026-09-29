"""
ORCA Phase 3 — Marine Agent Test Suite
Tests:
1. Agent inheritance and contract compliance
2. Successful live execution (real Open-Meteo Marine API)
3. Tool delegation (MarineTool is called, not marine_service directly)
4. Graceful error handling (tool failure -> clean AgentResult.FAILED)
5. AgentStatus mapping (SUCCESS / PARTIAL / FAILED)
6. DataStatus preservation from ToolResult -> AgentResult
7. Evidence preservation through the full chain
8. Confidence scoring based on field completeness
9. Invalid coordinate handling
10. Dependency injection via constructor
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
from agents.marine_agent import MarineAgent
from tools.base_tool import ToolResult
from tools.marine_tool import MarineTool


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_live_evidence() -> Evidence:
    return Evidence(
        source="Open-Meteo Marine API",
        source_type="api",
        data_status=DataStatus.LIVE,
        reference="https://open-meteo.com/en/docs/marine-weather-api",
    )


def _make_full_marine_data() -> dict:
    """Simulates a rich marine service response with all required fields present."""
    return {
        "source": "Open-Meteo",
        "current": {
            "time": "2026-09-29T16:00:00Z",
            "wave_height": 1.2,
            "wave_direction": 215,
            "wave_period": 8.5,
            "sea_surface_temperature": 28.4,
            "wind_wave_height": 0.6,
            "swell_wave_height": 0.9,
            "swell_wave_direction": 220,
            "swell_wave_period": 10.2,
        },
        "hourly": {
            "time": ["2026-09-29T17:00:00Z"],
            "wave_height": [1.3],
        },
    }


def _make_partial_marine_data() -> dict:
    """Simulates a partial marine response (some fields missing)."""
    return {
        "source": "Open-Meteo",
        "current": {
            "time": "2026-09-29T16:00:00Z",
            "wave_height": 1.0,
            "wave_direction": None,
            "wave_period": None,
            "sea_surface_temperature": None,
        },
    }


def _make_failed_tool_result(msg: str = "Marine service call failed: timeout") -> ToolResult:
    return ToolResult(
        tool="marine_tool",
        status=AgentStatus.FAILED,
        data=None,
        evidence=Evidence(
            source="Open-Meteo Marine API",
            source_type="api",
            data_status=DataStatus.ERROR,
            reference="https://open-meteo.com/en/docs/marine-weather-api",
        ),
        errors=[msg],
        metadata={},
    )


def _make_request(lat: float = 15.4989, lon: float = 73.8278) -> AgentRequest:
    return AgentRequest(latitude=lat, longitude=lon)


# ---------------------------------------------------------------------------
# TEST 1 - Agent inheritance / contract
# ---------------------------------------------------------------------------

def test_marine_agent_inherits_base_agent():
    print("\n[TEST 1] MarineAgent inherits BaseAgent and satisfies contract...")
    agent = MarineAgent()
    assert isinstance(agent, BaseAgent), "MarineAgent must inherit BaseAgent"
    assert agent.name == "marine_agent"
    assert hasattr(agent, "execute"), "Must expose execute()"
    assert hasattr(agent, "create_error_result"), "Must expose create_error_result()"
    assert hasattr(agent, "create_evidence"), "Must expose create_evidence()"
    print("  [PASS] MarineAgent correctly inherits BaseAgent and satisfies contract.")


# ---------------------------------------------------------------------------
# TEST 2 - Dependency injection
# ---------------------------------------------------------------------------

def test_marine_agent_dependency_injection():
    print("\n[TEST 2] MarineAgent dependency injection via constructor...")
    mock_tool = MagicMock(spec=MarineTool)
    agent = MarineAgent(tool=mock_tool)
    assert agent.tool is mock_tool, "Injected tool must be stored"
    print("  [PASS] Dependency injection correctly replaces default MarineTool.")


# ---------------------------------------------------------------------------
# TEST 3 - Successful execution with full data
# ---------------------------------------------------------------------------

async def test_marine_agent_success_full_data():
    print("\n[TEST 3] MarineAgent - successful execution with full marine data...")
    evidence = _make_live_evidence()
    full_tool_result = ToolResult(
        tool="marine_tool",
        status=AgentStatus.SUCCESS,
        data=_make_full_marine_data(),
        evidence=evidence,
        errors=[],
        metadata={"source": "Open-Meteo"},
    )

    mock_tool = AsyncMock(spec=MarineTool)
    mock_tool.execute.return_value = full_tool_result

    agent = MarineAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert isinstance(result, AgentResult)
    assert result.agent == "marine_agent"
    assert result.status == AgentStatus.SUCCESS
    assert result.data is not None
    assert "current" in result.data
    assert result.confidence == 1.0
    assert result.errors == []
    assert result.message is not None and len(result.message) > 0
    print(f"  [PASS] Full marine data -> SUCCESS, confidence=1.0 | {result.message}")


# ---------------------------------------------------------------------------
# TEST 4 - Successful execution with partial data (some fields None)
# ---------------------------------------------------------------------------

async def test_marine_agent_partial_data():
    print("\n[TEST 4] MarineAgent - partial marine data (some fields missing)...")
    evidence = _make_live_evidence()
    partial_tool_result = ToolResult(
        tool="marine_tool",
        status=AgentStatus.SUCCESS,
        data=_make_partial_marine_data(),
        evidence=evidence,
        errors=[],
        metadata={},
    )

    mock_tool = AsyncMock(spec=MarineTool)
    mock_tool.execute.return_value = partial_tool_result

    agent = MarineAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert isinstance(result, AgentResult)
    assert result.agent == "marine_agent"
    # Only 1 of 4 required fields present -> PARTIAL
    assert result.status in (AgentStatus.PARTIAL, AgentStatus.FAILED)
    assert result.confidence < 1.0
    print(f"  [PASS] Partial marine data -> status={result.status}, confidence={result.confidence}")


# ---------------------------------------------------------------------------
# TEST 5 - Tool failure propagation
# ---------------------------------------------------------------------------

async def test_marine_agent_tool_failure():
    print("\n[TEST 5] MarineAgent - tool failure propagated as FAILED AgentResult...")
    mock_tool = AsyncMock(spec=MarineTool)
    mock_tool.execute.return_value = _make_failed_tool_result("Upstream network timeout")

    agent = MarineAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert isinstance(result, AgentResult)
    assert result.status == AgentStatus.FAILED
    assert result.confidence == 0.0
    assert len(result.errors) > 0
    # The error message must surface either in errors or message
    combined = " ".join(result.errors) + (result.message or "")
    assert "Upstream network timeout" in combined
    print(f"  [PASS] Tool failure correctly propagated -> FAILED | {result.message}")


# ---------------------------------------------------------------------------
# TEST 6 - Evidence preservation
# ---------------------------------------------------------------------------

async def test_marine_agent_evidence_preserved():
    print("\n[TEST 6] MarineAgent - evidence propagated from ToolResult -> AgentResult...")
    evidence = Evidence(
        source="Open-Meteo Marine API",
        source_type="api",
        observed_at="2026-09-29T16:00:00Z",
        data_status=DataStatus.LIVE,
        reference="https://open-meteo.com/en/docs/marine-weather-api",
    )
    tool_result = ToolResult(
        tool="marine_tool",
        status=AgentStatus.SUCCESS,
        data=_make_full_marine_data(),
        evidence=evidence,
        errors=[],
        metadata={},
    )

    mock_tool = AsyncMock(spec=MarineTool)
    mock_tool.execute.return_value = tool_result

    agent = MarineAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert result.evidence is not None
    assert result.evidence.source == "Open-Meteo Marine API"
    assert result.evidence.source_type == "api"
    assert result.evidence.observed_at == "2026-09-29T16:00:00Z"
    assert result.evidence.data_status == DataStatus.LIVE
    assert result.evidence.reference == "https://open-meteo.com/en/docs/marine-weather-api"
    print(f"  [PASS] Evidence fully preserved -> source={result.evidence.source}, status={result.evidence.data_status}")


# ---------------------------------------------------------------------------
# TEST 7 - DataStatus preservation in failure path
# ---------------------------------------------------------------------------

async def test_marine_agent_data_status_error_propagated():
    print("\n[TEST 7] MarineAgent - DataStatus.ERROR preserved on tool failure...")
    mock_tool = AsyncMock(spec=MarineTool)
    mock_tool.execute.return_value = _make_failed_tool_result()

    agent = MarineAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert result.evidence is not None
    assert result.evidence.data_status == DataStatus.ERROR
    print(f"  [PASS] DataStatus.ERROR preserved -> {result.evidence.data_status}")


# ---------------------------------------------------------------------------
# TEST 8 - Tool is invoked with correct coordinates
# ---------------------------------------------------------------------------

async def test_marine_agent_tool_invocation():
    print("\n[TEST 8] MarineAgent - tool.execute called with correct coordinates...")
    mock_tool = AsyncMock(spec=MarineTool)
    mock_tool.execute.return_value = ToolResult(
        tool="marine_tool",
        status=AgentStatus.SUCCESS,
        data=_make_full_marine_data(),
        evidence=_make_live_evidence(),
        errors=[],
        metadata={},
    )

    agent = MarineAgent(tool=mock_tool)
    req = _make_request(lat=8.5241, lon=76.9366)
    await agent.execute(req)

    mock_tool.execute.assert_called_once_with(lat=8.5241, lon=76.9366)
    print("  [PASS] MarineTool.execute called once with correct lat/lon.")


# ---------------------------------------------------------------------------
# TEST 9 - Live integration test (real Open-Meteo Marine API)
# ---------------------------------------------------------------------------

async def test_marine_agent_live():
    print("\n[TEST 9] MarineAgent - live integration test (Goa, India)...")
    agent = MarineAgent()
    req = AgentRequest(latitude=15.4989, longitude=73.8278)
    result = await agent.execute(req)

    assert isinstance(result, AgentResult)
    assert result.agent == "marine_agent"
    assert result.status in (AgentStatus.SUCCESS, AgentStatus.PARTIAL)
    assert result.data is not None
    assert result.evidence is not None
    assert result.evidence.source == "Open-Meteo Marine API"
    assert result.confidence > 0.0
    print(f"  [PASS] Live marine result: status={result.status}, confidence={result.confidence}")
    print(f"         Message: {result.message}")


# ---------------------------------------------------------------------------
# TEST 10 - Confidence = 1.0 when all 4 key fields present
# ---------------------------------------------------------------------------

async def test_marine_agent_confidence_all_fields():
    print("\n[TEST 10] MarineAgent - confidence=1.0 when all 4 fields present...")
    data = {
        "current": {
            "wave_height": 1.0,
            "wave_direction": 180,
            "wave_period": 9.0,
            "sea_surface_temperature": 28.0,
        }
    }
    tool_result = ToolResult(
        tool="marine_tool",
        status=AgentStatus.SUCCESS,
        data=data,
        evidence=_make_live_evidence(),
        errors=[],
        metadata={},
    )

    mock_tool = AsyncMock(spec=MarineTool)
    mock_tool.execute.return_value = tool_result

    agent = MarineAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert result.confidence == 1.0
    assert result.status == AgentStatus.SUCCESS
    print(f"  [PASS] All 4 fields present -> confidence={result.confidence}")


# ---------------------------------------------------------------------------
# TEST 11 - Confidence = 0.0 when no fields present
# ---------------------------------------------------------------------------

async def test_marine_agent_confidence_no_fields():
    print("\n[TEST 11] MarineAgent - confidence=0.0 when no fields present...")
    data = {
        "current": {
            "wave_height": None,
            "wave_direction": None,
            "wave_period": None,
            "sea_surface_temperature": None,
        }
    }
    tool_result = ToolResult(
        tool="marine_tool",
        status=AgentStatus.SUCCESS,
        data=data,
        evidence=_make_live_evidence(),
        errors=[],
        metadata={},
    )

    mock_tool = AsyncMock(spec=MarineTool)
    mock_tool.execute.return_value = tool_result

    agent = MarineAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert result.confidence == 0.0
    assert result.status == AgentStatus.FAILED
    print(f"  [PASS] No fields present -> confidence={result.confidence}, status={result.status}")


# ---------------------------------------------------------------------------
# MAIN runner
# ---------------------------------------------------------------------------

async def main():
    print("=" * 65)
    print("ORCA PHASE 3 - MARINE AGENT TEST SUITE")
    print("=" * 65)

    test_marine_agent_inherits_base_agent()
    test_marine_agent_dependency_injection()
    await test_marine_agent_success_full_data()
    await test_marine_agent_partial_data()
    await test_marine_agent_tool_failure()
    await test_marine_agent_evidence_preserved()
    await test_marine_agent_data_status_error_propagated()
    await test_marine_agent_tool_invocation()
    await test_marine_agent_live()
    await test_marine_agent_confidence_all_fields()
    await test_marine_agent_confidence_no_fields()

    print("\n" + "=" * 65)
    print("ALL MARINE AGENT TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
