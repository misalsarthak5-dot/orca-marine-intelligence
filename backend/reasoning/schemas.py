"""
ORCA Collaborative Multi-Agent Reasoning Schemas — Phase 5
Defines structured contracts for cross-agent interpretation, decision factors,
conflict detection, consistency analysis, evidence traceability, and operational reasoning.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

from core.schemas import AgentResult, Evidence, DataStatus, AgentStatus
from orchestration.schemas import ExecutionPlan


class ConflictSeverity(str, Enum):
    """
    Deterministic severity level for cross-agent contradictions.
    Never decided arbitrarily by an LLM.
    """
    INFO = "INFO"          # Complementary information or minor non-blocking variance
    WARNING = "WARNING"    # Freshness mismatch, unverified boundaries, or missing supporting data
    CRITICAL = "CRITICAL"  # Active safety hazard contradictions, severe squalls, or blocking failures


class ImpactLevel(str, Enum):
    """Impact of an isolated decision factor on operational feasibility."""
    FAVORABLE = "FAVORABLE"
    UNFAVORABLE = "UNFAVORABLE"
    CAUTION = "CAUTION"
    NEUTRAL = "NEUTRAL"
    CRITICAL = "CRITICAL"


class FactorCategory(str, Enum):
    """Classification domain for decision factors."""
    ATMOSPHERIC = "ATMOSPHERIC"
    OCEANOGRAPHIC = "OCEANOGRAPHIC"
    HAZARD = "HAZARD"
    FISHERY = "FISHERY"
    RESTRICTION_GEOFENCE = "RESTRICTION_GEOFENCE"
    NAVIGATION_ROUTE = "NAVIGATION_ROUTE"
    OPERATIONAL = "OPERATIONAL"


class RequirementLevel(str, Enum):
    """Significance level of an agent capability relative to the active query intent."""
    REQUIRED = "REQUIRED"      # Mandatory; failure precludes confident operational clearance
    SUPPORTING = "SUPPORTING"  # Valuable context; failure generates warning without blocking
    OPTIONAL = "OPTIONAL"      # Auxiliary telemetry; failure has minimal impact


class DecisionFactor(BaseModel):
    """
    Grounded, factual decision factor extracted from an AgentResult.
    Must be strictly traceable back to source Evidence and DataStatus.
    """
    model_config = ConfigDict(extra="ignore")

    factor: str = Field(..., description="Canonical name of factor, e.g. 'Wind Speed', 'Significant Wave Height'")
    category: FactorCategory = Field(..., description="Domain category")
    value: Any = Field(..., description="Factual value or state (number, string, or boolean)")
    source_agent: str = Field(..., description="Canonical name of the domain agent providing this factor")
    evidence: Optional[Evidence] = Field(default=None, description="Direct provenance metadata link")
    impact: ImpactLevel = Field(default=ImpactLevel.NEUTRAL, description="Feasibility impact")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence of this individual factor")
    explanation: Optional[str] = Field(default=None, description="Deterministic explanation of why this factor matters")


class Conflict(BaseModel):
    """
    Detected contradiction, incompatible state, or freshness gap across domain results.
    """
    model_config = ConfigDict(extra="ignore")

    conflict_type: str = Field(..., description="Identifier (e.g. 'HAZARD_CONTRADICTION', 'FRESHNESS_MISMATCH')")
    agents: List[str] = Field(..., description="Names of conflicting or discordant agents")
    description: str = Field(..., description="Factual explanation of the contradiction")
    severity: ConflictSeverity = Field(..., description="Deterministic conflict severity")
    evidence: List[Evidence] = Field(default_factory=list, description="Associated evidence records")


class ConsistencyReport(BaseModel):
    """
    Cross-agent consistency evaluation summary.
    """
    model_config = ConfigDict(extra="ignore")

    consistent: bool = Field(default=True, description="True if no CRITICAL conflicts were detected")
    conflicts: List[Conflict] = Field(default_factory=list, description="Identified conflicts")
    warnings: List[str] = Field(default_factory=list, description="Cross-agent operational warnings")
    checked_agents: List[str] = Field(default_factory=list, description="Agents evaluated for consistency")


class ReasoningContext(BaseModel):
    """
    Input context provided to the ORCA Collaborative Reasoning Engine.
    """
    model_config = ConfigDict(extra="ignore")

    query: str = Field(..., description="Original user query")
    intent: str = Field(..., description="Detected user intent")
    agent_results: Dict[str, AgentResult] = Field(default_factory=dict, description="Domain agent outputs")
    evidence: List[Evidence] = Field(default_factory=list, description="Grounded provenance records")
    plan: Optional[ExecutionPlan] = Field(default=None, description="Execution plan from Phase 4")
    timestamp: Optional[str] = Field(default=None, description="Temporal window")
    evidence_context: Optional[Any] = Field(default=None, description="Contextual RAG evidence (Phase 6)")


class ReasoningResult(BaseModel):
    """
    Comprehensive, structured outcome of collaborative multi-agent reasoning.
    Carries extracted decision factors, consistency audit, conclusions, and uncertainties.
    """
    model_config = ConfigDict(extra="ignore")

    decision_factors: List[DecisionFactor] = Field(
        default_factory=list,
        description="Factual decision factors extracted from agent results"
    )
    consistency: ConsistencyReport = Field(
        ...,
        description="Cross-agent conflict and consistency analysis"
    )
    conclusions: List[str] = Field(
        default_factory=list,
        description="Deterministic operational conclusions derived from factors"
    )
    uncertainties: List[str] = Field(
        default_factory=list,
        description="Explicitly surfaced data gaps, stale layers, or unverified boundaries"
    )
    required_followups: List[str] = Field(
        default_factory=list,
        description="Practical safety or navigational verification checks for the mariner"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Deterministic composite confidence"
    )
    iteration_count: int = Field(
        default=1,
        ge=1,
        le=2,
        description="Number of bounded reasoning refinement passes executed (max 2)"
    )
    reasoning_graph: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Structured representation of cross-agent reasoning relationships"
    )
    evidence_context: Optional[Any] = Field(
        default=None,
        description="Contextual RAG evidence and citations (Phase 6)"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 creation timestamp"
    )
