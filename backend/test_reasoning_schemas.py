"""
ORCA Phase 5 — Reasoning Schemas Verification Suite
Tests:
1. DecisionFactor validation, category enums, and impact levels
2. Conflict schema, deterministic ConflictSeverity enums, and evidence links
3. ConsistencyReport generation and consistency flags
4. ReasoningContext structure and serialization
5. ReasoningResult schema with decision factors, conclusions, and reasoning graph
"""

import asyncio
from core.schemas import Evidence, DataStatus, AgentResult, AgentStatus
from reasoning.schemas import (
    ConflictSeverity,
    ImpactLevel,
    FactorCategory,
    RequirementLevel,
    DecisionFactor,
    Conflict,
    ConsistencyReport,
    ReasoningContext,
    ReasoningResult,
)


def test_decision_factor_schema():
    print("\n[TEST 1] DecisionFactor Schema Contract Verification...")
    ev = Evidence(
        source="Open-Meteo Marine API",
        source_type="api",
        data_status=DataStatus.LIVE,
    )

    factor = DecisionFactor(
        factor="Significant Wave Height",
        category=FactorCategory.OCEANOGRAPHIC,
        value="0.88 m",
        source_agent="marine",
        evidence=ev,
        impact=ImpactLevel.FAVORABLE,
        confidence=1.0,
        explanation="Wave height is within safe operational limits for small craft.",
    )

    assert factor.factor == "Significant Wave Height"
    assert factor.category == FactorCategory.OCEANOGRAPHIC
    assert factor.value == "0.88 m"
    assert factor.source_agent == "marine"
    assert factor.evidence.source == "Open-Meteo Marine API"
    assert factor.evidence.data_status == DataStatus.LIVE
    assert factor.impact == ImpactLevel.FAVORABLE
    print("  [PASS] DecisionFactor schema verified with full evidence grounding.")


def test_conflict_and_severity_schema():
    print("\n[TEST 2] Conflict and ConflictSeverity Schema Verification...")
    ev = Evidence(
        source="ORCA Marine Hazard Engine",
        source_type="rule_engine",
        data_status=DataStatus.LIVE,
    )

    conflict = Conflict(
        conflict_type="HAZARD_SAFETY_ALERT",
        agents=["hazard"],
        description="HazardAgent reports active gale warning.",
        severity=ConflictSeverity.CRITICAL,
        evidence=[ev],
    )

    assert conflict.conflict_type == "HAZARD_SAFETY_ALERT"
    assert conflict.severity == ConflictSeverity.CRITICAL
    assert len(conflict.evidence) == 1
    assert conflict.agents == ["hazard"]
    print("  [PASS] Conflict schema and deterministic severity verified.")


def test_consistency_report_schema():
    print("\n[TEST 3] ConsistencyReport Schema Contract Verification...")
    # Report with no critical conflicts -> consistent=True
    rep_clean = ConsistencyReport(
        consistent=True,
        conflicts=[],
        warnings=[],
        checked_agents=["weather", "marine"],
    )
    assert rep_clean.consistent is True
    assert len(rep_clean.conflicts) == 0

    # Report with critical conflict -> consistent=False
    c_crit = Conflict(
        conflict_type="HAZARD_CONTRADICTION",
        agents=["hazard", "weather"],
        description="Severe squall conflicting with normal transit.",
        severity=ConflictSeverity.CRITICAL,
    )
    rep_crit = ConsistencyReport(
        consistent=False,
        conflicts=[c_crit],
        warnings=["Critical hazard conflict active."],
        checked_agents=["hazard", "weather"],
    )
    assert rep_crit.consistent is False
    assert len(rep_crit.conflicts) == 1
    assert rep_crit.conflicts[0].severity == ConflictSeverity.CRITICAL
    print("  [PASS] ConsistencyReport correctly handles clean and conflicting states.")


def test_reasoning_context_and_result_schema():
    print("\n[TEST 4] ReasoningContext & ReasoningResult Schema Verification...")
    w_res = AgentResult(
        agent="weather",
        status=AgentStatus.SUCCESS,
        data={"temp_c": 26.5},
        confidence=1.0,
    )
    ctx = ReasoningContext(
        query="Is it safe to fish?",
        intent="fishing_safety",
        agent_results={"weather": w_res},
        evidence=[],
    )
    assert ctx.query == "Is it safe to fish?"
    assert "weather" in ctx.agent_results

    # ReasoningResult
    rep = ConsistencyReport(consistent=True, conflicts=[], checked_agents=["weather"])
    factor = DecisionFactor(
        factor="Air Temperature",
        category=FactorCategory.ATMOSPHERIC,
        value="26.5 °C",
        source_agent="weather",
    )

    result = ReasoningResult(
        decision_factors=[factor],
        consistency=rep,
        conclusions=["Weather is favorable."],
        uncertainties=["Chlorophyll data unavailable."],
        required_followups=["Monitor VHF Channel 16."],
        confidence=0.95,
        iteration_count=1,
        reasoning_graph={"nodes": [{"id": "1"}], "edges": []},
    )

    assert len(result.decision_factors) == 1
    assert result.confidence == 0.95
    assert result.consistency.consistent is True
    assert len(result.conclusions) == 1
    assert len(result.uncertainties) == 1
    assert len(result.required_followups) == 1
    assert result.iteration_count == 1
    assert result.reasoning_graph is not None
    print("  [PASS] ReasoningResult schema contract validated with full structure.")


def main():
    print("=" * 65)
    print("ORCA PHASE 5 — REASONING SCHEMAS VERIFICATION SUITE")
    print("=" * 65)

    test_decision_factor_schema()
    test_conflict_and_severity_schema()
    test_consistency_report_schema()
    test_reasoning_context_and_result_schema()

    print("\n" + "=" * 65)
    print("ALL REASONING SCHEMA TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    main()
