"""
Verification Suite for ORCA Phase 3.5: Chlorophyll Tool
Tests:
1. BaseTool contract & ToolResult schema verification
2. Successful response if source is available (mock)
3. Transparent UNAVAILABLE response when not connected
4. Service exception / connection error handling
5. Evidence propagation (source, source_type, reference)
6. DataStatus preservation (LIVE, UNAVAILABLE, CACHED, STALE, ERROR)
7. Non-fabrication guarantee (no fake numbers when unavailable)
8. Live integration execution
"""

import asyncio
from unittest.mock import patch

from core.schemas import AgentStatus, DataStatus, Evidence
from tools.base_tool import BaseTool, ToolResult
from tools.chlorophyll_tool import ChlorophyllTool


def test_tool_contract():
    print("\n[TEST 1] ChlorophyllTool Contract & Inheritance Verification...")
    tool = ChlorophyllTool()
    assert isinstance(tool, BaseTool)
    assert tool.name == "chlorophyll_tool"
    assert hasattr(tool, "execute")
    assert hasattr(tool, "create_evidence")
    assert hasattr(tool, "create_error_result")
    print("  [PASS] ChlorophyllTool satisfies BaseTool contract.")


async def test_tool_success_when_available():
    print("\n[TEST 2] Successful response when satellite data source is available...")
    tool = ChlorophyllTool()

    mock_service_data = {
        "available": True,
        "value": 0.42,
        "unit": "mg/m³",
        "source": "NASA Ocean Color / MODIS-Aqua Level-3 Mapped",
        "provider": "NASA Earthdata Cloud / OB.DAAC",
        "status": "authenticated_granule_located",
        "granule": "AQUA_MODIS.20260929.L3m.DAY.CHL.chlor_a.4km.nc",
        "timestamp": "2026-09-29T10:00:00Z",
        "coordinates": {"latitude": 15.4989, "longitude": 73.8278},
        "message": "NASA Earthdata authenticated. Granule located.",
    }

    with patch("tools.chlorophyll_tool.get_chlorophyll_data", return_value=mock_service_data):
        res = await tool.execute(lat=15.4989, lon=73.8278)

    assert isinstance(res, ToolResult)
    assert res.tool == "chlorophyll_tool"
    assert res.status == AgentStatus.SUCCESS
    assert res.data["available"] is True
    assert res.data["value"] == 0.42
    assert res.evidence is not None
    assert res.evidence.data_status == DataStatus.LIVE
    assert res.evidence.source_type == "satellite"
    assert res.evidence.observed_at == "2026-09-29T10:00:00Z"
    assert len(res.errors) == 0
    print("  [PASS] Successful response correctly mapped with DataStatus.LIVE.")


async def test_tool_unavailable_response():
    print("\n[TEST 3] Honest UNAVAILABLE response when not connected...")
    tool = ChlorophyllTool()

    mock_unavail_data = {
        "available": False,
        "value": None,
        "unit": "mg/m³",
        "source": "NASA Ocean Color / MODIS-Aqua",
        "provider": "NASA Earthdata / OB.DAAC",
        "status": "not_connected",
        "message": "Chlorophyll-a satellite data source is not connected.",
        "coordinates": {"latitude": 15.4989, "longitude": 73.8278},
    }

    with patch("tools.chlorophyll_tool.get_chlorophyll_data", return_value=mock_unavail_data):
        res = await tool.execute(lat=15.4989, lon=73.8278)

    assert isinstance(res, ToolResult)
    assert res.tool == "chlorophyll_tool"
    assert res.status == AgentStatus.PARTIAL
    assert res.data["available"] is False
    assert res.data["value"] is None
    assert res.evidence is not None
    assert res.evidence.data_status == DataStatus.UNAVAILABLE
    assert res.evidence.source_type == "satellite"
    print("  [PASS] Unavailable response correctly returns AgentStatus.PARTIAL and DataStatus.UNAVAILABLE.")


async def test_tool_service_error():
    print("\n[TEST 4] Service exception handling -> AgentStatus.FAILED & DataStatus.ERROR...")
    tool = ChlorophyllTool()

    with patch("tools.chlorophyll_tool.get_chlorophyll_data", side_effect=RuntimeError("NASA Earthdata API timeout")):
        res = await tool.execute(lat=15.4989, lon=73.8278)

    assert isinstance(res, ToolResult)
    assert res.status == AgentStatus.FAILED
    assert res.data is None
    assert len(res.errors) > 0
    assert "NASA Earthdata API timeout" in res.errors[0]
    assert res.evidence is not None
    assert res.evidence.data_status == DataStatus.ERROR
    print("  [PASS] Service error caught gracefully and returned as FAILED/ERROR.")


async def test_tool_evidence_propagation():
    print("\n[TEST 5] Evidence propagation verification...")
    tool = ChlorophyllTool()

    mock_service_data = {
        "available": True,
        "value": 0.18,
        "unit": "mg/m³",
        "source": "INCOIS Ocean Color / Indian Marine Remote Sensing",
        "provider": "INCOIS / MoES",
        "status": "active_advisory",
        "timestamp": "2026-09-29T12:00:00Z",
    }

    with patch("tools.chlorophyll_tool.get_chlorophyll_data", return_value=mock_service_data):
        res = await tool.execute(lat=12.0, lon=80.0)

    assert res.evidence.source == "INCOIS Ocean Color / Indian Marine Remote Sensing"
    assert res.evidence.source_type == "satellite"
    assert res.evidence.observed_at == "2026-09-29T12:00:00Z"
    assert res.evidence.reference == "https://oceancolor.gsfc.nasa.gov"
    assert res.evidence.retrieved_at is not None
    print("  [PASS] Evidence fields accurately propagated from source.")


async def test_tool_datastatus_preservation():
    print("\n[TEST 6] DataStatus preservation across CACHED, STALE, and UNAVAILABLE...")
    tool = ChlorophyllTool()

    for ds in [DataStatus.CACHED, DataStatus.STALE, DataStatus.UNAVAILABLE]:
        mock_data = {
            "available": ds != DataStatus.UNAVAILABLE,
            "data_status": ds.value,
            "value": 0.25 if ds != DataStatus.UNAVAILABLE else None,
            "source": "NASA Ocean Color",
        }
        with patch("tools.chlorophyll_tool.get_chlorophyll_data", return_value=mock_data):
            res = await tool.execute(lat=15.0, lon=73.0)
            assert res.evidence.data_status == ds, f"Expected {ds}, got {res.evidence.data_status}"

    print("  [PASS] DataStatus strictly preserved without converting STALE or CACHED to LIVE.")


async def test_tool_non_fabrication():
    print("\n[TEST 7] Critical non-fabrication check...")
    tool = ChlorophyllTool()

    # Default unconfigured service response
    mock_data = {
        "available": False,
        "value": None,
        "unit": "mg/m³",
        "status": "not_connected",
    }
    with patch("tools.chlorophyll_tool.get_chlorophyll_data", return_value=mock_data):
        res = await tool.execute(lat=18.9, lon=72.8)

    assert res.data["value"] is None
    assert res.data["available"] is False
    assert res.evidence.data_status == DataStatus.UNAVAILABLE
    print("  [PASS] Zero data fabrication confirmed for unavailable chlorophyll telemetry.")


async def test_tool_live_integration():
    print("\n[TEST 8] Live integration test with real chlorophyll_service...")
    tool = ChlorophyllTool()
    res = await tool.execute(lat=15.4989, lon=73.8278)

    assert isinstance(res, ToolResult)
    assert res.tool == "chlorophyll_tool"
    assert res.evidence is not None
    print(f"  Live execution status: {res.status.value}")
    print(f"  DataStatus: {res.evidence.data_status.value}")
    print(f"  Source: {res.evidence.source}")
    print(f"  Available: {res.data.get('available')}")
    print(f"  Value: {res.data.get('value')}")
    print(f"  Message: {res.data.get('message')}")
    print("  [PASS] Live chlorophyll tool execution succeeded.")


async def main():
    print("=" * 60)
    print("ORCA PHASE 3.5 — CHLOROPHYLL TOOL VERIFICATION SUITE")
    print("=" * 60)

    test_tool_contract()
    await test_tool_success_when_available()
    await test_tool_unavailable_response()
    await test_tool_service_error()
    await test_tool_evidence_propagation()
    await test_tool_datastatus_preservation()
    await test_tool_non_fabrication()
    await test_tool_live_integration()

    print("\n" + "=" * 60)
    print("ALL CHLOROPHYLL TOOL TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
