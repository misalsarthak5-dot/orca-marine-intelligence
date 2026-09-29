"""
ORCA Phase 3 - Route Agent Test Suite
Tests:
1. Agent inheritance and contract compliance
2. Successful route analysis (valid origin + destination)
3. Missing destination -> FAILED before tool call
4. Invalid destination coordinates -> FAILED
5. Tool failure propagation
6. No routes returned -> PARTIAL with confidence=0.0
7. Candidate corridors preserved in result.data
8. Evidence preservation
9. DataStatus preservation
10. Context parameters (destination_name, time_window, override_zones)
11. Confidence scoring (viable routes / total routes)
12. Tool invoked with correct parameters
13. Live integration test
"""

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock


def _safe(text) -> str:
    """Encode text safely for Windows console (cp1252 fallback)."""
    if text is None:
        return "None"
    return str(text).encode("ascii", errors="replace").decode("ascii")

from core.schemas import (
    AgentRequest,
    AgentResult,
    AgentStatus,
    DataStatus,
    Evidence,
)
from agents.base_agent import BaseAgent
from agents.route_agent import RouteAgent
from tools.base_tool import ToolResult
from tools.route_tool import RouteTool


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_route_evidence(data_status: DataStatus = DataStatus.LIVE) -> Evidence:
    return Evidence(
        source="ORCA Route Intelligence Engine (Multi-Source Feeds)",
        source_type="rule_engine",
        data_status=data_status,
        reference="Open-Meteo & INCOIS WebGIS",
    )


def _make_route_data(
    routes: list = None,
    recommended_id: str = "direct",
    time_window: str = "tomorrow_morning",
) -> dict:
    if routes is None:
        routes = [
            {
                "id": "direct",
                "name": "Direct Corridor",
                "risk_score": 25,
                "overall_status": "VIABLE",
                "waypoints": [[15.4989, 73.8278], [15.2000, 73.5000]],
            },
            {
                "id": "coastal",
                "name": "Coastal Route",
                "risk_score": 35,
                "overall_status": "VIABLE",
                "waypoints": [[15.4989, 73.8278], [15.35, 73.7], [15.2000, 73.5000]],
            },
            {
                "id": "offshore",
                "name": "Offshore Corridor",
                "risk_score": 50,
                "overall_status": "CAUTION",
                "waypoints": [[15.4989, 73.8278], [15.0, 73.2], [15.2000, 73.5000]],
            },
        ]
    return {
        "routes": routes,
        "recommended_route_id": recommended_id,
        "time_window": time_window,
        "origin": {"lat": 15.4989, "lon": 73.8278},
        "destination": {"lat": 15.2000, "lon": 73.5000, "name": "Target"},
    }


def _make_no_routes_data() -> dict:
    return {
        "routes": [],
        "recommended_route_id": None,
        "time_window": "tomorrow_morning",
    }


def _make_route_success_tool_result() -> ToolResult:
    return ToolResult(
        tool="route_tool",
        status=AgentStatus.SUCCESS,
        data=_make_route_data(),
        evidence=_make_route_evidence(),
        errors=[],
        metadata={"routes_count": 3, "recommended_route_id": "direct", "time_window": "tomorrow_morning"},
    )


def _make_route_no_routes_tool_result() -> ToolResult:
    return ToolResult(
        tool="route_tool",
        status=AgentStatus.SUCCESS,
        data=_make_no_routes_data(),
        evidence=_make_route_evidence(),
        errors=[],
        metadata={"routes_count": 0},
    )


def _make_failed_tool_result(msg: str = "Route service call failed: timeout") -> ToolResult:
    return ToolResult(
        tool="route_tool",
        status=AgentStatus.FAILED,
        data=None,
        evidence=Evidence(
            source="ORCA Route Intelligence Engine",
            source_type="rule_engine",
            data_status=DataStatus.ERROR,
        ),
        errors=[msg],
        metadata={},
    )


def _make_request(
    origin_lat: float = 15.4989,
    origin_lon: float = 73.8278,
    dest_lat: float = 15.2000,
    dest_lon: float = 73.5000,
    context: dict = None,
) -> AgentRequest:
    return AgentRequest(
        latitude=origin_lat,
        longitude=origin_lon,
        destination_latitude=dest_lat,
        destination_longitude=dest_lon,
        context=context or {},
    )


# ---------------------------------------------------------------------------
# TEST 1 - Agent inheritance / contract
# ---------------------------------------------------------------------------

def test_route_agent_inherits_base_agent():
    print("\n[TEST 1] RouteAgent inherits BaseAgent and satisfies contract...")
    agent = RouteAgent()
    assert isinstance(agent, BaseAgent)
    assert agent.name == "route_agent"
    assert hasattr(agent, "execute")
    assert hasattr(agent, "create_error_result")
    assert hasattr(agent, "create_evidence")
    print("  [PASS] RouteAgent correctly inherits BaseAgent.")


# ---------------------------------------------------------------------------
# TEST 2 - Dependency injection
# ---------------------------------------------------------------------------

def test_route_agent_dependency_injection():
    print("\n[TEST 2] RouteAgent dependency injection via constructor...")
    mock_tool = MagicMock(spec=RouteTool)
    agent = RouteAgent(tool=mock_tool)
    assert agent.tool is mock_tool
    print("  [PASS] Dependency injection correctly replaces default RouteTool.")


# ---------------------------------------------------------------------------
# TEST 3 - Successful route analysis
# ---------------------------------------------------------------------------

async def test_route_agent_success():
    print("\n[TEST 3] RouteAgent - successful route analysis (3 corridors)...")
    mock_tool = AsyncMock(spec=RouteTool)
    mock_tool.execute.return_value = _make_route_success_tool_result()

    agent = RouteAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert isinstance(result, AgentResult)
    assert result.agent == "route_agent"
    assert result.status == AgentStatus.SUCCESS
    assert result.data is not None
    assert "routes" in result.data
    assert len(result.data["routes"]) == 3
    assert result.data.get("recommended_route_id") == "direct"
    assert result.confidence > 0.0
    assert result.errors == []
    assert result.message is not None
    print(f"  [PASS] Route success: {len(result.data['routes'])} corridors, recommended=direct, confidence={result.confidence}")
    print(f"         Message: {_safe(result.message)}")


# ---------------------------------------------------------------------------
# TEST 4 - Missing destination -> FAILED before tool call
# ---------------------------------------------------------------------------

async def test_route_agent_missing_destination():
    print("\n[TEST 4] RouteAgent - missing destination -> FAILED before tool call...")
    mock_tool = AsyncMock(spec=RouteTool)
    mock_tool.execute.return_value = _make_route_success_tool_result()

    agent = RouteAgent(tool=mock_tool)
    # No destination_latitude / destination_longitude
    req = AgentRequest(latitude=15.4989, longitude=73.8278)
    result = await agent.execute(req)

    assert result.status == AgentStatus.FAILED
    assert result.confidence == 0.0
    assert len(result.errors) > 0
    # Tool must NOT be called - error is caught before delegation
    mock_tool.execute.assert_not_called()
    print(f"  [PASS] Missing destination -> FAILED (no tool call) | {_safe(result.message)}")


# ---------------------------------------------------------------------------
# TEST 5 - Tool failure propagation
# ---------------------------------------------------------------------------

async def test_route_agent_tool_failure():
    print("\n[TEST 5] RouteAgent - tool failure propagated as FAILED AgentResult...")
    mock_tool = AsyncMock(spec=RouteTool)
    mock_tool.execute.return_value = _make_failed_tool_result("Route service 500 error")

    agent = RouteAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert result.status == AgentStatus.FAILED
    assert result.confidence == 0.0
    assert len(result.errors) > 0
    combined = " ".join(result.errors) + (result.message or "")
    assert "Route service 500 error" in combined
    print(f"  [PASS] Tool failure -> FAILED | {_safe(result.message)}")


# ---------------------------------------------------------------------------
# TEST 6 - No routes returned -> PARTIAL with confidence=0.0
# ---------------------------------------------------------------------------

async def test_route_agent_no_routes():
    print("\n[TEST 6] RouteAgent - no routes returned -> PARTIAL, confidence=0.0...")
    mock_tool = AsyncMock(spec=RouteTool)
    mock_tool.execute.return_value = _make_route_no_routes_tool_result()

    agent = RouteAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert isinstance(result, AgentResult)
    assert result.status == AgentStatus.PARTIAL
    assert result.confidence == 0.0
    assert result.data is not None
    print(f"  [PASS] No routes -> PARTIAL, confidence=0.0 | {_safe(result.message)}")


# ---------------------------------------------------------------------------
# TEST 7 - Evidence preservation
# ---------------------------------------------------------------------------

async def test_route_agent_evidence_preserved():
    print("\n[TEST 7] RouteAgent - evidence propagated verbatim from ToolResult...")
    evidence = Evidence(
        source="ORCA Route Intelligence Engine (Multi-Source Feeds)",
        source_type="rule_engine",
        data_status=DataStatus.LIVE,
        reference="Open-Meteo & INCOIS WebGIS",
    )
    tool_result = ToolResult(
        tool="route_tool",
        status=AgentStatus.SUCCESS,
        data=_make_route_data(),
        evidence=evidence,
        errors=[],
        metadata={},
    )

    mock_tool = AsyncMock(spec=RouteTool)
    mock_tool.execute.return_value = tool_result

    agent = RouteAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert result.evidence is not None
    assert result.evidence.source == "ORCA Route Intelligence Engine (Multi-Source Feeds)"
    assert result.evidence.source_type == "rule_engine"
    assert result.evidence.data_status == DataStatus.LIVE
    assert result.evidence.reference == "Open-Meteo & INCOIS WebGIS"
    print(f"  [PASS] Evidence preserved: source={result.evidence.source}")


# ---------------------------------------------------------------------------
# TEST 8 - DataStatus.ERROR preserved on tool failure
# ---------------------------------------------------------------------------

async def test_route_agent_error_status_preserved():
    print("\n[TEST 8] RouteAgent - DataStatus.ERROR preserved on tool failure...")
    mock_tool = AsyncMock(spec=RouteTool)
    mock_tool.execute.return_value = _make_failed_tool_result()

    agent = RouteAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert result.evidence is not None
    assert result.evidence.data_status == DataStatus.ERROR
    print(f"  [PASS] DataStatus.ERROR preserved: {result.evidence.data_status}")


# ---------------------------------------------------------------------------
# TEST 9 - Context parameters passed through correctly
# ---------------------------------------------------------------------------

async def test_route_agent_context_parameters():
    print("\n[TEST 9] RouteAgent - context params (destination_name, time_window, override_zones)...")
    mock_tool = AsyncMock(spec=RouteTool)
    mock_tool.execute.return_value = _make_route_success_tool_result()

    agent = RouteAgent(tool=mock_tool)
    req = _make_request(
        context={
            "destination_name": "PFZ Zone Alpha",
            "time_window": "current",
            "override_zones": [{"id": "test_zone", "type": "exclusion"}],
        }
    )
    await agent.execute(req)

    mock_tool.execute.assert_called_once_with(
        origin_lat=15.4989,
        origin_lon=73.8278,
        destination_lat=15.2000,
        destination_lon=73.5000,
        destination_name="PFZ Zone Alpha",
        time_window="current",
        override_zones=[{"id": "test_zone", "type": "exclusion"}],
    )
    print("  [PASS] All context parameters correctly passed to RouteTool.execute.")


# ---------------------------------------------------------------------------
# TEST 10 - Default context parameters
# ---------------------------------------------------------------------------

async def test_route_agent_default_context():
    print("\n[TEST 10] RouteAgent - default context parameters used when context empty...")
    mock_tool = AsyncMock(spec=RouteTool)
    mock_tool.execute.return_value = _make_route_success_tool_result()

    agent = RouteAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    mock_tool.execute.assert_called_once_with(
        origin_lat=15.4989,
        origin_lon=73.8278,
        destination_lat=15.2000,
        destination_lon=73.5000,
        destination_name="Designated Target",
        time_window="tomorrow_morning",  # default
        override_zones=None,
    )
    print("  [PASS] Default context params correctly applied.")


# ---------------------------------------------------------------------------
# TEST 11 - timestamp field used as time_window fallback
# ---------------------------------------------------------------------------

async def test_route_agent_timestamp_fallback():
    print("\n[TEST 11] RouteAgent - request.timestamp used as time_window fallback...")
    mock_tool = AsyncMock(spec=RouteTool)
    mock_tool.execute.return_value = _make_route_success_tool_result()

    agent = RouteAgent(tool=mock_tool)
    req = AgentRequest(
        latitude=15.4989,
        longitude=73.8278,
        destination_latitude=15.2000,
        destination_longitude=73.5000,
        timestamp="tomorrow",  # Should be used when context['time_window'] is not set
    )
    await agent.execute(req)

    call_kwargs = mock_tool.execute.call_args[1]
    assert call_kwargs["time_window"] == "tomorrow"
    print("  [PASS] request.timestamp='tomorrow' used as time_window fallback.")


# ---------------------------------------------------------------------------
# TEST 12 - Confidence scoring (viable/total)
# ---------------------------------------------------------------------------

async def test_route_agent_confidence_scoring():
    print("\n[TEST 12] RouteAgent - confidence = viable_routes / total_routes...")
    # 2 VIABLE out of 3 -> confidence = 0.67
    routes = [
        {"id": "r1", "risk_score": 20, "overall_status": "VIABLE"},
        {"id": "r2", "risk_score": 45, "overall_status": "VIABLE"},
        {"id": "r3", "risk_score": 80, "overall_status": "NOT_VIABLE"},
    ]
    tool_result = ToolResult(
        tool="route_tool",
        status=AgentStatus.SUCCESS,
        data=_make_route_data(routes=routes, recommended_id="r1"),
        evidence=_make_route_evidence(),
        errors=[],
        metadata={},
    )

    mock_tool = AsyncMock(spec=RouteTool)
    mock_tool.execute.return_value = tool_result

    agent = RouteAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    # 2/3 viable -> 0.67
    assert result.confidence == round(2 / 3, 2)
    assert result.status == AgentStatus.SUCCESS
    print(f"  [PASS] 2/3 viable routes -> confidence={result.confidence}")


# ---------------------------------------------------------------------------
# TEST 13 - Live integration test
# ---------------------------------------------------------------------------

async def test_route_agent_live():
    print("\n[TEST 13] RouteAgent - live integration test (Goa -> offshore target)...")
    agent = RouteAgent()
    req = AgentRequest(
        latitude=15.4989,
        longitude=73.8278,
        destination_latitude=15.2000,
        destination_longitude=73.5000,
        context={"destination_name": "Test Target", "time_window": "tomorrow_morning"},
    )
    result = await agent.execute(req)

    assert isinstance(result, AgentResult)
    assert result.agent == "route_agent"
    assert result.status in (AgentStatus.SUCCESS, AgentStatus.PARTIAL)
    assert result.data is not None
    assert result.evidence is not None
    assert result.evidence.source_type == "rule_engine"
    print(f"  [PASS] Live route result: status={result.status}, routes={len(result.data.get('routes', []))}")
    print(f"         Confidence={result.confidence}, Message: {_safe(result.message)}")


# ---------------------------------------------------------------------------
# MAIN runner
# ---------------------------------------------------------------------------

async def main():
    print("=" * 65)
    print("ORCA PHASE 3 - ROUTE AGENT TEST SUITE")
    print("=" * 65)

    test_route_agent_inherits_base_agent()
    test_route_agent_dependency_injection()
    await test_route_agent_success()
    await test_route_agent_missing_destination()
    await test_route_agent_tool_failure()
    await test_route_agent_no_routes()
    await test_route_agent_evidence_preserved()
    await test_route_agent_error_status_preserved()
    await test_route_agent_context_parameters()
    await test_route_agent_default_context()
    await test_route_agent_timestamp_fallback()
    await test_route_agent_confidence_scoring()
    await test_route_agent_live()

    print("\n" + "=" * 65)
    print("ALL ROUTE AGENT TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
