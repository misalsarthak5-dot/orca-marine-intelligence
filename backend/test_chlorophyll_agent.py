"""
Verification Suite for ORCA Phase 3.5: Chlorophyll Agent
Tests:
1. Agent contract & BaseAgent inheritance
2. Dependency injection via constructor
3. Valid coordinates execution
4. Invalid coordinates rejection
5. Successful execution if source is available (mock)
6. Honest UNAVAILABLE handling (PARTIAL, not FAILED, no fake data)
7. Tool failure propagation -> FAILED AgentResult
8. Evidence preservation verbatim
9. Confidence propagation
10. Tool invocation verification (coordinates passed accurately)
11. AgentResult schema & structure
12. Live integration test
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
from agents.chlorophyll_agent import ChlorophyllAgent
from tools.base_tool import ToolResult
from tools.chlorophyll_tool import ChlorophyllTool


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_evidence(
    data_status: DataStatus = DataStatus.LIVE,
    observed_at: str = "2026-09-29T10:00:00Z",
) -> Evidence:
    return Evidence(
        source="NASA Ocean Color / MODIS-Aqua",
        source_type="satellite",
        observed_at=observed_at,
        data_status=data_status,
        reference="https://oceancolor.gsfc.nasa.gov",
    )


def _make_success_tool_result() -> ToolResult:
    return ToolResult(
        tool="chlorophyll_tool",
        status=AgentStatus.SUCCESS,
        data={
            "available": True,
            "value": 0.38,
            "unit": "mg/m³",
            "source": "NASA Ocean Color / MODIS-Aqua Level-3 Mapped",
            "provider": "NASA Earthdata Cloud / OB.DAAC",
            "status": "authenticated_granule_located",
            "granule": "AQUA_MODIS.20260929.L3m.DAY.CHL.chlor_a.4km.nc",
            "timestamp": "2026-09-29T10:00:00Z",
            "coordinates": {"latitude": 15.4989, "longitude": 73.8278},
        },
        evidence=_make_evidence(DataStatus.LIVE, "2026-09-29T10:00:00Z"),
        errors=[],
        metadata={
            "source": "NASA Ocean Color / MODIS-Aqua Level-3 Mapped",
            "provider": "NASA Earthdata Cloud / OB.DAAC",
            "chlorophyll_status": "authenticated_granule_located",
            "confidence": 1.0,
        },
    )


def _make_unavailable_tool_result() -> ToolResult:
    return ToolResult(
        tool="chlorophyll_tool",
        status=AgentStatus.PARTIAL,
        data={
            "available": False,
            "value": None,
            "unit": "mg/m³",
            "source": "NASA Ocean Color / MODIS-Aqua",
            "provider": "NASA Earthdata / OB.DAAC",
            "status": "not_connected",
            "message": "Chlorophyll-a satellite data source is not connected.",
            "coordinates": {"latitude": 15.4989, "longitude": 73.8278},
        },
        evidence=_make_evidence(DataStatus.UNAVAILABLE, None),
        errors=[],
        metadata={
            "source": "NASA Ocean Color / MODIS-Aqua",
            "provider": "NASA Earthdata / OB.DAAC",
            "chlorophyll_status": "not_connected",
            "confidence": 0.5,
        },
    )


def _make_failed_tool_result(msg: str = "NASA Earthdata timeout") -> ToolResult:
    return ToolResult(
        tool="chlorophyll_tool",
        status=AgentStatus.FAILED,
        data=None,
        evidence=Evidence(
            source="NASA Ocean Color / MODIS-Aqua",
            source_type="satellite",
            data_status=DataStatus.ERROR,
            reference="https://oceancolor.gsfc.nasa.gov",
        ),
        errors=[msg],
        metadata={},
    )


# ---------------------------------------------------------------------------
# TEST 1 - Agent inheritance / contract
# ---------------------------------------------------------------------------

def test_chlorophyll_agent_inherits_base_agent():
    print("\n[TEST 1] ChlorophyllAgent inherits BaseAgent and satisfies contract...")
    agent = ChlorophyllAgent()
    assert isinstance(agent, BaseAgent)
    assert agent.name == "chlorophyll_agent"
    assert hasattr(agent, "execute")
    assert hasattr(agent, "create_error_result")
    assert hasattr(agent, "create_evidence")
    print("  [PASS] ChlorophyllAgent correctly inherits BaseAgent.")


# ---------------------------------------------------------------------------
# TEST 2 - Dependency injection
# ---------------------------------------------------------------------------

def test_chlorophyll_agent_dependency_injection():
    print("\n[TEST 2] ChlorophyllAgent dependency injection via constructor...")
    mock_tool = MagicMock(spec=ChlorophyllTool)
    agent = ChlorophyllAgent(tool=mock_tool)
    assert agent.tool is mock_tool
    print("  [PASS] Dependency injection correctly replaces default ChlorophyllTool.")


# ---------------------------------------------------------------------------
# TEST 3 - Valid coordinates execution
# ---------------------------------------------------------------------------

async def test_chlorophyll_agent_valid_coordinates():
    print("\n[TEST 3] ChlorophyllAgent with valid coordinates...")
    mock_tool = AsyncMock(spec=ChlorophyllTool)
    mock_tool.execute.return_value = _make_success_tool_result()

    agent = ChlorophyllAgent(tool=mock_tool)
    req = AgentRequest(latitude=15.4989, longitude=73.8278)
    res = await agent.execute(req)

    assert isinstance(res, AgentResult)
    assert res.status == AgentStatus.SUCCESS
    print("  [PASS] Valid coordinates successfully processed.")


# ---------------------------------------------------------------------------
# TEST 4 - Invalid coordinates rejection
# ---------------------------------------------------------------------------

async def test_chlorophyll_agent_invalid_coordinates():
    print("\n[TEST 4] ChlorophyllAgent coordinate validation...")
    mock_tool = AsyncMock(spec=ChlorophyllTool)
    agent = ChlorophyllAgent(tool=mock_tool)

    # 1. Pydantic schema rejection
    try:
        AgentRequest(latitude=-95.0, longitude=73.0)
        assert False, "Should have raised ValidationError for latitude < -90"
    except Exception as e:
        assert "greater_than_equal" in str(e) or "validation error" in str(e).lower()

    # 2. Defense-in-depth guard in execute() via model_construct
    for lat, lon in [(-95.0, 73.0), (95.0, 73.0), (15.0, -185.0), (15.0, 185.0)]:
        req = AgentRequest.model_construct(latitude=lat, longitude=lon, context={})
        res = await agent.execute(req)

        assert isinstance(res, AgentResult)
        assert res.status == AgentStatus.FAILED
        assert res.data is None
        assert res.confidence == 0.0
        assert "Invalid geographic coordinates" in res.message
        assert res.evidence is not None
        assert res.evidence.data_status == DataStatus.ERROR
        mock_tool.execute.assert_not_called()

    print("  [PASS] Coordinate boundary violations rejected before tool invocation.")


# ---------------------------------------------------------------------------
# TEST 5 - Successful execution if source is available
# ---------------------------------------------------------------------------

async def test_chlorophyll_agent_success():
    print("\n[TEST 5] ChlorophyllAgent successful execution when source available...")
    mock_tool = AsyncMock(spec=ChlorophyllTool)
    mock_tool.execute.return_value = _make_success_tool_result()

    agent = ChlorophyllAgent(tool=mock_tool)
    req = AgentRequest(latitude=15.4989, longitude=73.8278)
    res = await agent.execute(req)

    assert isinstance(res, AgentResult)
    assert res.agent == "chlorophyll_agent"
    assert res.status == AgentStatus.SUCCESS
    assert res.confidence == 1.0
    assert res.data["available"] is True
    assert res.data["value"] == 0.38
    assert res.evidence.data_status == DataStatus.LIVE
    assert "0.38 mg/m³" in res.message
    print("  [PASS] Successful execution correctly mapped to AgentResult.")


# ---------------------------------------------------------------------------
# TEST 6 - UNAVAILABLE behavior (honest disclosure, no fake data)
# ---------------------------------------------------------------------------

async def test_chlorophyll_agent_unavailable():
    print("\n[TEST 6] ChlorophyllAgent honest UNAVAILABLE disclosure...")
    mock_tool = AsyncMock(spec=ChlorophyllTool)
    mock_tool.execute.return_value = _make_unavailable_tool_result()

    agent = ChlorophyllAgent(tool=mock_tool)
    req = AgentRequest(latitude=15.4989, longitude=73.8278)
    res = await agent.execute(req)

    assert isinstance(res, AgentResult)
    # UNAVAILABLE data is an honest PARTIAL state, never FAILED or fabricated SUCCESS
    assert res.status == AgentStatus.PARTIAL
    assert res.confidence == 0.5
    assert res.data["available"] is False
    assert res.data["value"] is None
    assert res.evidence.data_status == DataStatus.UNAVAILABLE
    assert "unavailable" in res.message.lower()
    print("  [PASS] UNAVAILABLE telemetry preserved honestly as PARTIAL with confidence 0.5.")


# ---------------------------------------------------------------------------
# TEST 7 - Error handling
# ---------------------------------------------------------------------------

async def test_chlorophyll_agent_error_handling():
    print("\n[TEST 7] ChlorophyllAgent tool error propagation...")
    mock_tool = AsyncMock(spec=ChlorophyllTool)
    mock_tool.execute.return_value = _make_failed_tool_result("Earthdata timeout")

    agent = ChlorophyllAgent(tool=mock_tool)
    req = AgentRequest(latitude=15.4989, longitude=73.8278)
    res = await agent.execute(req)

    assert res.status == AgentStatus.FAILED
    assert res.data is None
    assert res.confidence == 0.0
    assert len(res.errors) > 0
    assert "Earthdata timeout" in res.errors[0]
    assert res.evidence.data_status == DataStatus.ERROR
    print("  [PASS] Tool failure propagated to FAILED AgentResult.")


# ---------------------------------------------------------------------------
# TEST 8 - Evidence propagation
# ---------------------------------------------------------------------------

async def test_chlorophyll_agent_evidence_propagation():
    print("\n[TEST 8] Evidence propagation verification...")
    mock_tool = AsyncMock(spec=ChlorophyllTool)
    expected_ev = _make_evidence(DataStatus.LIVE, "2026-09-29T08:30:00Z")
    mock_result = _make_success_tool_result()
    mock_result.evidence = expected_ev
    mock_tool.execute.return_value = mock_result

    agent = ChlorophyllAgent(tool=mock_tool)
    req = AgentRequest(latitude=10.0, longitude=76.0)
    res = await agent.execute(req)

    assert res.evidence is expected_ev
    assert res.evidence.observed_at == "2026-09-29T08:30:00Z"
    assert res.evidence.source_type == "satellite"
    print("  [PASS] Evidence object forwarded verbatim.")


# ---------------------------------------------------------------------------
# TEST 9 - Confidence propagation
# ---------------------------------------------------------------------------

async def test_chlorophyll_agent_confidence_propagation():
    print("\n[TEST 9] Confidence propagation from tool metadata...")
    mock_tool = AsyncMock(spec=ChlorophyllTool)
    mock_result = _make_success_tool_result()
    mock_result.metadata["confidence"] = 0.92
    mock_tool.execute.return_value = mock_result

    agent = ChlorophyllAgent(tool=mock_tool)
    req = AgentRequest(latitude=15.0, longitude=73.0)
    res = await agent.execute(req)

    assert res.confidence == 0.92
    print("  [PASS] Confidence value accurately propagated from tool metadata.")


# ---------------------------------------------------------------------------
# TEST 10 - Tool invocation coordinates
# ---------------------------------------------------------------------------

async def test_chlorophyll_agent_tool_invocation():
    print("\n[TEST 10] ChlorophyllTool invocation with accurate coordinates...")
    mock_tool = AsyncMock(spec=ChlorophyllTool)
    mock_tool.execute.return_value = _make_success_tool_result()

    agent = ChlorophyllAgent(tool=mock_tool)
    req = AgentRequest(latitude=19.0760, longitude=72.8777)
    await agent.execute(req)

    mock_tool.execute.assert_awaited_once_with(lat=19.0760, lon=72.8777)
    print("  [PASS] ChlorophyllTool called with exact latitude and longitude.")


# ---------------------------------------------------------------------------
# TEST 11 - AgentResult structure
# ---------------------------------------------------------------------------

async def test_chlorophyll_agent_result_structure():
    print("\n[TEST 11] AgentResult structure compliance...")
    mock_tool = AsyncMock(spec=ChlorophyllTool)
    mock_tool.execute.return_value = _make_success_tool_result()

    agent = ChlorophyllAgent(tool=mock_tool)
    req = AgentRequest(latitude=15.4989, longitude=73.8278)
    res = await agent.execute(req)

    for field in ["agent", "status", "data", "evidence", "confidence", "message", "errors"]:
        assert hasattr(res, field), f"Missing field: {field}"
    assert isinstance(res.confidence, float)
    assert isinstance(res.errors, list)
    print("  [PASS] AgentResult schema fully satisfied.")


# ---------------------------------------------------------------------------
# TEST 12 - Live integration test
# ---------------------------------------------------------------------------

async def test_chlorophyll_agent_live_integration():
    print("\n[TEST 12] Live integration test (ChlorophyllAgent -> ChlorophyllTool -> real service)...")
    agent = ChlorophyllAgent()
    req = AgentRequest(latitude=15.4989, longitude=73.8278)
    res = await agent.execute(req)

    assert isinstance(res, AgentResult)
    assert res.agent == "chlorophyll_agent"
    assert res.evidence is not None
    print(f"  Live status: {res.status.value}")
    print(f"  DataStatus: {res.evidence.data_status.value}")
    print(f"  Confidence: {res.confidence}")
    print(f"  Source: {res.evidence.source}")
    print(f"  Message: {res.message}")
    print("  [PASS] Live ChlorophyllAgent integration test passed.")


async def main():
    print("=" * 60)
    print("ORCA PHASE 3.5 - CHLOROPHYLL AGENT VERIFICATION SUITE")
    print("=" * 60)

    test_chlorophyll_agent_inherits_base_agent()
    test_chlorophyll_agent_dependency_injection()
    await test_chlorophyll_agent_valid_coordinates()
    await test_chlorophyll_agent_invalid_coordinates()
    await test_chlorophyll_agent_success()
    await test_chlorophyll_agent_unavailable()
    await test_chlorophyll_agent_error_handling()
    await test_chlorophyll_agent_evidence_propagation()
    await test_chlorophyll_agent_confidence_propagation()
    await test_chlorophyll_agent_tool_invocation()
    await test_chlorophyll_agent_result_structure()
    await test_chlorophyll_agent_live_integration()

    print("\n" + "=" * 60)
    print("ALL CHLOROPHYLL AGENT TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
