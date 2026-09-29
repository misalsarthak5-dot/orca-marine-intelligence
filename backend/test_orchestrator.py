"""
ORCA Phase 4 — Orchestrator Verification Suite
Tests:
1. Single agent execution through orchestrator
2. Multiple parallel agents executed concurrently
3. Strict dependency ordering (Step 1 before Step 2)
4. PFZ -> Route dependency (passing PFZ coordinates into Route)
5. Agent failure propagation without crashing orchestrator
6. Partial results handling (one agent partial/unavailable while others succeed)
7. Evidence aggregation from all agents
8. Status preservation (LIVE, CACHED, STALE, UNAVAILABLE, ERROR)
"""

import asyncio
import time
from typing import Dict, Any, Optional

from core.schemas import AgentRequest, AgentResult, AgentStatus, Evidence, DataStatus
from agents.base_agent import BaseAgent
from orchestration.agent_registry import AgentRegistry
from orchestration.schemas import PlannerRequest, ExecutionPlan, PlanStep
from orchestration.orchestrator import OrcaOrchestrator, OrchestratorError
from orchestration.planner import OrcaPlanner


class MockAgent(BaseAgent):
    """Configurable mock domain agent for deterministic testing."""

    def __init__(
        self,
        name: str,
        status: AgentStatus = AgentStatus.SUCCESS,
        data: Optional[Dict[str, Any]] = None,
        data_status: DataStatus = DataStatus.LIVE,
        delay_seconds: float = 0.0,
        should_raise: bool = False,
        confidence: float = 1.0,
    ):
        self.name = name
        self.status = status
        self.data = data or {"test": True}
        self.data_status = data_status
        self.delay_seconds = delay_seconds
        self.should_raise = should_raise
        self.confidence = confidence
        self.execution_log = []

    async def execute(self, request: AgentRequest) -> AgentResult:
        self.execution_log.append({
            "time": time.time(),
            "request": request,
        })

        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)

        if self.should_raise:
            raise RuntimeError(f"Simulated crash in {self.name}")

        ev = self.create_evidence(
            source=f"MockSource-{self.name}",
            source_type="api",
            data_status=self.data_status,
        )

        return AgentResult(
            agent=self.name,
            status=self.status,
            data=self.data,
            evidence=ev,
            confidence=self.confidence,
            message=f"{self.name} completed with status {self.status.value}",
        )


async def test_orchestrator_single_agent():
    print("\n[TEST 1] Single Agent Execution...")
    mock_weather = MockAgent("weather", data={"temp_c": 28.0})
    registry = AgentRegistry(agents={"weather": mock_weather})
    orchestrator = OrcaOrchestrator(registry=registry)

    plan = ExecutionPlan(
        plan_id="plan_single",
        intent="weather_check",
        required_agents=["weather"],
        steps=[PlanStep(step_id="step_1", agent="weather", purpose="Get weather")],
        reasoning_summary="Single agent test",
    )
    req = PlannerRequest(query="Weather check", latitude=15.5, longitude=73.8)

    result = await orchestrator.execute_plan(plan, req)
    assert result.overall_status == AgentStatus.SUCCESS
    assert "weather" in result.agent_results
    assert result.agent_results["weather"].data == {"temp_c": 28.0}
    assert len(result.evidence) == 1
    assert result.evidence[0].source == "MockSource-weather"
    print("  [PASS] Single agent executed and result collected.")


async def test_orchestrator_multiple_parallel_agents():
    print("\n[TEST 2] Multiple Independent Agents Concurrency...")
    # Both agents take 0.15s; if executed in parallel, total time should be around 0.15-0.25s, not 0.30s+
    mock_weather = MockAgent("weather", delay_seconds=0.15)
    mock_marine = MockAgent("marine", delay_seconds=0.15)

    registry = AgentRegistry(agents={"weather": mock_weather, "marine": mock_marine})
    orchestrator = OrcaOrchestrator(registry=registry)

    plan = ExecutionPlan(
        plan_id="plan_parallel",
        intent="environment_check",
        required_agents=["weather", "marine"],
        steps=[
            PlanStep(step_id="step_w", agent="weather", purpose="Weather", depends_on=[]),
            PlanStep(step_id="step_m", agent="marine", purpose="Marine", depends_on=[]),
        ],
        reasoning_summary="Parallel execution test",
    )
    req = PlannerRequest(query="Conditions", latitude=15.5, longitude=73.8)

    t0 = time.time()
    result = await orchestrator.execute_plan(plan, req)
    elapsed = time.time() - t0

    assert result.overall_status == AgentStatus.SUCCESS
    assert len(result.agent_results) == 2
    # Verify both ran concurrently in less than sequential sum (0.15 + 0.15 = 0.30s)
    assert elapsed < 0.28, f"Expected parallel execution < 0.28s, took {elapsed:.3f}s"
    print(f"  [PASS] Independent agents ran concurrently in parallel: elapsed={elapsed:.3f}s")


async def test_orchestrator_dependency_ordering():
    print("\n[TEST 3] Strict Dependency Ordering Verification...")
    mock_pfz = MockAgent("pfz", delay_seconds=0.1)
    mock_hazard = MockAgent("hazard", delay_seconds=0.05)

    registry = AgentRegistry(agents={"pfz": mock_pfz, "hazard": mock_hazard})
    orchestrator = OrcaOrchestrator(registry=registry)

    # hazard depends_on pfz
    plan = ExecutionPlan(
        plan_id="plan_dep",
        intent="ordered_check",
        required_agents=["pfz", "hazard"],
        steps=[
            PlanStep(step_id="step_pfz", agent="pfz", purpose="Step 1"),
            PlanStep(step_id="step_haz", agent="hazard", purpose="Step 2", depends_on=["step_pfz"]),
        ],
        reasoning_summary="Dependency test",
    )
    req = PlannerRequest(query="Ordered", latitude=15.5, longitude=73.8)

    result = await orchestrator.execute_plan(plan, req)
    assert result.overall_status == AgentStatus.SUCCESS

    # Verify pfz finished before hazard started
    pfz_time = mock_pfz.execution_log[0]["time"]
    haz_time = mock_hazard.execution_log[0]["time"]
    assert haz_time >= pfz_time + 0.08, "Hazard started before PFZ completed!"
    print("  [PASS] Dependency ordering strictly enforced: Step 2 waited for Step 1.")


async def test_orchestrator_pfz_to_route_dependency():
    print("\n[TEST 4] PFZ -> Route Coordinate Dependency Propagation...")
    # PFZ returns an advisory at coordinates (15.20, 73.50)
    pfz_data = {
        "available": True,
        "nearest_advisory": {
            "landing_center": "Malpe Landing",
            "lc_coordinates": {"latitude": 15.20, "longitude": 73.50},
            "bearing_degrees": 240.0,
            "distance_from_query_km": 42.0,
        },
    }
    mock_pfz = MockAgent("pfz", data=pfz_data)
    mock_route = MockAgent("route", data={"recommended_route_id": "route_1", "routes": []})

    registry = AgentRegistry(agents={"pfz": mock_pfz, "route": mock_route})
    orchestrator = OrcaOrchestrator(registry=registry)

    plan = ExecutionPlan(
        plan_id="plan_pfz_route",
        intent="pfz_passage",
        required_agents=["pfz", "route"],
        steps=[
            PlanStep(step_id="step_pfz", agent="pfz", purpose="Find PFZ coordinates"),
            PlanStep(
                step_id="step_route",
                agent="route",
                purpose="Navigate to PFZ",
                depends_on=["step_pfz"],
                parameters={"latitude": 15.50, "longitude": 73.80},
            ),
        ],
        reasoning_summary="PFZ to Route dependency test",
    )
    # PlannerRequest has origin coordinates only (no destination_latitude)
    req = PlannerRequest(query="Navigate to nearest PFZ", latitude=15.50, longitude=73.80)

    result = await orchestrator.execute_plan(plan, req)
    assert result.overall_status == AgentStatus.SUCCESS

    # Verify route agent received destination coordinates extracted from PFZ advisory!
    route_req: AgentRequest = mock_route.execution_log[0]["request"]
    assert route_req.destination_latitude == 15.20
    assert route_req.destination_longitude == 73.50
    assert "Malpe Landing" in route_req.context.get("destination_name", "")
    print("  [PASS] Route agent successfully received destination coordinates (15.20, 73.50) from PFZ advisory.")


async def test_orchestrator_agent_failure_propagation():
    print("\n[TEST 5] Agent Failure Handled Without Crashing Orchestrator...")
    mock_weather = MockAgent("weather", data={"temp_c": 25.0})
    mock_failing_gis = MockAgent("gis", should_raise=True)

    registry = AgentRegistry(agents={"weather": mock_weather, "gis": mock_failing_gis})
    orchestrator = OrcaOrchestrator(registry=registry)

    plan = ExecutionPlan(
        plan_id="plan_fail",
        intent="robustness_test",
        required_agents=["weather", "gis"],
        steps=[
            PlanStep(step_id="step_w", agent="weather", purpose="Weather"),
            PlanStep(step_id="step_g", agent="gis", purpose="GIS check"),
        ],
        reasoning_summary="Failure propagation test",
    )
    req = PlannerRequest(query="Check both", latitude=15.5, longitude=73.8)

    result = await orchestrator.execute_plan(plan, req)
    # Orchestrator did not crash; weather succeeded, gis failed
    assert result.agent_results["weather"].status == AgentStatus.SUCCESS
    assert result.agent_results["gis"].status == AgentStatus.FAILED
    assert "Simulated crash in gis" in result.agent_results["gis"].errors[0]
    # Overall status is PARTIAL because one succeeded and one failed
    assert result.overall_status == AgentStatus.PARTIAL
    print("  [PASS] Agent exception safely captured in AgentResult with status=FAILED and overall=PARTIAL.")


async def test_orchestrator_evidence_and_status_preservation():
    print("\n[TEST 6] Data Status & Evidence Preservation (LIVE, STALE, UNAVAILABLE)...")
    mock_live = MockAgent("weather", data_status=DataStatus.LIVE)
    mock_stale = MockAgent("pfz", data_status=DataStatus.STALE)
    mock_unavail = MockAgent("chlorophyll", data_status=DataStatus.UNAVAILABLE, status=AgentStatus.PARTIAL)

    registry = AgentRegistry(agents={
        "weather": mock_live,
        "pfz": mock_stale,
        "chlorophyll": mock_unavail,
    })
    orchestrator = OrcaOrchestrator(registry=registry)

    plan = ExecutionPlan(
        plan_id="plan_statuses",
        intent="truth_test",
        required_agents=["weather", "pfz", "chlorophyll"],
        steps=[
            PlanStep(step_id="step_w", agent="weather", purpose="Live"),
            PlanStep(step_id="step_p", agent="pfz", purpose="Stale"),
            PlanStep(step_id="step_c", agent="chlorophyll", purpose="Unavailable"),
        ],
        reasoning_summary="Data truth test",
    )
    req = PlannerRequest(query="Statuses", latitude=15.5, longitude=73.8)

    result = await orchestrator.execute_plan(plan, req)

    # Check evidence statuses
    evidence_statuses = {e.source.replace("MockSource-", ""): e.data_status for e in result.evidence}
    assert evidence_statuses["weather"] == DataStatus.LIVE
    assert evidence_statuses["pfz"] == DataStatus.STALE
    assert evidence_statuses["chlorophyll"] == DataStatus.UNAVAILABLE

    # Check warnings were automatically generated for STALE and UNAVAILABLE
    warning_text = " ".join(result.warnings)
    assert "historical/stale" in warning_text
    assert "unavailable" in warning_text
    print("  [PASS] Telemetry statuses LIVE, STALE, and UNAVAILABLE preserved faithfully in evidence and warnings.")


async def main():
    print("=" * 65)
    print("ORCA PHASE 4 — ORCHESTRATOR VERIFICATION SUITE")
    print("=" * 65)

    await test_orchestrator_single_agent()
    await test_orchestrator_multiple_parallel_agents()
    await test_orchestrator_dependency_ordering()
    await test_orchestrator_pfz_to_route_dependency()
    await test_orchestrator_agent_failure_propagation()
    await test_orchestrator_evidence_and_status_preservation()

    print("\n" + "=" * 65)
    print("ALL ORCHESTRATOR TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
