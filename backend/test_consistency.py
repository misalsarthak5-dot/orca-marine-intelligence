"""
ORCA Phase 5 — Cross-Agent Consistency Verification Suite
Tests:
1. Example A: Complementary conditions (wind 8 kn, wave 0.7m) -> No conflict, consistent=True
2. Example B: HazardAgent reports HIGH hazard -> CRITICAL conflict, consistent=False
3. Example C: PFZ target exists but Route destination unavailable -> Incomplete workflow conflict
4. Example D: GIS unavailable while Route evaluated -> UNVERIFIED_MARITIME_RESTRICTION warning conflict
5. Example E: PFZ data is STALE -> FRESHNESS_STALE_DATA warning conflict
6. Deterministic severity classification (INFO, WARNING, CRITICAL)
7. Physical plausibility anomaly detection (e.g. storm winds with flat calm sea)
"""

import asyncio
from core.schemas import AgentResult, AgentStatus, Evidence, DataStatus
from reasoning.schemas import (
    ReasoningContext,
    ConflictSeverity,
)
from reasoning.consistency import ConsistencyChecker


def test_example_a_complementary_conditions():
    print("\n[TEST 1] Example A: Complementary Weather & Marine Conditions...")
    checker = ConsistencyChecker()

    weather_res = AgentResult(
        agent="weather",
        status=AgentStatus.SUCCESS,
        data={"current": {"wind_speed_knots": 8.0, "wind_gusts_knots": 11.0}},
        evidence=Evidence(source="Open-Meteo", source_type="api", data_status=DataStatus.LIVE),
        confidence=1.0,
    )
    marine_res = AgentResult(
        agent="marine",
        status=AgentStatus.SUCCESS,
        data={"current": {"wave_height_m": 0.70, "dominant_wave_period_s": 5.0}},
        evidence=Evidence(source="Open-Meteo Marine", source_type="api", data_status=DataStatus.LIVE),
        confidence=1.0,
    )

    ctx = ReasoningContext(
        query="Is it calm today?",
        intent="environmental_assessment",
        agent_results={"weather": weather_res, "marine": marine_res},
    )

    report = checker.analyze(ctx)
    assert report.consistent is True
    assert len(report.conflicts) == 0
    print("  [PASS] Wind 8 kn and wave 0.7m recognized as complementary with 0 conflicts.")


def test_example_b_hazard_contradiction():
    print("\n[TEST 2] Example B: Hazard Contradiction (HIGH Hazard)...")
    checker = ConsistencyChecker()

    hazard_res = AgentResult(
        agent="hazard",
        status=AgentStatus.SUCCESS,
        data={
            "hazard_state": "HIGH",
            "alerts": [{"event": "Severe Gale Squall Warning", "severity": "HIGH"}],
        },
        evidence=Evidence(source="ORCA Hazard Engine", source_type="rule_engine", data_status=DataStatus.LIVE),
        confidence=1.0,
    )

    ctx = ReasoningContext(
        query="Can I sail tomorrow?",
        intent="fishing_safety",
        agent_results={"hazard": hazard_res},
    )

    report = checker.analyze(ctx)
    assert report.consistent is False
    assert len(report.conflicts) == 1
    conflict = report.conflicts[0]
    assert conflict.conflict_type == "HAZARD_SAFETY_ALERT"
    assert conflict.severity == ConflictSeverity.CRITICAL
    assert "HIGH" in conflict.description
    print("  [PASS] HIGH hazard state surfaced as CRITICAL conflict making consistent=False.")


def test_example_c_pfz_route_incomplete_workflow():
    print("\n[TEST 3] Example C: Incomplete Workflow (PFZ Exists, Route Failed)...")
    checker = ConsistencyChecker()

    pfz_res = AgentResult(
        agent="pfz",
        status=AgentStatus.SUCCESS,
        data={"available": True, "nearest_advisory": {"landing_center": "Malpe"}},
        evidence=Evidence(source="INCOIS", source_type="ogc_wfs", data_status=DataStatus.LIVE),
        confidence=1.0,
    )
    route_res = AgentResult(
        agent="route",
        status=AgentStatus.FAILED,
        data=None,
        message="Route destination unavailable",
        errors=["Missing destination coordinates"],
        confidence=0.0,
    )

    ctx = ReasoningContext(
        query="Navigate to nearest PFZ",
        intent="pfz_passage_safety",
        agent_results={"pfz": pfz_res, "route": route_res},
    )

    report = checker.analyze(ctx)
    incomplete_conflicts = [c for c in report.conflicts if c.conflict_type == "INCOMPLETE_WORKFLOW"]
    assert len(incomplete_conflicts) == 1
    assert incomplete_conflicts[0].severity == ConflictSeverity.WARNING
    assert "route navigation" in incomplete_conflicts[0].description.lower()
    print("  [PASS] Identified PFZ -> Route workflow gap as WARNING conflict.")


def test_example_d_gis_unavailable_with_evaluated_route():
    print("\n[TEST 4] Example D: GIS UNAVAILABLE with Evaluated Route Corridors...")
    checker = ConsistencyChecker()

    route_res = AgentResult(
        agent="route",
        status=AgentStatus.SUCCESS,
        data={"recommended_route_id": "route_1", "routes": [{"id": "route_1"}]},
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
        query="Find route to target",
        intent="route_navigation",
        agent_results={"route": route_res, "gis": gis_res},
    )

    report = checker.analyze(ctx)
    gis_conflicts = [c for c in report.conflicts if c.conflict_type == "UNVERIFIED_MARITIME_RESTRICTION"]
    assert len(gis_conflicts) == 1
    assert gis_conflicts[0].severity == ConflictSeverity.WARNING
    assert "restriction-zone" in gis_conflicts[0].description
    print("  [PASS] Detected unverified restriction clearance caveat without concluding route is restriction-free.")


def test_example_e_stale_pfz_freshness_contradiction():
    print("\n[TEST 5] Example E: Stale PFZ Provenance Warning...")
    checker = ConsistencyChecker()

    pfz_res = AgentResult(
        agent="pfz",
        status=AgentStatus.SUCCESS,
        data={"available": True, "nearest_advisory": {"landing_center": "Panaji"}},
        evidence=Evidence(
            source="INCOIS WebGIS GeoServer",
            source_type="ogc_wfs",
            observed_at="2024-04-29T00:00:00Z",
            data_status=DataStatus.STALE,
        ),
        confidence=0.8,
    )

    ctx = ReasoningContext(
        query="Where is today's PFZ?",
        intent="pfz_discovery",
        agent_results={"pfz": pfz_res},
    )

    report = checker.analyze(ctx)
    stale_conflicts = [c for c in report.conflicts if c.conflict_type == "FRESHNESS_STALE_DATA"]
    assert len(stale_conflicts) == 1
    assert stale_conflicts[0].severity == ConflictSeverity.WARNING
    assert "2024-04-29" in stale_conflicts[0].description
    print("  [PASS] Stale PFZ telemetry flagged as FRESHNESS_STALE_DATA warning.")


def test_physical_plausibility_anomaly():
    print("\n[TEST 6] Physical Plausibility Anomaly (Severe Wind with Dead Calm Sea)...")
    checker = ConsistencyChecker()

    weather_res = AgentResult(
        agent="weather",
        status=AgentStatus.SUCCESS,
        data={"current": {"wind_speed_knots": 48.0}},
        evidence=Evidence(source="Open-Meteo", source_type="api", data_status=DataStatus.LIVE),
        confidence=1.0,
    )
    marine_res = AgentResult(
        agent="marine",
        status=AgentStatus.SUCCESS,
        data={"current": {"wave_height_m": 0.20}},
        evidence=Evidence(source="Open-Meteo Marine", source_type="api", data_status=DataStatus.LIVE),
        confidence=1.0,
    )

    ctx = ReasoningContext(
        query="Weather check",
        intent="environmental_assessment",
        agent_results={"weather": weather_res, "marine": marine_res},
    )

    report = checker.analyze(ctx)
    anomaly_conflicts = [c for c in report.conflicts if c.conflict_type == "PHYSICAL_PLAUSIBILITY_ANOMALY"]
    assert len(anomaly_conflicts) == 1
    assert anomaly_conflicts[0].severity == ConflictSeverity.WARNING
    assert "48.0 kn" in anomaly_conflicts[0].description
    print("  [PASS] Extreme physical divergence (48 kn wind vs 0.2 m wave) flagged cleanly.")


def main():
    print("=" * 65)
    print("ORCA PHASE 5 — CROSS-AGENT CONSISTENCY VERIFICATION SUITE")
    print("=" * 65)

    test_example_a_complementary_conditions()
    test_example_b_hazard_contradiction()
    test_example_c_pfz_route_incomplete_workflow()
    test_example_d_gis_unavailable_with_evaluated_route()
    test_example_e_stale_pfz_freshness_contradiction()
    test_physical_plausibility_anomaly()

    print("\n" + "=" * 65)
    print("ALL CROSS-AGENT CONSISTENCY TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    main()
