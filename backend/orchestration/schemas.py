"""
ORCA Orchestration Schemas — Phase 4
Standardized contracts for Planner, ExecutionPlan, PlanStep, OrchestrationResult,
MapAction, and final synthesized OrcaResponse.
"""

import re
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

from core.schemas import AgentResult, AgentStatus, Evidence, DataStatus

# Disallowed dangerous code execution tokens in plans to prevent prompt injection payload execution
DANGEROUS_PATTERNS = re.compile(
    r"(__import__|eval\(|exec\(|subprocess|os\.system|shutil|popen|system\(|<script|javascript:)",
    re.IGNORECASE,
)


class PlannerRequest(BaseModel):
    """
    Standard input submitted to the ORCA Planner.
    Carries user natural-language query, spatial coordinates, and optional context.
    """
    model_config = ConfigDict(extra="ignore")

    query: str = Field(..., min_length=1, description="Natural-language marine query")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Vessel / target latitude in decimal degrees")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Vessel / target longitude in decimal degrees")
    destination_latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0, description="Destination latitude if relevant")
    destination_longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0, description="Destination longitude if relevant")
    timestamp: Optional[str] = Field(default=None, description="Time window context (e.g. 'now', 'tomorrow_morning')")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional maritime session context")


class PlanStep(BaseModel):
    """
    Atomic execution step in an ExecutionPlan.
    Contains strictly data parameters, never arbitrary executable code.
    """
    model_config = ConfigDict(extra="ignore")

    step_id: str = Field(..., description="Unique step identifier, e.g. 'step_1', 'step_2'")
    agent: str = Field(..., description="Canonical agent name (e.g. 'weather', 'pfz', 'route')")
    purpose: str = Field(..., description="Brief reason why this agent is required for the user query")
    depends_on: List[str] = Field(
        default_factory=list,
        description="List of step_ids that must complete before this step can execute"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Factual input parameters passed to the agent request"
    )

    @field_validator("parameters")
    @classmethod
    def validate_no_executable_code_in_parameters(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Reject executable code or dangerous scripting patterns in step parameters."""
        serialized = str(v)
        if DANGEROUS_PATTERNS.search(serialized):
            raise ValueError(
                "Executable code or dangerous injection tokens are strictly prohibited in plan parameters."
            )
        return v

    @field_validator("purpose")
    @classmethod
    def validate_purpose_safety(cls, v: str) -> str:
        """Reject injection tokens in step purpose."""
        if DANGEROUS_PATTERNS.search(v):
            raise ValueError("Dangerous scripting tokens detected in step purpose.")
        return v


class ExecutionPlan(BaseModel):
    """
    Structured execution plan created by the ORCA Planner.
    Defines intent, required capabilities, and a directed acyclic graph (DAG) of PlanSteps.
    """
    model_config = ConfigDict(extra="ignore")

    plan_id: str = Field(
        default_factory=lambda: f"plan_{uuid.uuid4().hex[:10]}",
        description="Unique identifier for this plan instance"
    )
    intent: str = Field(..., description="High-level classified intent (e.g. 'fishing_advisory', 'passage_safety')")
    required_agents: List[str] = Field(
        default_factory=list,
        description="List of canonical agent names needed for execution"
    )
    steps: List[PlanStep] = Field(..., min_length=1, description="Sequential or DAG steps to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Global plan-level parameters")
    reasoning_summary: str = Field(..., description="Explanation of why this plan satisfies the user query")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp when plan was generated"
    )

    @model_validator(mode="after")
    def validate_plan_dag_and_steps(self) -> "ExecutionPlan":
        """
        Validate:
        1. No duplicate step_ids.
        2. All depends_on references point to valid existing step_ids.
        3. No circular dependencies (DAG cycle detection).
        4. Step agents are consistent with required_agents.
        """
        step_ids = set()
        step_map: Dict[str, PlanStep] = {}

        for step in self.steps:
            if step.step_id in step_ids:
                raise ValueError(f"Duplicate step_id detected in execution plan: '{step.step_id}'")
            step_ids.add(step.step_id)
            step_map[step.step_id] = step

        # Validate dependency references
        for step in self.steps:
            for dep in step.depends_on:
                if dep not in step_ids:
                    raise ValueError(
                        f"Step '{step.step_id}' depends on non-existent step '{dep}'"
                    )
                if dep == step.step_id:
                    raise ValueError(f"Step '{step.step_id}' cannot depend on itself.")

        # Cycle detection (DFS)
        visited: Dict[str, int] = {}  # 0: unvisited, 1: visiting, 2: visited

        def has_cycle(curr_id: str) -> bool:
            visited[curr_id] = 1
            for neighbor in step_map[curr_id].depends_on:
                state = visited.get(neighbor, 0)
                if state == 1:
                    return True  # Cycle detected
                if state == 0 and has_cycle(neighbor):
                    return True
            visited[curr_id] = 2
            return False

        for sid in step_ids:
            if visited.get(sid, 0) == 0:
                if has_cycle(sid):
                    raise ValueError("Circular dependency detected in execution plan steps.")

        # Ensure required_agents matches or includes step agents
        step_agents = {step.agent for step in self.steps}
        if not self.required_agents:
            self.required_agents = sorted(list(step_agents))

        return self


class OrchestrationResult(BaseModel):
    """
    Standardized aggregated result produced after executing an ExecutionPlan.
    Preserves all individual AgentResults, evidence records, and data status.
    """
    model_config = ConfigDict(extra="ignore")

    query: str = Field(..., description="Original user query")
    plan: ExecutionPlan = Field(..., description="Executed plan")
    agent_results: Dict[str, AgentResult] = Field(
        default_factory=dict,
        description="Map of agent_name -> AgentResult preserving all domain outputs"
    )
    overall_status: AgentStatus = Field(
        default=AgentStatus.SUCCESS,
        description="Aggregate status: SUCCESS (all ok), PARTIAL (some partial/failed), FAILED (critical failure)"
    )
    evidence: List[Evidence] = Field(
        default_factory=list,
        description="Aggregated list of grounded evidence provenance records"
    )
    warnings: List[str] = Field(default_factory=list, description="Aggregated operational warnings")
    errors: List[str] = Field(default_factory=list, description="Aggregated errors encountered")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp when orchestration completed"
    )


class MapAction(BaseModel):
    """
    Backend-neutral structured map action for frontend visualization.
    Contains only factual coordinates and geometries derived from agent results.
    """
    model_config = ConfigDict(extra="ignore")

    action_type: str = Field(
        ...,
        description="Action type: 'show_origin', 'show_destination', 'show_pfz', 'show_route', 'fit_bounds'"
    )
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Factual coordinates or geometries from agent results"
    )


class OrcaResponse(BaseModel):
    """
    Final synthesized response returned to the caller.
    Combines the natural-language answer with full underlying factual provenance.
    """
    model_config = ConfigDict(extra="ignore")

    answer: str = Field(..., description="Natural-language response grounded strictly in agent results")
    intent: str = Field(..., description="Classified intent of the user query")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Deterministically aggregated confidence score")
    agent_results: Dict[str, AgentResult] = Field(
        default_factory=dict,
        description="Underlying domain agent results"
    )
    evidence: List[Evidence] = Field(
        default_factory=list,
        description="Aggregated evidence provenance records"
    )
    warnings: List[str] = Field(default_factory=list, description="Active operational warnings")
    map_actions: List[MapAction] = Field(
        default_factory=list,
        description="Backend-neutral structured map actions"
    )
    data_freshness: Dict[str, DataStatus] = Field(
        default_factory=dict,
        description="Telemetry freshness state per agent (LIVE, CACHED, STALE, UNAVAILABLE, ERROR)"
    )
    reasoning: Optional[Any] = Field(
        default=None,
        description="Collaborative multi-agent reasoning result (Phase 5)"
    )
    citations: List[Any] = Field(
        default_factory=list,
        description="Authoritative reference citations (Phase 6)"
    )
    evidence_context: Optional[Any] = Field(
        default=None,
        description="Contextual RAG evidence container (Phase 6)"
    )
