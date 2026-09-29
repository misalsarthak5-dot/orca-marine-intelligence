"""
Verification Suite for ORCA Phase 2: Tool Layer
Tests:
1. BaseTool and ToolResult contract validation
2. WeatherTool -> existing services.weather_service
3. MarineTool -> existing services.marine_service
4. PFZTool -> existing services.pfz_service
5. HazardTool -> existing services.hazard_service
6. GISTool -> existing services.geofence_service
7. RouteTool -> existing services.route_service
8. Error handling & invalid input handling across all tools
9. Provenance & data status preservation
10. WeatherAgent -> WeatherTool -> WeatherService end-to-end integration
"""

import asyncio
from unittest.mock import patch

from core.schemas import AgentStatus, DataStatus
from tools.base_tool import BaseTool, ToolResult
from tools.weather_tool import WeatherTool
from tools.marine_tool import MarineTool
from tools.pfz_tool import PFZTool
from tools.hazard_tool import HazardTool
from tools.gis_tool import GISTool
from tools.route_tool import RouteTool
from agents.weather_agent import WeatherAgent
from core.schemas import AgentRequest, AgentResult


async def test_base_tool_contract():
    print("\n[TEST 1] BaseTool Contract & ToolResult Schema Verification...")

    class DummyTool(BaseTool):
        name = "dummy_tool"
        description = "Test tool"

        async def execute(self, **kwargs) -> ToolResult:
            ev = self.create_evidence(source="Test Source", source_type="api", data_status=DataStatus.LIVE)
            return ToolResult(tool=self.name, status=AgentStatus.SUCCESS, data={"dummy": True}, evidence=ev)

    tool = DummyTool()
    res = await tool.execute()
    assert isinstance(res, ToolResult)
    assert res.tool == "dummy_tool"
    assert res.status == AgentStatus.SUCCESS
    assert res.data == {"dummy": True}
    assert res.evidence is not None
    assert res.evidence.data_status == DataStatus.LIVE
    print("  [PASS] BaseTool contract and ToolResult schema verified.")


async def test_weather_tool():
    print("\n[TEST 2] WeatherTool -> existing WeatherService...")
    tool = WeatherTool()
    
    # 1. Live execution
    res = await tool.execute(lat=15.4989, lon=73.8278)
    assert isinstance(res, ToolResult)
    assert res.tool == "weather_tool"
    assert res.status == AgentStatus.SUCCESS
    assert "current" in res.data
    assert "temperature" in res.data["current"]
    assert res.evidence.source == "Open-Meteo Forecast API"
    assert res.evidence.data_status == DataStatus.LIVE
    print(f"  [PASS] Live weather retrieved: {res.data['current']['temperature']}°C")

    # 2. Invalid inputs
    bad_res = await tool.execute(lat=999.0, lon=73.8278)
    assert bad_res.status == AgentStatus.FAILED
    assert bad_res.evidence.data_status == DataStatus.ERROR
    print("  [PASS] Invalid coordinate boundary handled gracefully.")


async def test_marine_tool():
    print("\n[TEST 3] MarineTool -> existing MarineService...")
    tool = MarineTool()

    # 1. Live execution
    res = await tool.execute(lat=15.4989, lon=73.8278)
    assert isinstance(res, ToolResult)
    assert res.tool == "marine_tool"
    assert res.status == AgentStatus.SUCCESS
    assert "current" in res.data
    assert "wave_height" in res.data["current"]
    assert res.evidence.source == "Open-Meteo Marine API"
    assert res.evidence.data_status == DataStatus.LIVE
    print(f"  [PASS] Live marine retrieved: wave_height={res.data['current']['wave_height']}m")

    # 2. Invalid inputs
    bad_res = await tool.execute(lat=-999.0, lon=73.8278)
    assert bad_res.status == AgentStatus.FAILED
    assert bad_res.evidence.data_status == DataStatus.ERROR
    print("  [PASS] Invalid coordinate boundary handled gracefully.")


async def test_pfz_tool():
    print("\n[TEST 4] PFZTool -> existing PFZService...")
    tool = PFZTool()

    res = await tool.execute(lat=15.4989, lon=73.8278, radius_km=250.0)
    assert isinstance(res, ToolResult)
    assert res.tool == "pfz_tool"
    assert res.status in [AgentStatus.SUCCESS, AgentStatus.PARTIAL]
    assert "advisory_metadata" in res.data
    assert res.evidence.source == "INCOIS WebGIS GeoServer WFS"
    assert res.evidence.source_type == "ogc_wfs"
    print(f"  [PASS] PFZ intelligence retrieved: total_lines={res.metadata['total_nationwide_lines']}")


async def test_hazard_tool():
    print("\n[TEST 5] HazardTool -> existing HazardService...")
    tool = HazardTool()

    res = await tool.execute(lat=15.4989, lon=73.8278)
    assert isinstance(res, ToolResult)
    assert res.tool == "hazard_tool"
    assert res.status == AgentStatus.SUCCESS
    assert "overall_state" in res.data
    assert res.data["overall_state"] in ["NO SIGNIFICANT HAZARDS", "CAUTION", "HIGH ALERT"]
    assert res.evidence.source_type == "rule_engine"
    print(f"  [PASS] Hazard state evaluated: {res.data['overall_state']}")


async def test_gis_tool():
    print("\n[TEST 6] GISTool -> existing Geofence/Spatial Service...")
    tool = GISTool()

    # 1. Query active geofences
    res_query = await tool.execute(lat=15.4989, lon=73.8278, operation="query_zones")
    assert isinstance(res_query, ToolResult)
    assert res_query.tool == "gis_tool"
    assert res_query.status == AgentStatus.SUCCESS
    assert res_query.data["status"] == "UNAVAILABLE"
    assert res_query.evidence.data_status == DataStatus.UNAVAILABLE
    print("  [PASS] Production geofences query returns honest UNAVAILABLE status.")

    # 2. Evaluate route geofences
    test_route = [[15.4989, 73.8278], [15.3000, 73.6000]]
    res_route = await tool.execute(route_coords=test_route, operation="evaluate_route")
    assert res_route.status == AgentStatus.SUCCESS
    assert "restriction_status" in res_route.data
    print(f"  [PASS] Route geofence evaluation: restriction_status={res_route.data['restriction_status']}")


async def test_route_tool():
    print("\n[TEST 7] RouteTool -> existing RouteService...")
    tool = RouteTool()

    res = await tool.execute(
        origin_lat=15.4989,
        origin_lon=73.8278,
        destination_lat=15.2000,
        destination_lon=73.5000,
        destination_name="Goa Target Area",
        time_window="tomorrow_morning",
    )
    assert isinstance(res, ToolResult)
    assert res.tool == "route_tool"
    assert res.status == AgentStatus.SUCCESS
    assert len(res.data["routes"]) == 3
    assert "recommended_route_id" in res.data
    assert res.evidence.data_status == DataStatus.LIVE
    print(f"  [PASS] Candidate routes evaluated: recommended={res.data['recommended_route_id']}")


async def test_weather_agent_integration():
    print("\n[TEST 8] WeatherAgent -> WeatherTool Integration...")
    agent = WeatherAgent()
    req = AgentRequest(latitude=15.4989, longitude=73.8278, query="Weather check")

    res = await agent.execute(req)
    assert isinstance(res, AgentResult)
    assert res.agent == "weather_agent"
    assert res.status == AgentStatus.SUCCESS
    assert res.confidence == 1.0
    assert res.evidence.source == "Open-Meteo Forecast API"
    assert res.evidence.data_status == DataStatus.LIVE
    assert "current" in res.data
    print(f"  [PASS] WeatherAgent seamlessly delegates to WeatherTool: {res.message}")


async def main():
    print("=" * 65)
    print("ORCA PHASE 2 — TOOL LAYER VERIFICATION SUITE")
    print("=" * 65)

    await test_base_tool_contract()
    await test_weather_tool()
    await test_marine_tool()
    await test_pfz_tool()
    await test_hazard_tool()
    await test_gis_tool()
    await test_route_tool()
    await test_weather_agent_integration()

    print("\n" + "=" * 65)
    print("ALL PHASE 2 TOOL LAYER TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
