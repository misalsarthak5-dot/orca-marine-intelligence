"""
ORCA Phase 5 — Collaborative Reasoning Engine Verification Suite
Tests the 6 core reasoning scenarios, bounded iteration, reasoning graph, and synthesizer integration:
1. Scenario 1 — Fishing Opportunity: PFZ (Live) + Marine (Live) + Chlorophyll (Live) + Weather (Live)
2. Scenario 2 — Stale PFZ: PFZ (Stale) + Marine (Live) + Weather (Live) -> Freshness warning & confidence cap
3. Scenario 3 — GIS Unavailable: PFZ (Live) + Route (Success) + GIS (Unavailable) -> Restriction caveat
4. Scenario 4 — Hazard Conflict: Hazard (HIGH) + Marine (Favorable) -> Critical conflict cannot be hidden
5. Scenario 5 — Chlorophyll Unavailable: PFZ (Live) + Chlorophyll (Unavailable) -> Honest disclosure
6. Scenario 6 — PFZ -> Route: Coordinate provenance preserved and traceable
7. Bounded Reasoning Iteration: Max 2 passes enforced, zero infinite loops
8. Reasoning Graph Construction: Structured nodes and edges generated
9. Synthesizer Integration: OrcaSynthesizer seamlessly consumes ReasoningResult
"""

import asyncio
from core.schemas import AgentResult, AgentStatus, Evidence, DataStatus
from orchestration.schemas import PlannerRequest, ExecutionPlan, PlanStep, OrchestrationResult
from orchestration.synthesizer import OrcaSynthesizer
from reasoning.schemas import (
    ReasoningContext,
    ReasoningResult,
    ConflictSeverity,
    ImpactLevel,
)
from reasoning.engine import OperationalReasoningEngine


async def test_scenario_1_fishing_opportunity():
    print("\n[TEST 1] Scenario 1 — Comprehensive Fishing Opportunity (All LIVE)...")
    engine = OperationalReasoningEngine()

    pfz_res = AgentResult(
        agent="pfz",
        status=AgentStatus.SUCCESS,
        data={
            "available": True,
            "nearest_advisory": {
                "landing_center": "Panaji (Malim)",
                "distance_from_query_km": 21.0,
                "bearing_degrees": 250.0,
                "direction": "SW",
            }
        },
        evidence=Evidence(source="INCOIS", source_type="ogc_wfs", data_status=DataStatus.LIVE),
        confidence=1.0,
    )
    marine_res = AgentResult(
        agent="marine",
        status=AgentStatus.SUCCESS,
        data={"current": {"wave_height_m": 0.85, "dominant_wave_period_s": 5.5, "sea_surface_temperature_c": 28.5}},
        evidence=Evidence(source="Open-Meteo Marine", source_type="api", data_status=DataStatus.LIVE),
        confidence=1.0,
    )
    chla_res = AgentResult(
        agent="chlorophyll",
        status=AgentStatus.SUCCESS,
        data={"available": True, "chlorophyll_a_mg_m3": 0.72},
        evidence=Evidence(source="MODIS-Aqua", source_type="satellite", data_status=DataStatus.LIVE),
        confidence=1.0,
    )
    weather_res = AgentResult(
        agent="weather",
        status=AgentStatus.SUCCESS,
        data={"current": {"wind_speed_knots": 7.5, "wind_gusts_knots": 10.0}},
        evidence=Evidence(source="Open-Meteo", source_type="api", data_status=DataStatus.LIVE),
        confidence=1.0,
    )

    ctx = ReasoningContext(
        query="Where should I fish tomorrow?",
        intent="fishing_ground_selection",
        agent_results={"pfz": pfz_res, "marine": marine_res, "chlorophyll": chla_res, "weather": weather_res},
    )

    result = await engine.reason(ctx)
    assert result.consistency.consistent is True
    assert len(result.consistency.conflicts) == 0
    assert result.confidence >= 0.95
    assert any("Panaji (Malim)" in c for c in result.conclusions)
    assert any("0.72 mg/m³" in c for c in result.conclusions)
    assert len(result.uncertainties) == 0
    print("  [PASS] Scenario 1: All factors extracted, 0 false conflicts, high confidence verified.")


async def test_scenario_2_stale_pfz():
    print("\n[TEST 2] Scenario 2 — Stale PFZ Telemetry Provenance...")
    engine = OperationalReasoningEngine()

    pfz_res = AgentResult(
        agent="pfz",
        status=AgentStatus.SUCCESS,
        data={
            "available": True,
            "nearest_advisory": {
                "landing_center": "KharDanda",
                "distance_from_query_km": 31.0,
                "bearing_degrees": 281.0,
                "reference_layer_date": "29-Apr-2024",
            }
        },
        evidence=Evidence(
            source="INCOIS WebGIS GeoServer",
            source_type="ogc_wfs",
            observed_at="2024-04-29T00:00:00Z",
            data_status=DataStatus.STALE,
        ),
        confidence=0.8,
    )
    marine_res = AgentResult(
        agent="marine",
        status=AgentStatus.SUCCESS,
        data={"current": {"wave_height_m": 0.60}},
        evidence=Evidence(source="Open-Meteo Marine", source_type="api", data_status=DataStatus.LIVE),
        confidence=1.0,
    )

    ctx = ReasoningContext(
        query="Where is the fishing zone?",
        intent="pfz_discovery",
        agent_results={"pfz": pfz_res, "marine": marine_res},
    )

    result = await engine.reason(ctx)
    # Stale PFZ must trigger freshness warning
    stale_conflicts = [c for c in result.consistency.conflicts if c.conflict_type == "FRESHNESS_STALE_DATA"]
    assert len(stale_conflicts) == 1
    # Confidence capped due to stale telemetry
    assert result.confidence <= 0.75
    # Uncertainties must state historical provenance
    assert any("historical reference" in u for u in result.uncertainties)
    print("  [PASS] Scenario 2: Stale PFZ provenance warned, confidence capped at 0.75.")


async def test_scenario_3_gis_unavailable_with_route():
    print("\n[TEST 3] Scenario 3 — GIS Unavailable with Active Route Evaluation...")
    engine = OperationalReasoningEngine()

    route_res = AgentResult(
        agent="route",
        status=AgentStatus.SUCCESS,
        data={
            "recommended_route_id": "corridor_alpha",
            "routes": [{"id": "corridor_alpha", "name": "Direct Passage", "distance_nm": 14.2, "risk_score": 20, "risk_level": "LOW"}],
        },
        evidence=Evidence(source="RouteEngine", source_type="api", data_status=DataStatus.LIVE),
        confidence=1.0,
    )
    gis_res = AgentResult(
        agent="gis",
        status=AgentStatus.PARTIAL,
        data={"restriction_status": "UNAVAILABLE", "zones": []},
        evidence=Evidence(source="MSDI WFS", source_type="ogc_wfs", data_status=DataStatus.UNAVAILABLE),
        confidence=0.5,
    )

    ctx = ReasoningContext(
        query="Can I reach the destination safely?",
        intent="route_navigation",
        agent_results={"route": route_res, "gis": gis_res},
    )

    result = await engine.reason(ctx)
    # Conflict caught: unverified maritime restriction
    assert any(c.conflict_type == "UNVERIFIED_MARITIME_RESTRICTION" for c in result.consistency.conflicts)
    # Conclusions must NOT state route is restriction-free
    conclusions_str = " ".join(result.conclusions)
    assert "restriction polygons were unavailable" in conclusions_str or "unverified" in conclusions_str.lower()
    assert "restriction-free" not in conclusions_str.lower()
    print("  [PASS] Scenario 3: Route evaluated without falsely claiming restriction clearance.")


async def test_scenario_4_hazard_conflict():
    print("\n[TEST 4] Scenario 4 — Hazard Conflict (HIGH Hazard Cannot Be Hidden)...")
    engine = OperationalReasoningEngine()

    hazard_res = AgentResult(
        agent="hazard",
        status=AgentStatus.SUCCESS,
        data={"hazard_state": "HIGH", "alerts": [{"event": "Severe Squall Line"}]},
        evidence=Evidence(source="HazardEngine", source_type="rule_engine", data_status=DataStatus.LIVE),
        confidence=1.0,
    )
    marine_res = AgentResult(
        agent="marine",
        status=AgentStatus.SUCCESS,
        data={"current": {"wave_height_m": 0.80}},
        evidence=Evidence(source="Open-Meteo Marine", source_type="api", data_status=DataStatus.LIVE),
        confidence=1.0,
    )

    ctx = ReasoningContext(
        query="Is it safe to fish?",
        intent="fishing_safety",
        agent_results={"hazard": hazard_res, "marine": marine_res},
    )

    result = await engine.reason(ctx)
    assert result.consistency.consistent is False
    assert any(c.severity == ConflictSeverity.CRITICAL for c in result.consistency.conflicts)
    assert result.confidence <= 0.35
    assert any("SAFETY ADVISORY (CRITICAL)" in c for c in result.conclusions)
    print("  [PASS] Scenario 4: HIGH hazard surfaced as critical conclusion and penalized confidence.")


async def test_scenario_5_chlorophyll_unavailable():
    print("\n[TEST 5] Scenario 5 — Chlorophyll Unavailable (Zero Fabrication)...")
    engine = OperationalReasoningEngine()

    pfz_res = AgentResult(
        agent="pfz",
        status=AgentStatus.SUCCESS,
        data={"available": True, "nearest_advisory": {"landing_center": "Ratnagiri"}},
        evidence=Evidence(source="INCOIS", source_type="ogc_wfs", data_status=DataStatus.LIVE),
        confidence=1.0,
    )
    chla_res = AgentResult(
        agent="chlorophyll",
        status=AgentStatus.PARTIAL,
        data={"available": False, "chlorophyll_a_mg_m3": None},
        evidence=Evidence(source="NASA Ocean Color", source_type="satellite", data_status=DataStatus.UNAVAILABLE),
        confidence=0.5,
    )

    ctx = ReasoningContext(
        query="Find fish near Ratnagiri",
        intent="fishing_ground_selection",
        agent_results={"pfz": pfz_res, "chlorophyll": chla_res},
    )

    result = await engine.reason(ctx)
    # PFZ reasoning must proceed
    assert any("Ratnagiri" in c for c in result.conclusions)
    # Chlorophyll must be recorded in uncertainties
    assert any("Satellite chlorophyll-a concentration is currently unavailable" in u for u in result.uncertainties)
    # Check that no factor has fabricated chlorophyll number
    chla_factors = [f for f in result.decision_factors if f.factor == "Chlorophyll-a Concentration"]
    assert len(chla_factors) == 0
    print("  [PASS] Scenario 5: PFZ reasoning proceeded while Chlorophyll was disclosed as unavailable.")


async def test_scenario_6_pfz_to_route_provenance():
    print("\n[TEST 6] Scenario 6 — PFZ -> Route Provenance Traceability...")
    engine = OperationalReasoningEngine()

    pfz_res = AgentResult(
        agent="pfz",
        status=AgentStatus.SUCCESS,
        data={
            "available": True,
            "nearest_advisory": {
                "landing_center": "Mangalore Harbour",
                "lc_coordinates": {"latitude": 12.91, "longitude": 74.85},
            }
        },
        evidence=Evidence(source="INCOIS", source_type="ogc_wfs", data_status=DataStatus.LIVE),
        confidence=1.0,
    )
    route_res = AgentResult(
        agent="route",
        status=AgentStatus.SUCCESS,
        data={
            "destination_name": "Mangalore Harbour PFZ Target",
            "destination_coordinates": {"latitude": 12.91, "longitude": 74.85},
            "recommended_route_id": "route_direct",
            "routes": [{"id": "route_direct", "name": "Direct Path", "distance_nm": 22.0, "risk_score": 18, "risk_level": "LOW"}],
        },
        evidence=Evidence(source="RouteEngine", source_type="api", data_status=DataStatus.LIVE),
        confidence=1.0,
    )

    ctx = ReasoningContext(
        query="Route to nearest PFZ",
        intent="pfz_passage_safety",
        agent_results={"pfz": pfz_res, "route": route_res},
    )

    result = await engine.reason(ctx)
    route_factors = [f for f in result.decision_factors if f.source_agent == "route"]
    assert len(route_factors) > 0
    assert route_factors[0].evidence.source == "RouteEngine"
    assert "Direct Path" in str(route_factors[0].value)
    print("  [PASS] Scenario 6: Route factors trace back to destination and RouteEngine evidence.")


async def test_bounded_reasoning_iteration():
    print("\n[TEST 7] Bounded Reasoning Iteration (Max 2 Passes)...")
    engine = OperationalReasoningEngine()

    ctx = ReasoningContext(
        query="Test iterations",
        intent="general_marine_inquiry",
        agent_results={},
    )

    result = await engine.reason(ctx)
    assert 1 <= result.iteration_count <= 2, f"Expected 1 or 2 iterations, got {result.iteration_count}"
    print(f"  [PASS] Controlled bounded iterations verified: count={result.iteration_count} <= 2.")


async def test_reasoning_graph():
    print("\n[TEST 8] Reasoning Graph Structure...")
    engine = OperationalReasoningEngine()

    w_res = AgentResult(
        agent="weather",
        status=AgentStatus.SUCCESS,
        data={"current": {"wind_speed_knots": 10.0}},
        confidence=1.0,
    )
    ctx = ReasoningContext(
        query="Wind check",
        intent="weather_inquiry",
        agent_results={"weather": w_res},
    )

    result = await engine.reason(ctx)
    graph = result.reasoning_graph
    assert graph is not None
    assert graph["total_nodes"] > 0
    assert graph["total_edges"] > 0
    node_types = {n["type"] for n in graph["nodes"]}
    assert "USER_QUERY" in node_types
    assert "INTENT" in node_types
    assert "DOMAIN_AGENT" in node_types
    assert "DECISION_FACTOR" in node_types
    assert "CONCLUSION" in node_types
    print(f"  [PASS] Lightweight reasoning graph generated: {graph['total_nodes']} nodes, {graph['total_edges']} edges.")


async def test_synthesizer_integration_with_reasoning():
    print("\n[TEST 9] Synthesizer Integration with ReasoningResult...")
    engine = OperationalReasoningEngine()
    synthesizer = OrcaSynthesizer(llm_client=None)

    weather_res = AgentResult(
        agent="weather",
        status=AgentStatus.SUCCESS,
        data={"current": {"wind_speed_knots": 8.0, "temperature_c": 27.0}},
        evidence=Evidence(source="Open-Meteo", source_type="api", data_status=DataStatus.LIVE),
        confidence=1.0,
    )
    marine_res = AgentResult(
        agent="marine",
        status=AgentStatus.SUCCESS,
        data={"current": {"wave_height_m": 0.75, "sea_surface_temperature_c": 29.0}},
        evidence=Evidence(source="Open-Meteo Marine", source_type="api", data_status=DataStatus.LIVE),
        confidence=1.0,
    )

    req = PlannerRequest(query="Is it safe?", latitude=15.5, longitude=73.8)
    plan = ExecutionPlan(
        plan_id="plan_test_synth",
        intent="fishing_safety",
        required_agents=["weather", "marine"],
        steps=[PlanStep(step_id="step_1", agent="weather", purpose="weather")],
        reasoning_summary="Synth test",
    )
    orch_res = OrchestrationResult(
        query=req.query,
        plan=plan,
        agent_results={"weather": weather_res, "marine": marine_res},
        overall_status=AgentStatus.SUCCESS,
        evidence=[weather_res.evidence, marine_res.evidence],
    )

    ctx = ReasoningContext(
        query=req.query,
        intent=plan.intent,
        agent_results=orch_res.agent_results,
        evidence=orch_res.evidence,
        plan=plan,
    )

    reasoning_res = await engine.reason(ctx)
    orca_resp = await synthesizer.synthesize(orch_res, req, reasoning_result=reasoning_res)

    assert orca_resp.reasoning is not None
    assert orca_resp.confidence == reasoning_res.confidence
    assert "Operational Reasoning Conclusions" in orca_resp.answer
    assert "Actionable Mariner Verification Checks" in orca_resp.answer
    print("  [PASS] OrcaSynthesizer seamlessly integrated ReasoningResult and exposed full audit trail.")


async def main():
    print("=" * 65)
    print("ORCA PHASE 5 — REASONING ENGINE VERIFICATION SUITE")
    print("=" * 65)

    await test_scenario_1_fishing_opportunity()
    await test_scenario_2_stale_pfz()
    await test_scenario_3_gis_unavailable_with_route()
    await test_scenario_4_hazard_conflict()
    await test_scenario_5_chlorophyll_unavailable()
    await test_scenario_6_pfz_to_route_provenance()
    await test_bounded_reasoning_iteration()
    await test_reasoning_graph()
    await test_synthesizer_integration_with_reasoning()

    print("\n" + "=" * 65)
    print("ALL REASONING ENGINE TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
