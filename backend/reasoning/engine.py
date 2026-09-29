"""
ORCA Collaborative Multi-Agent Reasoning Engine — Phase 5
Interprets relationships between factual domain outputs, executes bounded reasoning passes,
traces evidence provenance, and produces deterministic, auditable decision conclusions.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from core.schemas import AgentResult, AgentStatus, Evidence, DataStatus
from .schemas import (
    ReasoningContext,
    ReasoningResult,
    DecisionFactor,
    ConsistencyReport,
    ConflictSeverity,
    ImpactLevel,
    RequirementLevel,
)
from .factors import DecisionFactorExtractor
from .consistency import ConsistencyChecker


class OperationalReasoningEngine:
    """
    Coordinates collaborative reasoning across ORCA domain agents.
    Enforces that:
    1. Agents communicate only indirectly through structured interpretation.
    2. Reasoning is deterministic, evidence-aware, and bounded (max 2 iterations).
    3. Existing safety logic is interpreted, never duplicated or arbitrarily overridden.
    """

    def __init__(
        self,
        factor_extractor: Optional[DecisionFactorExtractor] = None,
        consistency_checker: Optional[ConsistencyChecker] = None,
    ):
        self.factor_extractor = factor_extractor or DecisionFactorExtractor()
        self.consistency_checker = consistency_checker or ConsistencyChecker()

    async def reason(self, context: ReasoningContext) -> ReasoningResult:
        """
        Execute bounded operational reasoning over the provided ReasoningContext.

        Args:
            context: ReasoningContext with executed AgentResults and query metadata.

        Returns:
            ReasoningResult containing decision factors, consistency report, conclusions,
            uncertainties, follow-up actions, and deterministic confidence score.
        """
        iteration_count = 1

        # Pass 1: Extract factors and audit consistency
        factors = self.factor_extractor.extract_all(context.agent_results)
        consistency = self.consistency_checker.analyze(context)

        # Bounded iteration check (Max 2 passes)
        # If Pass 1 reveals missing destination or route refinement needed and data is present:
        if iteration_count < 2 and self._can_refine_workflow(context):
            iteration_count += 1
            # Re-evaluate factors and consistency post-refinement
            factors = self.factor_extractor.extract_all(context.agent_results)
            consistency = self.consistency_checker.analyze(context)

        # Determine capability requirement levels
        req_levels = self._classify_capability_requirements(context.intent)

        # Formulate deterministic operational conclusions
        conclusions = self._formulate_conclusions(context, factors, consistency, req_levels)

        # Extract explicit factual uncertainties
        uncertainties = self._extract_uncertainties(context, consistency)

        # Determine practical operational follow-up actions for the mariner
        followups = self._generate_followups(context, consistency, factors)

        # Calculate composite deterministic confidence
        confidence = self._calculate_reasoning_confidence(context, consistency, factors)

        # Construct lightweight reasoning graph
        graph = self._build_reasoning_graph(context, factors, conclusions, uncertainties)

        return ReasoningResult(
            decision_factors=factors,
            consistency=consistency,
            conclusions=conclusions,
            uncertainties=uncertainties,
            required_followups=followups,
            confidence=confidence,
            iteration_count=iteration_count,
            reasoning_graph=graph,
        )

    def _can_refine_workflow(self, context: ReasoningContext) -> bool:
        """Check if a bounded second reasoning pass can resolve an incomplete link."""
        pfz_res = context.agent_results.get("pfz")
        route_res = context.agent_results.get("route")
        # Example: PFZ succeeded with coordinates, but route was not initially configured
        if pfz_res and pfz_res.status == AgentStatus.SUCCESS and route_res is None:
            return False  # Agent execution is controlled by orchestrator, bounded reasoning does not spawn agents
        return False

    def _classify_capability_requirements(self, intent: str) -> Dict[str, RequirementLevel]:
        """Classify required vs supporting vs optional capabilities for the active intent."""
        intent_lower = intent.lower()

        if "safety" in intent_lower:
            return {
                "weather": RequirementLevel.REQUIRED,
                "marine": RequirementLevel.REQUIRED,
                "hazard": RequirementLevel.REQUIRED,
                "gis": RequirementLevel.SUPPORTING,
                "route": RequirementLevel.OPTIONAL,
                "pfz": RequirementLevel.OPTIONAL,
                "chlorophyll": RequirementLevel.OPTIONAL,
            }
        elif "pfz" in intent_lower or "fishing" in intent_lower:
            return {
                "pfz": RequirementLevel.REQUIRED,
                "marine": RequirementLevel.REQUIRED,
                "weather": RequirementLevel.REQUIRED,
                "chlorophyll": RequirementLevel.SUPPORTING,
                "hazard": RequirementLevel.SUPPORTING,
                "gis": RequirementLevel.SUPPORTING,
                "route": RequirementLevel.SUPPORTING,
            }
        elif "route" in intent_lower or "passage" in intent_lower or "navigation" in intent_lower:
            return {
                "route": RequirementLevel.REQUIRED,
                "marine": RequirementLevel.REQUIRED,
                "weather": RequirementLevel.REQUIRED,
                "gis": RequirementLevel.SUPPORTING,
                "hazard": RequirementLevel.SUPPORTING,
                "pfz": RequirementLevel.OPTIONAL,
                "chlorophyll": RequirementLevel.OPTIONAL,
            }

        return {
            "weather": RequirementLevel.REQUIRED,
            "marine": RequirementLevel.REQUIRED,
            "hazard": RequirementLevel.SUPPORTING,
            "pfz": RequirementLevel.OPTIONAL,
            "chlorophyll": RequirementLevel.OPTIONAL,
            "gis": RequirementLevel.OPTIONAL,
            "route": RequirementLevel.OPTIONAL,
        }

    def _formulate_conclusions(
        self,
        context: ReasoningContext,
        factors: List[DecisionFactor],
        consistency: ConsistencyReport,
        req_levels: Dict[str, RequirementLevel],
    ) -> List[str]:
        """
        Formulate deterministic conclusions derived directly from domain factors.
        Does not invent safety thresholds or override authoritative services.
        """
        conclusions: List[str] = []

        # 1. Critical Hazard Override
        critical_conflicts = [c for c in consistency.conflicts if c.severity == ConflictSeverity.CRITICAL]
        if critical_conflicts:
            for c in critical_conflicts:
                conclusions.append(f"SAFETY ADVISORY (CRITICAL): {c.description}")
            return conclusions

        # 2. Atmospheric & Oceanographic Environmental Assessment
        wind_factor = next((f for f in factors if f.factor == "Wind Speed"), None)
        wave_factor = next((f for f in factors if f.factor == "Significant Wave Height"), None)
        hazard_factor = next((f for f in factors if f.factor == "Marine Hazard State"), None)

        if wind_factor and wave_factor:
            unfavorable = any(f.impact == ImpactLevel.UNFAVORABLE for f in (wind_factor, wave_factor))
            caution = any(f.impact == ImpactLevel.CAUTION for f in (wind_factor, wave_factor))

            if unfavorable:
                conclusions.append(
                    f"Environmental conditions indicate rough sea state ({wave_factor.value}) "
                    f"and elevated winds ({wind_factor.value}). Transit not advised for small craft."
                )
            elif caution:
                conclusions.append(
                    f"Moderate coastal conditions observed ({wave_factor.value} waves, {wind_factor.value} winds). "
                    "Proceed with heightened vigilance and verify live harbor weather."
                )
            else:
                conclusions.append(
                    f"Atmospheric winds ({wind_factor.value}) and sea waves ({wave_factor.value}) "
                    "are within standard operational thresholds for coastal navigation."
                )
        elif wind_factor:
            if wind_factor.impact == ImpactLevel.UNFAVORABLE:
                conclusions.append(f"Elevated atmospheric winds observed ({wind_factor.value}). Small craft exercise caution.")
            else:
                conclusions.append(f"Atmospheric winds ({wind_factor.value}) are within standard operating limits.")
        elif wave_factor:
            if wave_factor.impact == ImpactLevel.UNFAVORABLE:
                conclusions.append(f"Elevated sea waves observed ({wave_factor.value}). Small craft exercise caution.")
            else:
                conclusions.append(f"Significant wave height ({wave_factor.value}) is within standard coastal operating limits.")

        if hazard_factor and hazard_factor.impact == ImpactLevel.FAVORABLE:
            conclusions.append("No active meteorological gale or squall hazard warnings identified for this coordinate.")

        if not conclusions and factors:
            conclusions.append(f"Evaluated {len(factors)} factual domain factor(s) for {context.intent.replace('_', ' ')}.")

        # 3. Fishery Intelligence (PFZ & Chlorophyll)
        pfz_factor = next((f for f in factors if f.factor == "PFZ Advisory Presence"), None)
        pfz_dist_factor = next((f for f in factors if f.factor == "PFZ Target Distance & Bearing"), None)
        pfz_fresh_factor = next((f for f in factors if f.factor == "PFZ Layer Snapshot Freshness"), None)
        chla_factor = next((f for f in factors if f.factor == "Chlorophyll-a Concentration"), None)

        if pfz_factor and "Identified" in str(pfz_factor.value):
            target_str = f"PFZ advisory located: {pfz_factor.value}"
            if pfz_dist_factor:
                target_str += f" ({pfz_dist_factor.value})"
            if pfz_fresh_factor:
                target_str += f". Note: Reference layer date is {pfz_fresh_factor.value}."
            conclusions.append(target_str)

            if chla_factor:
                conclusions.append(f"Primary productivity verified with satellite chlorophyll-a at {chla_factor.value}.")
        elif pfz_factor and "NO ACTIVE" in str(pfz_factor.value):
            conclusions.append("No active localized INCOIS PFZ landing centre advisories found within search radius.")

        # 4. Route Navigation & Geofence
        route_factor = next((f for f in factors if f.factor == "Recommended Navigation Corridor"), None)
        gis_factor = next((f for f in factors if f.factor == "Maritime Geofence Clearance"), None)

        if route_factor:
            conclusions.append(f"Passage corridors evaluated: {route_factor.value}.")
            if gis_factor and gis_factor.value == "UNAVAILABLE":
                conclusions.append(
                    "CAUTION: Official maritime boundary restriction polygons were unavailable from MSDI WFS. "
                    "Vessel must independently verify clearance from naval and marine protected zones."
                )

        return conclusions

    def _extract_uncertainties(
        self,
        context: ReasoningContext,
        consistency: ConsistencyReport,
    ) -> List[str]:
        """Extract and surface explicit factual data gaps and provenance caveats."""
        uncertainties: List[str] = []

        # Freshness caveats
        for agent_name, res in context.agent_results.items():
            if res.evidence and res.evidence.data_status == DataStatus.STALE:
                uncertainties.append(
                    f"PFZ telemetry from {res.evidence.source} is historical reference ({res.evidence.observed_at or 'prior date'}), not today's live forecast."
                )
            elif res.evidence and res.evidence.data_status == DataStatus.UNAVAILABLE:
                if agent_name == "chlorophyll":
                    uncertainties.append("Satellite chlorophyll-a concentration is currently unavailable from configured Earthdata / NASA sources.")
                elif agent_name == "gis":
                    uncertainties.append("Official maritime boundary geofence polygons could not be verified (MSDI source status: UNAVAILABLE).")
                else:
                    uncertainties.append(f"Telemetry from {agent_name} is currently unavailable.")
            elif res.status == AgentStatus.FAILED:
                uncertainties.append(f"Agent '{agent_name}' failed to retrieve data: {', '.join(res.errors)}")

        return uncertainties

    def _generate_followups(
        self,
        context: ReasoningContext,
        consistency: ConsistencyReport,
        factors: List[DecisionFactor],
    ) -> List[str]:
        """Generate practical, actionable mariner verifications."""
        followups: List[str] = [
            "Monitor VHF Coast Guard Emergency Channel 16 for live meteorological broadcasts.",
            "Verify life jacket readiness and distress beacon (EPIRB/DAT) operational status before departure.",
        ]

        if any(c.conflict_type == "UNVERIFIED_MARITIME_RESTRICTION" for c in consistency.conflicts):
            followups.append("Check official naval and port authority maritime notices (NOTAM/NOTMAR) for active firing ranges or restriction corridors.")

        if any(f.factor == "PFZ Advisory Presence" and "Identified" in str(f.value) for f in factors):
            followups.append("Cross-reference INCOIS frontal vector lines on the navigational map before finalizing bearing.")

        return followups

    def _calculate_reasoning_confidence(
        self,
        context: ReasoningContext,
        consistency: ConsistencyReport,
        factors: List[DecisionFactor],
    ) -> float:
        """
        Deterministic composite confidence calculation:
        Combines factor confidences and strictly penalizes for critical conflicts,
        stale layers, and unavailable telemetry.
        """
        if not factors:
            return 0.0

        mean_factor_conf = sum(f.confidence for f in factors) / len(factors)

        has_critical = any(c.severity == ConflictSeverity.CRITICAL for c in consistency.conflicts)
        has_warning = any(c.severity == ConflictSeverity.WARNING for c in consistency.conflicts)

        has_stale = any(
            res.evidence and res.evidence.data_status == DataStatus.STALE
            for res in context.agent_results.values()
        )
        has_unavailable = any(
            res.evidence and res.evidence.data_status == DataStatus.UNAVAILABLE
            for res in context.agent_results.values()
        )

        if has_critical:
            return round(min(mean_factor_conf, 0.35), 2)
        elif has_stale and has_unavailable:
            return round(min(mean_factor_conf, 0.60), 2)
        elif has_unavailable:
            return round(min(mean_factor_conf, 0.65), 2)
        elif has_stale or has_warning:
            return round(min(mean_factor_conf, 0.75), 2)

        return round(min(1.0, max(0.0, mean_factor_conf)), 2)

    def _build_reasoning_graph(
        self,
        context: ReasoningContext,
        factors: List[DecisionFactor],
        conclusions: List[str],
        uncertainties: List[str],
    ) -> Dict[str, Any]:
        """
        Build lightweight, auditable structured reasoning graph representation.
        Pure JSON schema, no graph database dependency.
        """
        nodes = [
            {"id": "query", "type": "USER_QUERY", "label": context.query},
            {"id": "intent", "type": "INTENT", "label": context.intent},
        ]
        edges = [
            {"source": "query", "target": "intent", "relation": "CLASSIFIED_AS"}
        ]

        # Add agent nodes and links
        for agent_name in context.agent_results.keys():
            nodes.append({"id": f"agent_{agent_name}", "type": "DOMAIN_AGENT", "label": agent_name})
            edges.append({"source": "intent", "target": f"agent_{agent_name}", "relation": "INVOKED"})

        # Add factor nodes and links
        for idx, f in enumerate(factors):
            fid = f"factor_{idx}"
            nodes.append({
                "id": fid,
                "type": "DECISION_FACTOR",
                "label": f.factor,
                "value": str(f.value),
                "impact": f.impact.value,
            })
            edges.append({"source": f"agent_{f.source_agent}", "target": fid, "relation": "PRODUCED"})

        # Add conclusion nodes and links
        for idx, c in enumerate(conclusions):
            cid = f"conclusion_{idx}"
            nodes.append({"id": cid, "type": "CONCLUSION", "label": c})
            edges.append({"source": "intent", "target": cid, "relation": "INFERRED"})

        return {
            "nodes": nodes,
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
        }
