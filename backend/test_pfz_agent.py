"""
ORCA Phase 3 - PFZ Agent Test Suite
Tests:
1. Agent inheritance and contract compliance
2. Successful PFZ execution with advisory data
3. PARTIAL state (PFZ unavailable / not found in radius)
4. Tool failure propagation -> FAILED AgentResult
5. Evidence propagation (INCOIS provenance preserved verbatim)
6. DataStatus preservation: LIVE, UNAVAILABLE, ERROR
7. Provenance preservation: source, source_type, reference, observed_at
8. radius_km passed through request.context
9. Tool is invoked with correct coordinates and radius
10. Live integration test
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
from agents.pfz_agent import PFZAgent
from tools.base_tool import ToolResult
from tools.pfz_tool import PFZTool


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_incois_evidence(data_status: DataStatus = DataStatus.LIVE, observed_at: str = "2026-09-29") -> Evidence:
    return Evidence(
        source="INCOIS WebGIS GeoServer WFS",
        source_type="ogc_wfs",
        observed_at=observed_at,
        data_status=data_status,
        reference="https://www.incois.gov.in/geoserver/PFZ_Automation/ows",
    )


def _make_pfz_available_data() -> dict:
    """Simulates INCOIS PFZ data with active advisories."""
    return {
        "available": True,
        "total_active_advisories_found": 3,
        "advisory_metadata": {
            "reference_layer_date": "2026-09-29",
            "source": "INCOIS",
        },
        "nearest_advisory": {
            "landing_center": "Mangaluru Fishing Harbour",
            "distance_from_query_km": 47.3,
            "depth_range_m": "30-80",
        },
        "advisories": [
            {"landing_center": "Mangaluru Fishing Harbour", "distance_from_query_km": 47.3},
        ],
    }


def _make_pfz_unavailable_data() -> dict:
    """Simulates INCOIS PFZ response when no advisories found."""
    return {
        "available": False,
        "total_active_advisories_found": 0,
        "advisory_metadata": {
            "reference_layer_date": None,
            "source": "INCOIS",
        },
        "nearest_advisory": None,
        "advisories": [],
    }


def _make_pfz_success_tool_result() -> ToolResult:
    return ToolResult(
        tool="pfz_tool",
        status=AgentStatus.SUCCESS,
        data=_make_pfz_available_data(),
        evidence=_make_incois_evidence(DataStatus.LIVE, "2026-09-29"),
        errors=[],
        metadata={"source": "INCOIS", "total_advisories": 3, "total_regional_lines": 5, "total_nationwide_lines": 20},
    )


def _make_pfz_partial_tool_result() -> ToolResult:
    """Tool returns PARTIAL when PFZ data is unavailable for the location."""
    return ToolResult(
        tool="pfz_tool",
        status=AgentStatus.PARTIAL,
        data=_make_pfz_unavailable_data(),
        evidence=_make_incois_evidence(DataStatus.UNAVAILABLE, None),
        errors=[],
        metadata={"source": "INCOIS", "total_advisories": 0, "total_regional_lines": 0, "total_nationwide_lines": 0},
    )


def _make_pfz_failed_tool_result(msg: str = "PFZ service call failed: connection refused") -> ToolResult:
    return ToolResult(
        tool="pfz_tool",
        status=AgentStatus.FAILED,
        data=None,
        evidence=Evidence(
            source="INCOIS WebGIS GeoServer WFS",
            source_type="ogc_wfs",
            data_status=DataStatus.ERROR,
            reference="https://www.incois.gov.in",
        ),
        errors=[msg],
        metadata={},
    )


def _make_request(lat: float = 15.4989, lon: float = 73.8278, radius_km: float = 250.0) -> AgentRequest:
    ctx = {"radius_km": radius_km} if radius_km != 250.0 else {}
    return AgentRequest(latitude=lat, longitude=lon, context=ctx)


# ---------------------------------------------------------------------------
# TEST 1 - Agent inheritance / contract
# ---------------------------------------------------------------------------

def test_pfz_agent_inherits_base_agent():
    print("\n[TEST 1] PFZAgent inherits BaseAgent and satisfies contract...")
    agent = PFZAgent()
    assert isinstance(agent, BaseAgent)
    assert agent.name == "pfz_agent"
    assert hasattr(agent, "execute")
    assert hasattr(agent, "create_error_result")
    assert hasattr(agent, "create_evidence")
    print("  [PASS] PFZAgent correctly inherits BaseAgent.")


# ---------------------------------------------------------------------------
# TEST 2 - Dependency injection
# ---------------------------------------------------------------------------

def test_pfz_agent_dependency_injection():
    print("\n[TEST 2] PFZAgent dependency injection via constructor...")
    mock_tool = MagicMock(spec=PFZTool)
    agent = PFZAgent(tool=mock_tool)
    assert agent.tool is mock_tool
    print("  [PASS] Dependency injection correctly replaces default PFZTool.")


# ---------------------------------------------------------------------------
# TEST 3 - Successful PFZ request (advisories found)
# ---------------------------------------------------------------------------

async def test_pfz_agent_success():
    print("\n[TEST 3] PFZAgent - successful PFZ request with active advisories...")
    mock_tool = AsyncMock(spec=PFZTool)
    mock_tool.execute.return_value = _make_pfz_success_tool_result()

    agent = PFZAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert isinstance(result, AgentResult)
    assert result.agent == "pfz_agent"
    assert result.status == AgentStatus.SUCCESS
    assert result.confidence == 1.0
    assert result.data is not None
    assert result.data.get("available") is True
    assert result.data.get("total_active_advisories_found") == 3
    assert result.errors == []
    assert result.message is not None
    print(f"  [PASS] PFZ SUCCESS: {result.message}")


# ---------------------------------------------------------------------------
# TEST 4 - PARTIAL state (PFZ unavailable / not found in radius)
# ---------------------------------------------------------------------------

async def test_pfz_agent_unavailable():
    print("\n[TEST 4] PFZAgent - PARTIAL when PFZ data unavailable...")
    mock_tool = AsyncMock(spec=PFZTool)
    mock_tool.execute.return_value = _make_pfz_partial_tool_result()

    agent = PFZAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert isinstance(result, AgentResult)
    assert result.agent == "pfz_agent"
    # PARTIAL tool result -> PARTIAL agent result (not FAILED - unavailable is honest)
    assert result.status == AgentStatus.PARTIAL
    assert result.confidence == 0.5  # Honest partial confidence
    assert result.data is not None
    assert result.data.get("available") is False
    print(f"  [PASS] PFZ PARTIAL (unavailable): status={result.status}, confidence={result.confidence}")


# ---------------------------------------------------------------------------
# TEST 5 - Tool failure propagation
# ---------------------------------------------------------------------------

async def test_pfz_agent_tool_failure():
    print("\n[TEST 5] PFZAgent - tool failure propagated as FAILED AgentResult...")
    mock_tool = AsyncMock(spec=PFZTool)
    mock_tool.execute.return_value = _make_pfz_failed_tool_result("INCOIS GeoServer unreachable")

    agent = PFZAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert result.status == AgentStatus.FAILED
    assert result.confidence == 0.0
    assert len(result.errors) > 0
    combined = " ".join(result.errors) + (result.message or "")
    assert "INCOIS GeoServer unreachable" in combined
    print(f"  [PASS] Tool failure -> FAILED | {result.message}")


# ---------------------------------------------------------------------------
# TEST 6 - Evidence / INCOIS provenance preserved verbatim
# ---------------------------------------------------------------------------

async def test_pfz_agent_evidence_preserved():
    print("\n[TEST 6] PFZAgent - INCOIS provenance preserved verbatim...")
    mock_tool = AsyncMock(spec=PFZTool)
    mock_tool.execute.return_value = _make_pfz_success_tool_result()

    agent = PFZAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert result.evidence is not None
    assert result.evidence.source == "INCOIS WebGIS GeoServer WFS"
    assert result.evidence.source_type == "ogc_wfs"
    assert result.evidence.data_status == DataStatus.LIVE
    assert result.evidence.reference == "https://www.incois.gov.in/geoserver/PFZ_Automation/ows"
    assert result.evidence.observed_at == "2026-09-29"
    print(f"  [PASS] INCOIS provenance preserved: source={result.evidence.source}, ref={result.evidence.reference}")


# ---------------------------------------------------------------------------
# TEST 7 - DataStatus.UNAVAILABLE preserved on PARTIAL result
# ---------------------------------------------------------------------------

async def test_pfz_agent_unavailable_data_status_preserved():
    print("\n[TEST 7] PFZAgent - DataStatus.UNAVAILABLE preserved on PARTIAL result...")
    mock_tool = AsyncMock(spec=PFZTool)
    mock_tool.execute.return_value = _make_pfz_partial_tool_result()

    agent = PFZAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert result.evidence is not None
    assert result.evidence.data_status == DataStatus.UNAVAILABLE
    print(f"  [PASS] DataStatus.UNAVAILABLE correctly preserved: {result.evidence.data_status}")


# ---------------------------------------------------------------------------
# TEST 8 - DataStatus.ERROR preserved on tool failure
# ---------------------------------------------------------------------------

async def test_pfz_agent_error_data_status_preserved():
    print("\n[TEST 8] PFZAgent - DataStatus.ERROR preserved on tool failure...")
    mock_tool = AsyncMock(spec=PFZTool)
    mock_tool.execute.return_value = _make_pfz_failed_tool_result()

    agent = PFZAgent(tool=mock_tool)
    result = await agent.execute(_make_request())

    assert result.evidence is not None
    assert result.evidence.data_status == DataStatus.ERROR
    print(f"  [PASS] DataStatus.ERROR preserved: {result.evidence.data_status}")


# ---------------------------------------------------------------------------
# TEST 9 - radius_km from request.context passed through
# ---------------------------------------------------------------------------

async def test_pfz_agent_radius_from_context():
    print("\n[TEST 9] PFZAgent - radius_km from context passed to tool...")
    mock_tool = AsyncMock(spec=PFZTool)
    mock_tool.execute.return_value = _make_pfz_success_tool_result()

    agent = PFZAgent(tool=mock_tool)
    req = AgentRequest(latitude=15.4989, longitude=73.8278, context={"radius_km": 400.0})
    await agent.execute(req)

    mock_tool.execute.assert_called_once_with(lat=15.4989, lon=73.8278, radius_km=400.0)
    print("  [PASS] radius_km=400.0 correctly passed to PFZTool.execute.")


# ---------------------------------------------------------------------------
# TEST 10 - Tool invoked with correct default radius
# ---------------------------------------------------------------------------

async def test_pfz_agent_default_radius():
    print("\n[TEST 10] PFZAgent - default radius_km=250.0 used when context is empty...")
    mock_tool = AsyncMock(spec=PFZTool)
    mock_tool.execute.return_value = _make_pfz_success_tool_result()

    agent = PFZAgent(tool=mock_tool)
    req = AgentRequest(latitude=15.4989, longitude=73.8278)
    await agent.execute(req)

    mock_tool.execute.assert_called_once_with(lat=15.4989, lon=73.8278, radius_km=250.0)
    print("  [PASS] Default radius_km=250.0 correctly used.")


# ---------------------------------------------------------------------------
# TEST 11 - Live integration test (real INCOIS WFS)
# ---------------------------------------------------------------------------

async def test_pfz_agent_live():
    print("\n[TEST 11] PFZAgent - live integration test (Goa, India)...")
    agent = PFZAgent()
    req = AgentRequest(latitude=15.4989, longitude=73.8278)
    result = await agent.execute(req)

    assert isinstance(result, AgentResult)
    assert result.agent == "pfz_agent"
    assert result.status in (AgentStatus.SUCCESS, AgentStatus.PARTIAL)
    assert result.evidence is not None
    assert result.evidence.source == "INCOIS WebGIS GeoServer WFS"
    assert result.evidence.source_type == "ogc_wfs"
    # Evidence must NOT fabricate or overstate data availability
    assert result.evidence.data_status in (DataStatus.LIVE, DataStatus.UNAVAILABLE)
    print(f"  [PASS] Live PFZ result: status={result.status}, data_status={result.evidence.data_status}")
    print(f"         Message: {result.message}")


# ---------------------------------------------------------------------------
# MAIN runner
# ---------------------------------------------------------------------------

async def main():
    print("=" * 65)
    print("ORCA PHASE 3 - PFZ AGENT TEST SUITE")
    print("=" * 65)

    test_pfz_agent_inherits_base_agent()
    test_pfz_agent_dependency_injection()
    await test_pfz_agent_success()
    await test_pfz_agent_unavailable()
    await test_pfz_agent_tool_failure()
    await test_pfz_agent_evidence_preserved()
    await test_pfz_agent_unavailable_data_status_preserved()
    await test_pfz_agent_error_data_status_preserved()
    await test_pfz_agent_radius_from_context()
    await test_pfz_agent_default_radius()
    await test_pfz_agent_live()

    print("\n" + "=" * 65)
    print("ALL PFZ AGENT TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
