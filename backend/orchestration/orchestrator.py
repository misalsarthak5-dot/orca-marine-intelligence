"""
ORCA Orchestrator — Phase 4
Coordinates plan execution, enforces DAG dependencies, executes independent agents in parallel,
collects AgentResults, preserves evidence and telemetry freshness without data fabrication.
"""

import asyncio
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timezone

from core.schemas import AgentRequest, AgentResult, AgentStatus, Evidence, DataStatus
from .schemas import PlannerRequest, ExecutionPlan, PlanStep, OrchestrationResult
from .agent_registry import AgentRegistry, get_default_registry
from .planner import OrcaPlanner, PlannerError


class OrchestratorError(Exception):
    """Raised when plan orchestration cannot proceed due to critical validation or structural failure."""
    pass


class OrcaOrchestrator:
    """
    Central orchestration engine for ORCA Marine Intelligence.
    Coordinates between Planner, AgentRegistry, and Domain Agents.
    Enforces that agents are called exclusively, preserving complete telemetry provenance.
    """

    def __init__(
        self,
        registry: Optional[AgentRegistry] = None,
        planner: Optional[OrcaPlanner] = None,
    ):
        """
        Initialize Orchestrator.

        Args:
            registry: AgentRegistry containing the domain agents. Defaults to singleton registry.
            planner: OrcaPlanner instance. Defaults to OrcaPlanner using registry.
        """
        self.registry = registry or get_default_registry()
        self.planner = planner or OrcaPlanner(registry=self.registry)

    async def orchestrate(self, request: PlannerRequest) -> OrchestrationResult:
        """
        End-to-end orchestration workflow:
        1. Receive query and spatial context.
        2. Generate validated ExecutionPlan via Planner.
        3. Execute plan respecting dependencies and concurrency.
        4. Aggregate AgentResults, evidence, data statuses, and warnings.
        5. Return structured OrchestrationResult.

        Args:
            request: PlannerRequest with user query and coordinates.

        Returns:
            OrchestrationResult containing factual domain outputs.
        """
        # Step 1 & 2: Generate plan
        plan = await self.planner.create_plan(request)

        # Step 3, 4, 5: Execute plan and aggregate results
        return await self.execute_plan(plan, request)

    async def execute_plan(
        self,
        plan: ExecutionPlan,
        request: PlannerRequest,
    ) -> OrchestrationResult:
        """
        Execute an existing validated ExecutionPlan.

        Args:
            plan: Validated ExecutionPlan.
            request: Initial PlannerRequest context.

        Returns:
            OrchestrationResult containing all agent results and evidence.
        """
        # 1. Validate that all plan agents are in the registry
        for step in plan.steps:
            if not self.registry.has(step.agent):
                raise OrchestratorError(
                    f"Unknown agent '{step.agent}' in step '{step.step_id}'. "
                    f"Registered agents: {self.registry.list_agents()}"
                )

        step_map: Dict[str, PlanStep] = {s.step_id: s for s in plan.steps}
        completed_step_results: Dict[str, AgentResult] = {}
        completed_step_ids: Set[str] = set()

        unexecuted_step_ids = set(step_map.keys())

        # 2. Dependency Wave Execution (DAG Topological Concurrency)
        while unexecuted_step_ids:
            # Find all steps whose dependencies have fully completed
            ready_step_ids = [
                sid for sid in unexecuted_step_ids
                if all(dep in completed_step_ids for dep in step_map[sid].depends_on)
            ]

            if not ready_step_ids:
                # Cycle or unfulfillable dependency encountered
                missing_deps = {
                    sid: [dep for dep in step_map[sid].depends_on if dep not in completed_step_ids]
                    for sid in unexecuted_step_ids
                }
                raise OrchestratorError(
                    f"Deadlock in execution plan: unable to resolve dependencies for steps: {missing_deps}"
                )

            # Execute all ready steps concurrently in parallel
            tasks = [
                self._execute_single_step(
                    step=step_map[sid],
                    request=request,
                    prior_results=completed_step_results,
                )
                for sid in ready_step_ids
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process batch outputs
            for sid, result_or_exc in zip(ready_step_ids, batch_results):
                step = step_map[sid]
                if isinstance(result_or_exc, Exception):
                    # Convert unhandled exception into a safe, factual FAILED AgentResult
                    agent_res = AgentResult(
                        agent=step.agent,
                        status=AgentStatus.FAILED,
                        data=None,
                        evidence=None,
                        confidence=0.0,
                        message=f"Agent '{step.agent}' execution encountered an unexpected error: {str(result_or_exc)}",
                        errors=[str(result_or_exc)],
                    )
                else:
                    agent_res = result_or_exc

                completed_step_results[sid] = agent_res
                completed_step_ids.add(sid)
                unexecuted_step_ids.remove(sid)

        # 3. Aggregate results and evidence
        agent_results: Dict[str, AgentResult] = {}
        all_evidence: List[Evidence] = []
        all_warnings: List[str] = []
        all_errors: List[str] = []

        for step in plan.steps:
            res = completed_step_results[step.step_id]
            agent_results[step.agent] = res

            if res.evidence is not None:
                all_evidence.append(res.evidence)
                # Check for stale or unavailable evidence warnings
                if res.evidence.data_status == DataStatus.STALE:
                    all_warnings.append(
                        f"Data from {res.agent} ({res.evidence.source}) is historical/stale: observed at {res.evidence.observed_at or 'prior date'}."
                    )
                elif res.evidence.data_status == DataStatus.UNAVAILABLE:
                    all_warnings.append(
                        f"Telemetry from {res.agent} ({res.evidence.source}) is currently unavailable."
                    )
            elif res.status == AgentStatus.FAILED:
                all_warnings.append(f"Agent '{res.agent}' failed during plan execution.")

            if res.errors:
                all_errors.extend(res.errors)

        # 4. Compute overall status
        statuses = [res.status for res in agent_results.values()]
        if all(s == AgentStatus.SUCCESS for s in statuses):
            overall_status = AgentStatus.SUCCESS
        elif any(s == AgentStatus.SUCCESS for s in statuses):
            overall_status = AgentStatus.PARTIAL
        else:
            overall_status = AgentStatus.FAILED

        return OrchestrationResult(
            query=request.query,
            plan=plan,
            agent_results=agent_results,
            overall_status=overall_status,
            evidence=all_evidence,
            warnings=all_warnings,
            errors=all_errors,
        )

    async def _execute_single_step(
        self,
        step: PlanStep,
        request: PlannerRequest,
        prior_results: Dict[str, AgentResult],
    ) -> AgentResult:
        """
        Execute an individual step by resolving agent from registry and constructing AgentRequest.
        Injects dependent inputs if needed (e.g. PFZ target coordinates into Route step).
        """
        agent = self.registry.get(step.agent)

        # Base coordinates
        lat = step.parameters.get("latitude", request.latitude)
        lon = step.parameters.get("longitude", request.longitude)
        dest_lat = step.parameters.get("destination_latitude", request.destination_latitude)
        dest_lon = step.parameters.get("destination_longitude", request.destination_longitude)
        timestamp = step.parameters.get("timestamp", request.timestamp)
        context = {**request.context, **step.parameters.get("context", {})}

        # Dependency resolution (e.g., PFZ -> Route)
        if step.agent == "route":
            dest_lat, dest_lon, context = self._resolve_route_dependencies(
                step=step,
                dest_lat=dest_lat,
                dest_lon=dest_lon,
                context=context,
                prior_results=prior_results,
            )

            # Guard: If route agent still has no destination coordinates, return informative partial/failed
            if dest_lat is None or dest_lon is None:
                return AgentResult(
                    agent=step.agent,
                    status=AgentStatus.FAILED,
                    data=None,
                    evidence=None,
                    confidence=0.0,
                    message="Route planning cannot proceed: destination coordinates were not provided and could not be derived from upstream dependencies.",
                    errors=["Missing destination_latitude and destination_longitude"],
                )

        agent_req = AgentRequest(
            query=request.query,
            latitude=lat,
            longitude=lon,
            destination_latitude=dest_lat,
            destination_longitude=dest_lon,
            timestamp=timestamp,
            context=context,
        )

        try:
            return await agent.execute(agent_req)
        except Exception as e:
            return AgentResult(
                agent=step.agent,
                status=AgentStatus.FAILED,
                data=None,
                evidence=None,
                confidence=0.0,
                message=f"Agent '{step.agent}' raised exception: {str(e)}",
                errors=[str(e)],
            )

    def _resolve_route_dependencies(
        self,
        step: PlanStep,
        dest_lat: Optional[float],
        dest_lon: Optional[float],
        context: Dict[str, Any],
        prior_results: Dict[str, AgentResult],
    ) -> tuple[Optional[float], Optional[float], Dict[str, Any]]:
        """
        Helper to extract destination coordinates from prior step results (e.g. PFZ advisories).
        """
        # If destination already explicitly set, keep it
        if dest_lat is not None and dest_lon is not None:
            return dest_lat, dest_lon, context

        # Look for pfz in dependent steps
        for dep_sid in step.depends_on:
            prior_res = prior_results.get(dep_sid)
            if prior_res and prior_res.agent == "pfz" and prior_res.data:
                # 1. Try nearest advisory
                nearest = prior_res.data.get("nearest_advisory")
                if nearest and isinstance(nearest, dict):
                    lc_coords = nearest.get("lc_coordinates") or {}
                    n_lat = lc_coords.get("latitude")
                    n_lon = lc_coords.get("longitude")
                    if n_lat is not None and n_lon is not None:
                        dest_lat = float(n_lat)
                        dest_lon = float(n_lon)
                        center_name = nearest.get("landing_center", "INCOIS PFZ")
                        context["destination_name"] = f"{center_name} PFZ Target"
                        return dest_lat, dest_lon, context

                # 2. Try first active advisory
                advisories = prior_res.data.get("active_advisories") or []
                if advisories and isinstance(advisories[0], dict):
                    first_adv = advisories[0]
                    lc_coords = first_adv.get("lc_coordinates") or {}
                    n_lat = lc_coords.get("latitude")
                    n_lon = lc_coords.get("longitude")
                    if n_lat is not None and n_lon is not None:
                        dest_lat = float(n_lat)
                        dest_lon = float(n_lon)
                        center_name = first_adv.get("landing_center", "INCOIS PFZ")
                        context["destination_name"] = f"{center_name} PFZ Target"
                        return dest_lat, dest_lon, context

        return dest_lat, dest_lon, context
