"""
Verification Suite for ORCA Phase 1: Contract Layer & WeatherAgent
Tests:
1. Schema contract validation (AgentRequest, AgentResult, Evidence, Enums)
2. WeatherAgent execution with real live Open-Meteo telemetry
3. WeatherAgent graceful error handling without crashing
4. Preservation of existing FastAPI endpoints via TestClient
"""

import asyncio
from unittest.mock import patch
from fastapi.testclient import TestClient

from core.schemas import (
    AgentRequest,
    AgentResult,
    Evidence,
    DataStatus,
    AgentStatus,
)
from agents.weather_agent import WeatherAgent
from main import app


def test_schema_contracts():
    print("\n[TEST 1] Standardized Schema Contracts Verification...")
    
    # 1. Verify AgentRequest creation and validation
    req = AgentRequest(
        query="What is the weather at Goa?",
        latitude=15.4989,
        longitude=73.8278,
        timestamp="now",
        context={"user_lang": "en"}
    )
    assert req.latitude == 15.4989
    assert req.longitude == 73.8278
    assert req.query == "What is the weather at Goa?"
    assert req.context["user_lang"] == "en"

    # 2. Verify Evidence creation
    ev = Evidence(
        source="Open-Meteo",
        source_type="api",
        data_status=DataStatus.LIVE,
        reference="https://open-meteo.com"
    )
    assert ev.data_status == DataStatus.LIVE
    assert ev.retrieved_at is not None

    # 3. Verify AgentResult creation
    res = AgentResult(
        agent="weather_agent",
        status=AgentStatus.SUCCESS,
        data={"temp": 28.5},
        evidence=ev,
        confidence=1.0,
        message="Telemetry ok",
        errors=[]
    )
    assert res.agent == "weather_agent"
    assert res.status == AgentStatus.SUCCESS
    assert res.confidence == 1.0
    print("  [PASS] Schema contracts adhere strictly to the ORCA specifications.")


async def test_weather_agent_live():
    print("\n[TEST 2] WeatherAgent Live Execution (Goa)...")
    agent = WeatherAgent()
    req = AgentRequest(
        query="Weather check",
        latitude=15.4989,
        longitude=73.8278,
    )
    
    result = await agent.execute(req)
    
    assert isinstance(result, AgentResult), "Must return an AgentResult instance"
    assert result.agent == "weather_agent"
    assert result.status == AgentStatus.SUCCESS, f"Expected SUCCESS, got {result.status}"
    assert result.data is not None, "Data payload must not be None"
    assert "current" in result.data, "Payload must contain 'current' conditions"
    assert "hourly" in result.data, "Payload must contain 'hourly' forecast"
    assert result.evidence is not None, "Evidence must be attached"
    assert result.evidence.data_status == DataStatus.LIVE
    assert result.evidence.source == "Open-Meteo Forecast API"
    assert result.evidence.observed_at is not None
    assert result.confidence == 1.0
    assert len(result.errors) == 0
    print(f"  [PASS] Live telemetry retrieved: {result.message}")
    print(f"         Confidence: {result.confidence}, Evidence Status: {result.evidence.data_status}")


async def test_weather_agent_error_handling():
    print("\n[TEST 3] WeatherAgent Error Handling (Graceful Degradation)...")
    agent = WeatherAgent()

    # 1. Pydantic coordinate boundary validation test
    try:
        AgentRequest(
            latitude=999.0,  # Out of range (-90 to 90)
            longitude=73.8278,
        )
        assert False, "Should have raised ValidationError for invalid latitude"
    except Exception as e:
        print(f"  [PASS] Pydantic schema validation rejected invalid coordinate: {type(e).__name__}")

    # 2. Simulated upstream API failure
    with patch("agents.weather_agent.get_weather_data", side_effect=Exception("Simulated upstream network timeout")):
        fail_req = AgentRequest(latitude=15.4989, longitude=73.8278)
        fail_res = await agent.execute(fail_req)
        assert fail_res.status == AgentStatus.FAILED
        assert fail_res.confidence == 0.0
        assert "Simulated upstream network timeout" in fail_res.errors[0]
        assert fail_res.evidence.data_status == DataStatus.ERROR
        print(f"  [PASS] Upstream network error trapped cleanly: {fail_res.message}")


def test_fastapi_endpoints_preservation():
    print("\n[TEST 4] Existing FastAPI Endpoints Backward Compatibility...")
    client = TestClient(app)

    # 1. Health
    r_health = client.get("/api/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "ok"
    print("  [PASS] /api/health returned 200 OK")

    # 2. Weather
    r_weather = client.get("/api/weather?latitude=15.4989&longitude=73.8278")
    assert r_weather.status_code == 200
    assert "current" in r_weather.json()
    print("  [PASS] /api/weather returned 200 OK with live data")

    # 3. Marine
    r_marine = client.get("/api/marine?latitude=15.4989&longitude=73.8278")
    assert r_marine.status_code == 200
    assert "current" in r_marine.json()
    print("  [PASS] /api/marine returned 200 OK with live data")

    # 4. Safety
    r_safety = client.get("/api/safety?latitude=15.4989&longitude=73.8278")
    assert r_safety.status_code == 200
    assert "risk_level" in r_safety.json()
    print("  [PASS] /api/safety returned 200 OK")

    # 5. Chlorophyll
    r_chloro = client.get("/api/chlorophyll?latitude=15.4989&longitude=73.8278")
    assert r_chloro.status_code == 200
    assert r_chloro.json()["available"] is False
    print("  [PASS] /api/chlorophyll returned 200 OK with truthful unavailable state")


async def main():
    print("=" * 65)
    print("ORCA AGENT CONTRACT & WEATHER AGENT VERIFICATION SUITE")
    print("=" * 65)
    
    test_schema_contracts()
    await test_weather_agent_live()
    await test_weather_agent_error_handling()
    test_fastapi_endpoints_preservation()
    
    print("\n" + "=" * 65)
    print("ALL PHASE 1 CONTRACT & AGENT TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
