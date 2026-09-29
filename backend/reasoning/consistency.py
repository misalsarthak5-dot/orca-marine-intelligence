"""
ORCA Cross-Agent Consistency & Conflict Analysis — Phase 5
Audits relationships and telemetry compatibility across domain agent results.
Detects contradictions, freshness gaps, unverified restrictions, and safety mismatches.
"""

from typing import Dict, Any, List, Optional
from core.schemas import AgentResult, AgentStatus, Evidence, DataStatus
from .schemas import Conflict, ConflictSeverity, ConsistencyReport, ReasoningContext


class ConsistencyChecker:
    """
    Evaluates cross-agent factual consistency without allowing an LLM to invent
    or hide contradictions. Enforces deterministic conflict severity.
    """

    def analyze(self, context: ReasoningContext) -> ConsistencyReport:
        """
        Execute comprehensive multi-agent consistency audit.

        Args:
            context: ReasoningContext containing all executed AgentResults and query metadata.

        Returns:
            ConsistencyReport containing detected conflicts, warnings, and overall consistency flag.
        """
        conflicts: List[Conflict] = []
        warnings: List[str] = []
        checked_agents = list(context.agent_results.keys())

        # 1. Hazard Contradiction Check (Example B)
        self._check_hazard_contradictions(context, conflicts)

        # 2. Freshness & Provenance Contradiction Check (Example E)
        self._check_freshness_contradictions(context, conflicts)

        # 3. GIS Boundary & Route Clearance Check (Example D)
        self._check_gis_route_clearance(context, conflicts)

        # 4. PFZ to Route Workflow Completeness Check (Example C)
        self._check_pfz_route_workflow(context, conflicts)

        # 5. Atmospheric vs Oceanographic Physics Plausibility Check (Example A & F)
        self._check_weather_marine_plausibility(context, conflicts)

        # 6. Synthesize consistency warnings
        for c in conflicts:
            warnings.append(f"[{c.severity.value}] {c.conflict_type}: {c.description}")

        is_consistent = not any(c.severity == ConflictSeverity.CRITICAL for c in conflicts)

        return ConsistencyReport(
            consistent=is_consistent,
            conflicts=conflicts,
            warnings=warnings,
            checked_agents=checked_agents,
        )

    def _check_hazard_contradictions(
        self,
        context: ReasoningContext,
        conflicts: List[Conflict],
    ) -> None:
        """
        Flag when HazardAgent identifies HIGH / CRITICAL alerts, squalls, or gales
        while the user intent or general conditions might otherwise suggest safe sailing.
        """
        hazard_res = context.agent_results.get("hazard")
        if not hazard_res or not hazard_res.data:
            return

        h_state = str(hazard_res.data.get("hazard_state", "")).strip().upper()
        alerts = hazard_res.data.get("alerts", [])

        is_high_hazard = (
            h_state in ("HIGH", "CRITICAL", "DANGER", "HIGH HAZARD")
            or any(a.get("severity", "").upper() in ("HIGH", "SEVERE", "EXTREME") for a in alerts)
        )

        if is_high_hazard:
            ev_list = [hazard_res.evidence] if hazard_res.evidence else []
            conflicts.append(Conflict(
                conflict_type="HAZARD_SAFETY_ALERT",
                agents=["hazard"],
                description=(
                    f"HazardAgent reports active HIGH severity marine hazard state ('{h_state}') "
                    f"with {len(alerts)} alert(s). Operational safety recommendations must prioritize this warning."
                ),
                severity=ConflictSeverity.CRITICAL,
                evidence=ev_list,
            ))

    def _check_freshness_contradictions(
        self,
        context: ReasoningContext,
        conflicts: List[Conflict],
    ) -> None:
        """
        Detect if stale/historical data is present when current/live conditions were expected,
        ensuring historical layers (e.g. INCOIS PFZ Landing Centres) are never presented as live.
        """
        for agent_name, res in context.agent_results.items():
            if res.evidence and res.evidence.data_status == DataStatus.STALE:
                obs_date = res.evidence.observed_at or "prior published snapshot"
                conflicts.append(Conflict(
                    conflict_type="FRESHNESS_STALE_DATA",
                    agents=[agent_name],
                    description=(
                        f"Telemetry from {agent_name} ({res.evidence.source}) is historical/stale "
                        f"(reference date: {obs_date}). It must not be presented as a current forecast."
                    ),
                    severity=ConflictSeverity.WARNING,
                    evidence=[res.evidence],
                ))

    def _check_gis_route_clearance(
        self,
        context: ReasoningContext,
        conflicts: List[Conflict],
    ) -> None:
        """
        Detect when RouteAgent completed route corridor calculations but GISAgent was UNAVAILABLE.
        Enforces rule: Never claim route is restriction-free when GIS is unavailable.
        """
        gis_res = context.agent_results.get("gis")
        route_res = context.agent_results.get("route")

        if route_res and route_res.status == AgentStatus.SUCCESS:
            gis_is_unavailable = (
                gis_res is None
                or gis_res.status in (AgentStatus.PARTIAL, AgentStatus.FAILED)
                or (gis_res.evidence and gis_res.evidence.data_status == DataStatus.UNAVAILABLE)
            )

            if gis_is_unavailable:
                ev_list = []
                if gis_res and gis_res.evidence:
                    ev_list.append(gis_res.evidence)
                if route_res.evidence:
                    ev_list.append(route_res.evidence)

                conflicts.append(Conflict(
                    conflict_type="UNVERIFIED_MARITIME_RESTRICTION",
                    agents=["gis", "route"],
                    description=(
                        "Candidate route corridors evaluated, but official maritime restriction-zone "
                        "verification was UNAVAILABLE. Passage clearance cannot be confirmed."
                    ),
                    severity=ConflictSeverity.WARNING,
                    evidence=ev_list,
                ))

    def _check_pfz_route_workflow(
        self,
        context: ReasoningContext,
        conflicts: List[Conflict],
    ) -> None:
        """
        Check completeness of PFZ -> Route workflow.
        If PFZ target was identified but RouteAgent failed or had missing coordinates.
        """
        pfz_res = context.agent_results.get("pfz")
        route_res = context.agent_results.get("route")

        if pfz_res and pfz_res.data and pfz_res.data.get("available"):
            if route_res and route_res.status == AgentStatus.FAILED:
                ev_list = []
                if pfz_res.evidence:
                    ev_list.append(pfz_res.evidence)
                if route_res.evidence:
                    ev_list.append(route_res.evidence)

                conflicts.append(Conflict(
                    conflict_type="INCOMPLETE_WORKFLOW",
                    agents=["pfz", "route"],
                    description=(
                        "INCOIS PFZ target advisory was identified, but route navigation analysis "
                        "failed or could not establish candidate corridors."
                    ),
                    severity=ConflictSeverity.WARNING,
                    evidence=ev_list,
                ))

    def _check_weather_marine_plausibility(
        self,
        context: ReasoningContext,
        conflicts: List[Conflict],
    ) -> None:
        """
        Verify physical alignment between atmospheric wind speed and ocean wave height.
        Complementary conditions produce no conflict (Example A).
        Extreme physical discordance produces an informative data audit warning (Example F).
        """
        weather_res = context.agent_results.get("weather")
        marine_res = context.agent_results.get("marine")

        if not weather_res or not marine_res:
            return
        if weather_res.status != AgentStatus.SUCCESS or marine_res.status != AgentStatus.SUCCESS:
            return

        w_curr = (weather_res.data or {}).get("current", {})
        m_curr = (marine_res.data or {}).get("current", {})

        wind_kts = w_curr.get("wind_speed_knots")
        wave_m = m_curr.get("wave_height_m")

        if wind_kts is not None and wave_m is not None:
            # Extreme anomaly: Severe gale wind (> 45 kts) alongside flat calm sea (< 0.3 m)
            if wind_kts >= 45.0 and wave_m < 0.3:
                ev_list = [e for e in [weather_res.evidence, marine_res.evidence] if e]
                conflicts.append(Conflict(
                    conflict_type="PHYSICAL_PLAUSIBILITY_ANOMALY",
                    agents=["weather", "marine"],
                    description=(
                        f"Atmospheric wind speed is severe ({wind_kts} kn), but significant wave height "
                        f"is recorded as calm ({wave_m} m). Possible sensor lag or sheltered harbor reading."
                    ),
                    severity=ConflictSeverity.WARNING,
                    evidence=ev_list,
                ))
            # Large swell with low local wind (common ocean swell from distant cyclone)
            elif wind_kts <= 6.0 and wave_m >= 3.5:
                ev_list = [e for e in [weather_res.evidence, marine_res.evidence] if e]
                conflicts.append(Conflict(
                    conflict_type="DISTANT_SWELL_DISSONANCE",
                    agents=["weather", "marine"],
                    description=(
                        f"Low local atmospheric winds ({wind_kts} kn), but high ocean waves ({wave_m} m) "
                        "indicating significant long-period swell propagating from a distant weather system."
                    ),
                    severity=ConflictSeverity.INFO,
                    evidence=ev_list,
                ))
