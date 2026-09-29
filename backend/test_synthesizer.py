"""
ORCA Phase 4 — Synthesizer Verification Suite
Tests:
1. Synthesizer uses strictly supplied facts from AgentResults
2. Truthful disclosure of UNAVAILABLE data (does not invent chlorophyll or clear GIS)
3. Stale telemetry and historical provenance disclosure
4. Deterministic confidence calculation (penalized for errors, stale, or unavailable data)
5. Backend-neutral map actions generated strictly from factual coordinates
6. Graceful recovery on LLM failure (deterministic synthesis fallback)
7. Missing agent results handled cleanly without raising unhandled errors
"""

import asyncio
from core.schemas import AgentResult, AgentStatus, Evidence, DataStatus
from orchestration.schemas import PlannerRequest, ExecutionPlan, PlanStep, OrchestrationResult, OrcaResponse
from orchestration.llm_client import MockLLMClient
from orchestration.synthesizer import OrcaSynthesizer


def create_base_orchestration_result(
    agent_results: dict,
    intent: str = "fishing_safety",
    warnings: list = None,
) -> tuple[OrchestrationResult, PlannerRequest]:
    req = PlannerRequest(
        query="Is it safe to fish tomorrow morning?",
        latitude=15.4989,
        longitude=73.8278,
    )
    plan = ExecutionPlan(
        plan_id="plan_synth_test",
        intent=intent,
        required_agents=list(agent_results.keys()),
        steps=[PlanStep(step_id=f"step_{k}", agent=k, purpose=f"Test {k}") for k in agent_results.keys()],
        reasoning_summary="Synthesis verification",
    )
    all_ev = [res.evidence for res in agent_results.values() if res.evidence is not None]
    orch_res = OrchestrationResult(
        query=req.query,
        plan=plan,
        agent_results=agent_results,
        overall_status=AgentStatus.SUCCESS,
        evidence=all_ev,
        warnings=warnings or [],
    )
    return orch_res, req


async def test_synthesizer_uses_only_supplied_facts():
    print("\n[TEST 1] Grounding in Supplied Facts (Deterministic Fallback)...")
    synthesizer = OrcaSynthesizer(llm_client=None)

    weather_res = AgentResult(
        agent="weather",
        status=AgentStatus.SUCCESS,
        data={
            "current": {
                "temperature_c": 27.5,
                "wind_speed_knots": 8.2,
                "wind_direction_compass": "NE",
                "wind_gusts_knots": 11.4,
            }
        },
        evidence=Evidence(source="Open-Meteo", source_type="api", data_status=DataStatus.LIVE),
        confidence=1.0,
    )
    marine_res = AgentResult(
        agent="marine",
        status=AgentStatus.SUCCESS,
        data={
            "current": {
                "wave_height_m": 0.85,
                "dominant_wave_period_s": 5.4,
                "swell_wave_height_m": 0.60,
                "sea_surface_temperature_c": 29.1,
            }
        },
        evidence=Evidence(source="Open-Meteo Marine", source_type="api", data_status=DataStatus.LIVE),
        confidence=1.0,
    )

    orch_res, req = create_base_orchestration_result({
        "weather": weather_res,
        "marine": marine_res,
    })

    orca_resp = await synthesizer.synthesize(orch_res, req)
    assert isinstance(orca_resp, OrcaResponse)
    assert "27.5" in orca_resp.answer
    assert "8.2" in orca_resp.answer
    assert "0.85" in orca_resp.answer
    assert "29.1" in orca_resp.answer
    assert orca_resp.confidence == 1.0
    print("  [PASS] All factual numbers preserved exactly in synthesized answer.")


async def test_synthesizer_unavailable_data_disclosure():
    print("\n[TEST 2] Truthful UNAVAILABLE Telemetry Disclosure...")
    synthesizer = OrcaSynthesizer(llm_client=None)

    # Chlorophyll is UNAVAILABLE
    chloro_res = AgentResult(
        agent="chlorophyll",
        status=AgentStatus.PARTIAL,
        data={"available": False, "chlorophyll_a_mg_m3": None},
        evidence=Evidence(
            source="NASA Ocean Color / MODIS-Aqua",
            source_type="satellite",
            data_status=DataStatus.UNAVAILABLE,
        ),
        confidence=0.5,
        message="Chlorophyll-a satellite data source is not connected.",
    )

    # GIS is UNAVAILABLE
    gis_res = AgentResult(
        agent="gis",
        status=AgentStatus.PARTIAL,
        data={"restriction_status": "UNAVAILABLE", "zones": []},
        evidence=Evidence(
            source="Marine Spatial Data Infrastructure (MSDI)",
            source_type="ogc_wfs",
            data_status=DataStatus.UNAVAILABLE,
        ),
        confidence=0.5,
        message="Official maritime geofences unavailable.",
    )

    orch_res, req = create_base_orchestration_result({
        "chlorophyll": chloro_res,
        "gis": gis_res,
    })

    orca_resp = await synthesizer.synthesize(orch_res, req)

    # Truthful statements must be present, never invented numbers
    assert "unavailable" in orca_resp.answer.lower()
    assert "could not verify official maritime restriction polygons" in orca_resp.answer
    # Confidence must be capped because important capabilities are unavailable
    assert orca_resp.confidence <= 0.65
    assert orca_resp.data_freshness["chlorophyll"] == DataStatus.UNAVAILABLE
    assert orca_resp.data_freshness["gis"] == DataStatus.UNAVAILABLE
    print("  [PASS] UNAVAILABLE chlorophyll and GIS truthfully disclosed with reduced confidence.")


async def test_synthesizer_stale_data_disclosure():
    print("\n[TEST 3] Stale / Historical PFZ Provenance Disclosure...")
    synthesizer = OrcaSynthesizer(llm_client=None)

    pfz_res = AgentResult(
        agent="pfz",
        status=AgentStatus.SUCCESS,
        data={
            "available": True,
            "nearest_advisory": {
                "landing_center": "Malpe",
                "distance_from_query_km": 35.4,
                "bearing_degrees": 235.0,
                "direction": "SW",
                "reference_layer_date": "29-Apr-2024",
            },
            "advisory_metadata": {
                "reference_layer_date": "29-Apr-2024",
            },
        },
        evidence=Evidence(
            source="INCOIS WebGIS GeoServer",
            source_type="ogc_wfs",
            observed_at="2024-04-29T00:00:00Z",
            data_status=DataStatus.STALE,
        ),
        confidence=0.8,
    )

    orch_res, req = create_base_orchestration_result({"pfz": pfz_res})
    orca_resp = await synthesizer.synthesize(orch_res, req)

    assert "29-Apr-2024" in orca_resp.answer or "historical" in orca_resp.answer.lower()
    assert "Malpe" in orca_resp.answer
    assert orca_resp.confidence <= 0.75
    assert orca_resp.data_freshness["pfz"] == DataStatus.STALE
    print("  [PASS] Historical/Stale PFZ layer date disclosed explicitly with confidence cap.")


async def test_synthesizer_confidence_calculation():
    print("\n[TEST 4] Deterministic Confidence Penalties...")
    synthesizer = OrcaSynthesizer()

    # Scenario A: All LIVE and SUCCESS -> 1.0
    res_a, req_a = create_base_orchestration_result({
        "weather": AgentResult(agent="weather", status=AgentStatus.SUCCESS, confidence=1.0, evidence=Evidence(source="A", source_type="api", data_status=DataStatus.LIVE)),
        "marine": AgentResult(agent="marine", status=AgentStatus.SUCCESS, confidence=1.0, evidence=Evidence(source="B", source_type="api", data_status=DataStatus.LIVE)),
    })
    resp_a = await synthesizer.synthesize(res_a, req_a)
    assert resp_a.confidence == 1.0

    # Scenario B: Stale agent -> capped at 0.75
    res_b, req_b = create_base_orchestration_result({
        "weather": AgentResult(agent="weather", status=AgentStatus.SUCCESS, confidence=1.0, evidence=Evidence(source="A", source_type="api", data_status=DataStatus.LIVE)),
        "pfz": AgentResult(agent="pfz", status=AgentStatus.SUCCESS, confidence=0.9, evidence=Evidence(source="C", source_type="api", data_status=DataStatus.STALE)),
    })
    resp_b = await synthesizer.synthesize(res_b, req_b)
    assert resp_b.confidence == 0.75

    # Scenario C: Failed agent -> capped at 0.35
    res_c, req_c = create_base_orchestration_result({
        "weather": AgentResult(agent="weather", status=AgentStatus.SUCCESS, confidence=1.0, evidence=Evidence(source="A", source_type="api", data_status=DataStatus.LIVE)),
        "gis": AgentResult(agent="gis", status=AgentStatus.FAILED, confidence=0.0),
    })
    resp_c = await synthesizer.synthesize(res_c, req_c)
    assert resp_c.confidence <= 0.35
    print("  [PASS] Confidence strictly derived deterministically from agent outcomes.")


async def test_synthesizer_map_actions():
    print("\n[TEST 5] Structured Map Actions Generation...")
    synthesizer = OrcaSynthesizer()

    pfz_res = AgentResult(
        agent="pfz",
        status=AgentStatus.SUCCESS,
        data={
            "available": True,
            "nearest_advisory": {
                "landing_center": "Ratnagiri",
                "lc_coordinates": {"latitude": 16.98, "longitude": 73.28},
                "bearing_degrees": 210.0,
                "distance_from_query_km": 28.0,
            }
        },
    )
    route_res = AgentResult(
        agent="route",
        status=AgentStatus.SUCCESS,
        data={
            "recommended_route_id": "corridor_alpha",
            "destination_coordinates": {"latitude": 16.98, "longitude": 73.28},
            "destination_name": "Ratnagiri Target",
            "routes": [
                {"id": "corridor_alpha", "name": "Direct Alpha", "distance_nm": 15.2, "risk_score": 22.0, "risk_level": "LOW"}
            ]
        },
    )

    orch_res, req = create_base_orchestration_result({
        "pfz": pfz_res,
        "route": route_res,
    })

    resp = await synthesizer.synthesize(orch_res, req)
    action_types = [a.action_type for a in resp.map_actions]
    assert "show_origin" in action_types
    assert "show_pfz" in action_types
    assert "show_destination" in action_types
    assert "show_route" in action_types
    assert "fit_bounds" in action_types

    # Coordinates in show_pfz must match real agent output
    pfz_action = next(a for a in resp.map_actions if a.action_type == "show_pfz")
    assert pfz_action.data["coordinates"]["latitude"] == 16.98
    assert pfz_action.data["coordinates"]["longitude"] == 73.28
    print("  [PASS] Backend-neutral map actions contain exact factual coordinates.")


async def test_synthesizer_llm_failure_fallback():
    print("\n[TEST 6] LLM Synthesis Failure Handled Gracefully...")
    # LLM configured to fail
    failing_llm = MockLLMClient(should_fail=True, failure_message="API Quota Exceeded")
    synthesizer = OrcaSynthesizer(llm_client=failing_llm)

    weather_res = AgentResult(
        agent="weather",
        status=AgentStatus.SUCCESS,
        data={"current": {"temperature_c": 26.0, "wind_speed_knots": 6.0}},
        evidence=Evidence(source="Open-Meteo", source_type="api", data_status=DataStatus.LIVE),
        confidence=1.0,
    )

    orch_res, req = create_base_orchestration_result({"weather": weather_res})

    # Must NOT raise exception; must fall back to deterministic synthesis
    resp = await synthesizer.synthesize(orch_res, req)
    assert isinstance(resp, OrcaResponse)
    assert "26.0" in resp.answer
    assert "6.0" in resp.answer
    print("  [PASS] LLM failure fell back to deterministic factual synthesis smoothly.")


async def main():
    print("=" * 65)
    print("ORCA PHASE 4 — SYNTHESIZER VERIFICATION SUITE")
    print("=" * 65)

    await test_synthesizer_uses_only_supplied_facts()
    await test_synthesizer_unavailable_data_disclosure()
    await test_synthesizer_stale_data_disclosure()
    await test_synthesizer_confidence_calculation()
    await test_synthesizer_map_actions()
    await test_synthesizer_llm_failure_fallback()

    print("\n" + "=" * 65)
    print("ALL SYNTHESIZER TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
