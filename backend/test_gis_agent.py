"""
ORCA Phase 3 - GIS Agent Test Suite
Tests:
1. Agent inheritance and contract compliance
2. query_zones operation (coordinates required)
3. evaluate_route operation (route_coords from context)
4. UNAVAILABLE state preserved (never fabricated as SUCCESS)
5. LIVE state (with override_zones)
6. Tool failure propagation
7. Evidence preservation
8. DataStatus preservation (UNAVAILABLE and ERROR)
9. Missing route_coords error for evaluate_route
10. Tool invoked with correct operation and parameters
11. Live integration test (query_zones)
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
from agents.gis_agent import GISAgent
from tools.base_tool import ToolResult
from tools.gis_tool import GISTool


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_gis_evidence(data_status: DataStatus = DataStatus.UNAVAILABLE) -> Evidence:
    return Evidence(
        source="Official Government Gazette / INCOIS WFS",
        source_type="ogc_wfs",
        data_status=data_status,
        reference="https://www.incois.gov.in",
    )


def _make_rule_engine_evidence(data_status: DataStatus = DataStatus.LIVE) -> Evidence:
    return Evidence(
        source="ORCA Geofencing & Spatial Engine",
        source_type="rule_engine",
        data_status=data_status,
    )


def _make_zone_query_data(status: str = "UNAVAILABLE") -> dict:
    """Simulates get_active_geofences response."""
    return {
        "status": status,
        "total_zones_found": 0,
        "zones": [],
        "query_coords": {"lat": 15.4989, "lon": 73.8278},
        "radius_km": 250.0,
    }


def _make_route_eval_data() -> dict:
    """Simulates evaluate_route_geofences response."""
    return {
        "restriction_status": "CLEAR",
        "intersecting_zones": [],
        "evaluated_waypoints": 2,
    }


def _make_gis_query_tool_result(data_status: DataStatus = DataStatus.UNAVAILABLE) -> ToolResult:
    """Tool result for query_zones operation - honest UNAVAILABLE."""
    return ToolResult(
        tool="gis_tool",
        status=AgentStatus.SUCCESS,
        data=_make_zone_query_data("UNAVAILABLE"),
        evidence=_make_gis_evidence(data_status),
        errors=[],
        metadata={"operation": "query_zones", "status": "UNAVAILABLE", "total_zones": 0},
    )


def _make_gis_route_tool_result() -> ToolResult:
    """Tool result for evaluate_route operation."""
    return ToolResult(
        tool="gis_tool",
        status=AgentStatus.SUCCESS,
        data=_make_route_eval_data(),
        evidence=_make_rule_engine_evidence(DataStatus.LIVE),
        errors=[],
        metadata={"operation": "evaluate_route"},
    )


def _make_failed_tool_result(msg: str = "GIS tool operation failed") -> ToolResult:
    return ToolResult(
        tool="gis_tool",
        status=AgentStatus.FAILED,
        data=None,
        evidence=Evidence(
            source="ORCA Geofencing & Spatial Engine",
            source_type="rule_engine",
            data_status=DataStatus.ERROR,
        ),
        errors=[msg],
        metadata={},
    )


def _make_request(
    lat: float = 15.4989,
    lon: float = 73.8278,
    operation: str = "query_zones",
    route_coords=None,
    override_zones=None,
    radius_km: float = 250.0,
) -> AgentRequest:
    ctx = {"operation": operation}
    if route_coords is not None:
        ctx["route_coords"] = route_coords
    if override_zones is not None:
        ctx["override_zones"] = override_zones
    if radius_km != 250.0:
        ctx["radius_km"] = radius_km
    return AgentRequest(latitude=lat, longitude=lon, context=ctx)


# ---------------------------------------------------------------------------
# TEST 1 - Agent inheritance / contract
# ---------------------------------------------------------------------------

def test_gis_agent_inherits_base_agent():
    print("\n[TEST 1] GISAgent inherits BaseAgent and satisfies contract...")
    agent = GISAgent()
    assert isinstance(agent, BaseAgent)
    assert agent.name == "gis_agent"
    assert hasattr(agent, "execute")
    assert hasattr(agent, "create_error_result")
    assert hasattr(agent, "create_evidence")
    print("  [PASS] GISAgent correctly inherits BaseAgent.")


# ---------------------------------------------------------------------------
# TEST 2 - Dependency injection
# ---------------------------------------------------------------------------

def test_gis_agent_dependency_injection():
    print("\n[TEST 2] GISAgent dependency injection via constructor...")
    mock_tool = MagicMock(spec=GISTool)
    agent = GISAgent(tool=mock_tool)
    assert agent.tool is mock_tool
    print("  [PASS] Dependency injection correctly replaces default GISTool.")


# ---------------------------------------------------------------------------
# TEST 3 - query_zones with UNAVAILABLE (honest state preserved)
# ---------------------------------------------------------------------------

async def test_gis_agent_query_zones_unavailable():
    print("\n[TEST 3] GISAgent - query_zones returns PARTIAL/UNAVAILABLE (honest)...")
    mock_tool = AsyncMock(spec=GISTool)
    mock_tool.execute.return_value = _make_gis_query_tool_result(DataStatus.UNAVAILABLE)

    agent = GISAgent(tool=mock_tool)
    result = await agent.execute(_make_request(operation="query_zones"))

    assert isinstance(result, AgentResult)
    assert result.agent == "gis_agent"
    # UNAVAILABLE official data -> PARTIAL (not FAILED, not fabricated SUCCESS)
    assert result.status == AgentStatus.PARTIAL
    assert result.confidence == 0.5
    assert result.evidence is not None
    assert result.evidence.data_status == DataStatus.UNAVAILABLE
    assert result.data is not None
    print(f"  [PASS] UNAVAILABLE correctly -> PARTIAL | data_status={result.evidence.data_status}")


# ---------------------------------------------------------------------------
# TEST 4 - evaluate_route with LIVE data (override_zones provided)
# ---------------------------------------------------------------------------

async def test_gis_agent_evaluate_route_live():
    print("\n[TEST 4] GISAgent - evaluate_route with LIVE data (override zones)...")
    mock_tool = AsyncMock(spec=GISTool)
    mock_tool.execute.return_value = _make_gis_route_tool_result()

    route_coords = [[15.4989, 73.8278], [15.3000, 73.6000]]
    agent = GISAgent(tool=mock_tool)
    result = await agent.execute(_make_request(
        operation="evaluate_route",
        route_coords=route_coords,
    ))

    assert isinstance(result, AgentResult)
    assert result.status == AgentStatus.SUCCESS
    assert result.confidence == 1.0
    assert result.data is not None
    assert "restriction_status" in result.data
    assert result.evidence.data_status == DataStatus.LIVE
    print(f"  [PASS] Route eval with LIVE data: restriction_status={result.data.get('restriction_status')}")


# ---------------------------------------------------------------------------
# TEST 5 - evaluate_route with missing route_coords -> FAILED
# ---------------------------------------------------------------------------

async def test_gis_agent_evaluate_route_missing_coords():
    print("\n[TEST 5] GISAgent - evaluate_route missing route_coords -> FAILED...")
    mock_tool = AsyncMock(spec=GISTool)
    # Tool should not be called in this case
    mock_tool.execute.return_value = _make_failed_tool_result()

    agent = GISAgent(tool=mock_tool)
    # evaluate_route without route_coords in context
    req = AgentRequest(latitude=15.4989, longitude=73.8278, context={"operation": "evaluate_route"})
    result = await agent.execute(req)

    assert result.status == AgentStatus.FAILED
    assert result.confidence == 0.0
    assert len(result.errors) > 0
    # Tool should NOT have been called - error is caught before tool call
    mock_tool.execute.assert_not_called()
    print(f"  [PASS] Missing route_coords -> FAILED before tool call | {result.message}")


# ---------------------------------------------------------------------------
# TEST 6 - Tool failure propagation
# ---------------------------------------------------------------------------

async def test_gis_agent_tool_failure():
    print("\n[TEST 6] GISAgent - tool failure propagated as FAILED AgentResult...")
    mock_tool = AsyncMock(spec=GISTool)
    mock_tool.execute.return_value = _make_failed_tool_result("Geofence service crashed")

    agent = GISAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert result.status == AgentStatus.FAILED
    assert result.confidence == 0.0
    assert len(result.errors) > 0
    combined = " ".join(result.errors) + (result.message or "")
    assert "Geofence service crashed" in combined
    print(f"  [PASS] Tool failure -> FAILED | {result.message}")


# ---------------------------------------------------------------------------
# TEST 7 - Evidence preservation (query_zones)
# ---------------------------------------------------------------------------

async def test_gis_agent_evidence_preserved():
    print("\n[TEST 7] GISAgent - evidence preserved verbatim from ToolResult...")
    evidence = Evidence(
        source="Official Government Gazette / INCOIS WFS",
        source_type="ogc_wfs",
        data_status=DataStatus.UNAVAILABLE,
        reference="https://www.incois.gov.in",
    )
    tool_result = ToolResult(
        tool="gis_tool",
        status=AgentStatus.SUCCESS,
        data=_make_zone_query_data(),
        evidence=evidence,
        errors=[],
        metadata={},
    )

    mock_tool = AsyncMock(spec=GISTool)
    mock_tool.execute.return_value = tool_result

    agent = GISAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert result.evidence is not None
    assert result.evidence.source == "Official Government Gazette / INCOIS WFS"
    assert result.evidence.source_type == "ogc_wfs"
    assert result.evidence.data_status == DataStatus.UNAVAILABLE
    assert result.evidence.reference == "https://www.incois.gov.in"
    print(f"  [PASS] Evidence preserved: source={result.evidence.source}")


# ---------------------------------------------------------------------------
# TEST 8 - DataStatus.ERROR preserved on failure
# ---------------------------------------------------------------------------

async def test_gis_agent_error_status_preserved():
    print("\n[TEST 8] GISAgent - DataStatus.ERROR preserved on tool failure...")
    mock_tool = AsyncMock(spec=GISTool)
    mock_tool.execute.return_value = _make_failed_tool_result()

    agent = GISAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert result.evidence is not None
    assert result.evidence.data_status == DataStatus.ERROR
    print(f"  [PASS] DataStatus.ERROR preserved: {result.evidence.data_status}")


# ---------------------------------------------------------------------------
# TEST 9 - Tool invoked with correct operation parameters
# ---------------------------------------------------------------------------

async def test_gis_agent_tool_invocation_query_zones():
    print("\n[TEST 9] GISAgent - tool.execute called with correct query_zones params...")
    mock_tool = AsyncMock(spec=GISTool)
    mock_tool.execute.return_value = _make_gis_query_tool_result()

    agent = GISAgent(tool=mock_tool)
    req = AgentRequest(latitude=9.9312, longitude=76.2673, context={"operation": "query_zones", "radius_km": 100.0})
    await agent.execute(req)

    mock_tool.execute.assert_called_once_with(
        lat=9.9312,
        lon=76.2673,
        radius_km=100.0,
        route_coords=None,
        override_zones=None,
        operation="query_zones",
    )
    print("  [PASS] GISTool.execute called with correct query_zones parameters.")


# ---------------------------------------------------------------------------
# TEST 10 - Tool invoked with route_coords for evaluate_route
# ---------------------------------------------------------------------------

async def test_gis_agent_tool_invocation_evaluate_route():
    print("\n[TEST 10] GISAgent - tool.execute called with route_coords for evaluate_route...")
    mock_tool = AsyncMock(spec=GISTool)
    mock_tool.execute.return_value = _make_gis_route_tool_result()

    agent = GISAgent(tool=mock_tool)
    route_coords = [[15.4989, 73.8278], [15.3000, 73.6000]]
    req = AgentRequest(
        latitude=15.4989,
        longitude=73.8278,
        context={"operation": "evaluate_route", "route_coords": route_coords},
    )
    await agent.execute(req)

    mock_tool.execute.assert_called_once_with(
        lat=15.4989,
        lon=73.8278,
        radius_km=250.0,
        route_coords=route_coords,
        override_zones=None,
        operation="evaluate_route",
    )
    print("  [PASS] GISTool.execute called with correct evaluate_route parameters.")


# ---------------------------------------------------------------------------
# TEST 11 - Live integration test (query_zones)
# ---------------------------------------------------------------------------

async def test_gis_agent_live():
    print("\n[TEST 11] GISAgent - live integration test (Goa, query_zones)...")
    agent = GISAgent()
    req = AgentRequest(latitude=15.4989, longitude=73.8278)
    result = await agent.execute(req)

    assert isinstance(result, AgentResult)
    assert result.agent == "gis_agent"
    # Production geofences are UNAVAILABLE -> PARTIAL (honest)
    assert result.status in (AgentStatus.SUCCESS, AgentStatus.PARTIAL)
    assert result.evidence is not None
    # Real upstream will be UNAVAILABLE - do not fabricate
    assert result.evidence.data_status in (DataStatus.UNAVAILABLE, DataStatus.LIVE, DataStatus.ERROR)
    print(f"  [PASS] Live GIS result: status={result.status}, data_status={result.evidence.data_status}")
    print(f"         Message: {result.message}")


# ---------------------------------------------------------------------------
# TEST 12 - UNAVAILABLE state is NOT collapsed to SUCCESS (critical rule)
# ---------------------------------------------------------------------------

async def test_gis_agent_unavailable_not_fabricated_as_success():
    print("\n[TEST 12] GISAgent - UNAVAILABLE data must NOT be fabricated as SUCCESS...")
    mock_tool = AsyncMock(spec=GISTool)
    mock_tool.execute.return_value = _make_gis_query_tool_result(DataStatus.UNAVAILABLE)

    agent = GISAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    # Absolute rule: UNAVAILABLE -> must NOT be AgentStatus.SUCCESS
    assert result.status != AgentStatus.SUCCESS, (
        "CRITICAL: GISAgent must NOT collapse UNAVAILABLE data_status into AgentStatus.SUCCESS!"
    )
    print(f"  [PASS] UNAVAILABLE correctly NOT collapsed to SUCCESS -> {result.status}")


# ---------------------------------------------------------------------------
# MAIN runner
# ---------------------------------------------------------------------------

async def main():
    print("=" * 65)
    print("ORCA PHASE 3 - GIS AGENT TEST SUITE")
    print("=" * 65)

    test_gis_agent_inherits_base_agent()
    test_gis_agent_dependency_injection()
    await test_gis_agent_query_zones_unavailable()
    await test_gis_agent_evaluate_route_live()
    await test_gis_agent_evaluate_route_missing_coords()
    await test_gis_agent_tool_failure()
    await test_gis_agent_evidence_preserved()
    await test_gis_agent_error_status_preserved()
    await test_gis_agent_tool_invocation_query_zones()
    await test_gis_agent_tool_invocation_evaluate_route()
    await test_gis_agent_live()
    await test_gis_agent_unavailable_not_fabricated_as_success()

    print("\n" + "=" * 65)
    print("ALL GIS AGENT TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
