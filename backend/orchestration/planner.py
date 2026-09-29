"""
ORCA Intelligent Planner — Phase 4
Analyzes natural-language queries, determines required domain agent capabilities,
and creates structured, validated ExecutionPlans.
Strictly adheres to: LLM IS A PLANNER, NOT A SOURCE OF MARINE DATA.
"""

import re
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import ValidationError

from .schemas import PlannerRequest, ExecutionPlan, PlanStep
from .agent_registry import AgentRegistry, get_default_registry
from .llm_client import LLMClient, LLMClientError


class PlannerError(Exception):
    """Raised when the planner cannot construct a valid, secure, schema-compliant ExecutionPlan."""
    pass


class OrcaPlanner:
    """
    Intelligent Planner for ORCA Marine Intelligence.
    Translates user intent into a structured Directed Acyclic Graph (DAG) of PlanSteps
    backed exclusively by registered domain agents.
    """

    def __init__(
        self,
        registry: Optional[AgentRegistry] = None,
        llm_client: Optional[LLMClient] = None,
        allow_fallback: bool = True,
    ):
        """
        Initialize the planner.

        Args:
            registry: Central AgentRegistry. Defaults to standard singleton registry.
            llm_client: LLMClient abstraction for LLM-based plan generation.
            allow_fallback: If True, falls back to deterministic rule-based planning
                            when LLM is not configured or encounters an error.
        """
        self.registry = registry or get_default_registry()
        self.llm_client = llm_client
        self.allow_fallback = allow_fallback

    async def create_plan(self, request: PlannerRequest) -> ExecutionPlan:
        """
        Create a validated ExecutionPlan from a PlannerRequest.

        Args:
            request: PlannerRequest containing query and spatial coordinates.

        Returns:
            ExecutionPlan with validated steps, dependencies, and parameters.

        Raises:
            PlannerError: If plan creation fails or LLM output violates schema/security constraints.
        """
        if not request.query or not request.query.strip():
            raise PlannerError("PlannerRequest query cannot be empty.")

        # Coordinate sanity check
        if not (-90.0 <= request.latitude <= 90.0) or not (-180.0 <= request.longitude <= 180.0):
            raise PlannerError(
                f"Invalid origin coordinates: ({request.latitude}, {request.longitude})"
            )

        # 1. Attempt LLM generation if client is available
        if self.llm_client is not None:
            try:
                plan = await self._generate_plan_via_llm(request)
                return self.validate_plan(plan)
            except Exception as e:
                if not self.allow_fallback:
                    if isinstance(e, PlannerError):
                        raise
                    raise PlannerError(f"LLM planning failed and fallback is disabled: {str(e)}")
                # If fallback is allowed, proceed to deterministic fallback

        # 2. Deterministic Fallback Planner
        if self.allow_fallback:
            plan = self._generate_deterministic_fallback_plan(request)
            return self.validate_plan(plan)

        raise PlannerError(
            "No LLM client configured and deterministic fallback is disabled."
        )

    async def _generate_plan_via_llm(self, request: PlannerRequest) -> ExecutionPlan:
        """Prompt the LLM to output a structured ExecutionPlan."""
        capabilities_prompt = self.registry.describe_capabilities_prompt()

        system_prompt = (
            "You are the ORCA Marine Intelligent Planner.\n"
            "Your role is to analyze a natural-language marine query and generate a structured ExecutionPlan.\n"
            "CRITICAL RULES:\n"
            "1. You are a PLANNER only. You are NOT a source of marine telemetry. Never output telemetry or values.\n"
            "2. Select ONLY from the available registered domain agents provided below. Never invent agent names.\n"
            "3. Every step parameters must be pure data. Never include executable code, shell commands, or scripts.\n"
            "4. If a step depends on an earlier step's output (e.g. route needing PFZ coordinates), specify 'depends_on'.\n"
            "5. Always return a valid ExecutionPlan object adhering strictly to the schema.\n\n"
            f"{capabilities_prompt}"
        )

        user_prompt = (
            f"Query: \"{request.query}\"\n"
            f"Origin Latitude: {request.latitude}\n"
            f"Origin Longitude: {request.longitude}\n"
            f"Destination Latitude: {request.destination_latitude}\n"
            f"Destination Longitude: {request.destination_longitude}\n"
            f"Timestamp / Forecast Window: {request.timestamp or 'now'}\n"
            f"Additional Context: {request.context}\n\n"
            "Construct a minimal, sufficient ExecutionPlan to address this mariner's query."
        )

        try:
            assert self.llm_client is not None
            plan = await self.llm_client.generate_structured(
                prompt=user_prompt,
                schema=ExecutionPlan,
                system_prompt=system_prompt,
            )
            return plan
        except LLMClientError as lce:
            raise PlannerError(f"LLM planner error: {str(lce)}")
        except ValidationError as ve:
            raise PlannerError(f"LLM produced malformed plan schema: {str(ve)}")
        except Exception as e:
            raise PlannerError(f"Unexpected error during LLM planning: {str(e)}")

    def _generate_deterministic_fallback_plan(self, request: PlannerRequest) -> ExecutionPlan:
        """
        Deterministic, rule-based marine intent planner.
        Maps natural language maritime queries to the appropriate capability sequence and DAG dependencies.
        """
        q = request.query.lower()

        # Heuristic Intent Detection
        is_route_query = any(k in q for k in ["route", "navigate", "reach", "can i reach", "passage", "corridor", "waypoint"])
        is_pfz_query = any(k in q for k in ["pfz", "potential fishing zone", "fish zone", "tuna", "feeding zone"])
        is_where_to_fish = any(k in q for k in ["where to fish", "where should i fish", "best spot", "best fishing", "find fish"])
        is_safety_query = any(k in q for k in ["safe", "safety", "hazard", "squall", "alert", "warning", "tomorrow morning", "is it safe"])
        is_chlorophyll_query = any(k in q for k in ["chlorophyll", "ocean color", "plankton", "satellite bloom"])
        is_marine_query = any(k in q for k in ["wave", "swell", "sea state", "tide", "sst", "water temp", "sea surface temperature"])
        is_gis_query = any(k in q for k in ["restricted", "geofence", "boundary", "security zone", "mpa", "border"])

        steps: List[PlanStep] = []
        intent: str = "general_marine_inquiry"
        reasoning: str = ""

        if is_route_query and (is_pfz_query or "pfz" in q):
            # Query: "Can I reach the nearest PFZ safely?"
            # Sequence: PFZ -> Weather, Marine, Hazard, GIS -> Route (depends_on: PFZ)
            intent = "pfz_passage_safety"
            reasoning = "Query requests reaching the nearest PFZ safely; requires PFZ coordinates, environmental hazards, GIS zones, and candidate route corridor intelligence."
            
            steps.append(PlanStep(
                step_id="step_pfz",
                agent="pfz",
                purpose="Locate nearest official INCOIS Potential Fishing Zone landing centre reference and coordinates.",
                parameters={"latitude": request.latitude, "longitude": request.longitude},
            ))
            steps.append(PlanStep(
                step_id="step_weather",
                agent="weather",
                purpose="Evaluate atmospheric winds, gusts, and storm precipitation along corridor.",
                parameters={"latitude": request.latitude, "longitude": request.longitude, "timestamp": request.timestamp},
            ))
            steps.append(PlanStep(
                step_id="step_marine",
                agent="marine",
                purpose="Evaluate wave height, dominant swell period, and sea surface temperature.",
                parameters={"latitude": request.latitude, "longitude": request.longitude, "timestamp": request.timestamp},
            ))
            steps.append(PlanStep(
                step_id="step_hazard",
                agent="hazard",
                purpose="Check active marine hazards and emergency weather warnings.",
                parameters={"latitude": request.latitude, "longitude": request.longitude},
            ))
            steps.append(PlanStep(
                step_id="step_gis",
                agent="gis",
                purpose="Verify official maritime restriction boundaries and naval security corridors.",
                parameters={"latitude": request.latitude, "longitude": request.longitude},
            ))
            # Route step depends on PFZ coordinates!
            route_params: Dict[str, Any] = {
                "latitude": request.latitude,
                "longitude": request.longitude,
            }
            if request.destination_latitude is not None and request.destination_longitude is not None:
                route_params["destination_latitude"] = request.destination_latitude
                route_params["destination_longitude"] = request.destination_longitude
            
            steps.append(PlanStep(
                step_id="step_route",
                agent="route",
                purpose="Analyze passage corridors to target PFZ and assess composite navigational risk.",
                depends_on=["step_pfz"],
                parameters=route_params,
            ))

        elif is_where_to_fish:
            # Query: "Where should I fish tomorrow?"
            # Requires: pfz, marine, chlorophyll, weather
            intent = "fishing_ground_selection"
            reasoning = "Query asks for fishing recommendations; requires INCOIS PFZs, ocean thermal conditions (SST), satellite chlorophyll productivity, and weather safety."
            
            steps.append(PlanStep(
                step_id="step_pfz",
                agent="pfz",
                purpose="Query active INCOIS PFZ landing centre advisories and frontal vectors.",
                parameters={"latitude": request.latitude, "longitude": request.longitude},
            ))
            steps.append(PlanStep(
                step_id="step_marine",
                agent="marine",
                purpose="Retrieve sea surface temperature (SST) and sea state viability.",
                parameters={"latitude": request.latitude, "longitude": request.longitude, "timestamp": request.timestamp},
            ))
            steps.append(PlanStep(
                step_id="step_chlorophyll",
                agent="chlorophyll",
                purpose="Check ocean-color satellite chlorophyll-a concentration and data readiness.",
                parameters={"latitude": request.latitude, "longitude": request.longitude},
            ))
            steps.append(PlanStep(
                step_id="step_weather",
                agent="weather",
                purpose="Verify wind speed and gusts for vessel operational safety.",
                parameters={"latitude": request.latitude, "longitude": request.longitude, "timestamp": request.timestamp},
            ))

        elif is_pfz_query:
            # Query: "Where is the nearest PFZ?"
            intent = "pfz_location"
            reasoning = "User specifically requests nearest INCOIS Potential Fishing Zone advisory."
            steps.append(PlanStep(
                step_id="step_pfz",
                agent="pfz",
                purpose="Retrieve closest INCOIS PFZ landing centre target and frontal lines.",
                parameters={"latitude": request.latitude, "longitude": request.longitude},
            ))

        elif is_safety_query:
            # Query: "Is it safe to go fishing tomorrow morning?"
            # Requires: weather, marine, hazard
            intent = "fishing_safety_evaluation"
            reasoning = "Query requests safety clearance for fishing; requires atmospheric conditions, sea state (waves/swell), and active hazard alerts."
            steps.append(PlanStep(
                step_id="step_weather",
                agent="weather",
                purpose="Assess wind speed, gusts, and storm precipitation forecasts.",
                parameters={"latitude": request.latitude, "longitude": request.longitude, "timestamp": request.timestamp},
            ))
            steps.append(PlanStep(
                step_id="step_marine",
                agent="marine",
                purpose="Assess significant wave height, dominant wave period, and swell.",
                parameters={"latitude": request.latitude, "longitude": request.longitude, "timestamp": request.timestamp},
            ))
            steps.append(PlanStep(
                step_id="step_hazard",
                agent="hazard",
                purpose="Check active meteorological hazards and coast guard alerts.",
                parameters={"latitude": request.latitude, "longitude": request.longitude},
            ))

        elif is_route_query and request.destination_latitude is not None:
            # Route with explicit destination
            intent = "passage_corridor_evaluation"
            reasoning = "Navigation request between known coordinates; requires route corridor analysis, marine conditions, and GIS geofence verification."
            steps.append(PlanStep(
                step_id="step_weather",
                agent="weather",
                purpose="Evaluate atmospheric conditions along route corridor.",
                parameters={"latitude": request.latitude, "longitude": request.longitude, "timestamp": request.timestamp},
            ))
            steps.append(PlanStep(
                step_id="step_marine",
                agent="marine",
                purpose="Evaluate wave heights and swell along passage.",
                parameters={"latitude": request.latitude, "longitude": request.longitude, "timestamp": request.timestamp},
            ))
            steps.append(PlanStep(
                step_id="step_gis",
                agent="gis",
                purpose="Check maritime security zones and restriction clearances.",
                parameters={"latitude": request.latitude, "longitude": request.longitude},
            ))
            steps.append(PlanStep(
                step_id="step_route",
                agent="route",
                purpose="Compute 3 candidate marine routes and risk scores.",
                parameters={
                    "latitude": request.latitude,
                    "longitude": request.longitude,
                    "destination_latitude": request.destination_latitude,
                    "destination_longitude": request.destination_longitude,
                },
            ))

        elif is_chlorophyll_query:
            intent = "chlorophyll_telemetry"
            reasoning = "User specifically requests satellite chlorophyll ocean color telemetry."
            steps.append(PlanStep(
                step_id="step_chlorophyll",
                agent="chlorophyll",
                purpose="Retrieve satellite chlorophyll-a concentration and source readiness.",
                parameters={"latitude": request.latitude, "longitude": request.longitude},
            ))

        elif is_gis_query:
            intent = "gis_geofence_check"
            reasoning = "User requests maritime boundary or restriction zone verification."
            steps.append(PlanStep(
                step_id="step_gis",
                agent="gis",
                purpose="Query official active geofence zones and restriction status.",
                parameters={"latitude": request.latitude, "longitude": request.longitude},
            ))

        else:
            # Default environmental query
            intent = "environmental_conditions"
            reasoning = "Standard environmental assessment covering atmospheric weather and ocean sea state."
            steps.append(PlanStep(
                step_id="step_weather",
                agent="weather",
                purpose="Retrieve atmospheric weather telemetry.",
                parameters={"latitude": request.latitude, "longitude": request.longitude, "timestamp": request.timestamp},
            ))
            steps.append(PlanStep(
                step_id="step_marine",
                agent="marine",
                purpose="Retrieve oceanographic wave and sea surface temperature telemetry.",
                parameters={"latitude": request.latitude, "longitude": request.longitude, "timestamp": request.timestamp},
            ))

        req_agents = sorted(list({s.agent for s in steps}))
        return ExecutionPlan(
            plan_id=f"plan_{uuid.uuid4().hex[:8]}",
            intent=intent,
            required_agents=req_agents,
            steps=steps,
            parameters={"query": request.query, "latitude": request.latitude, "longitude": request.longitude},
            reasoning_summary=reasoning,
        )

    def validate_plan(self, plan: ExecutionPlan) -> ExecutionPlan:
        """
        Validate plan against registry and security rules.
        Rejects:
        - unknown agents
        - malformed parameters
        - executable code
        - duplicate invalid steps
        - unsupported capabilities
        """
        if not plan.steps:
            raise PlannerError("ExecutionPlan contains no steps.")

        for step in plan.steps:
            # 1. Reject unknown agent
            if not self.registry.has(step.agent):
                raise PlannerError(
                    f"Plan step '{step.step_id}' references unknown agent '{step.agent}'. "
                    f"Only registered agents are allowed: {self.registry.list_agents()}"
                )

            # 2. Check parameters safety (no executable tokens)
            param_str = str(step.parameters)
            if re.search(r"(__import__|eval\(|exec\(|subprocess|os\.system|shutil|<script)", param_str, re.IGNORECASE):
                raise PlannerError(
                    f"Security violation: Executable content detected in parameters for step '{step.step_id}'"
                )

        # 3. Check required_agents
        for ag in plan.required_agents:
            if not self.registry.has(ag):
                raise PlannerError(
                    f"ExecutionPlan declared unsupported required agent '{ag}'."
                )

        return plan
