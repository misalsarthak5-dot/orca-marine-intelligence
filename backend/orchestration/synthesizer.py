"""
ORCA Synthesizer — Phase 4
Grounds natural-language synthesis strictly in factual AgentResults and Evidence.
Enforces the core rule:
THE LLM IS A PLANNER AND SYNTHESIZER.
THE LLM IS NOT A SOURCE OF MARINE DATA.
Derives confidence deterministically and provides structured map actions.
"""

from typing import Dict, Any, List, Optional
from core.schemas import AgentResult, AgentStatus, Evidence, DataStatus
from .schemas import PlannerRequest, OrchestrationResult, OrcaResponse, MapAction
from .llm_client import LLMClient, LLMClientError


class OrcaSynthesizer:
    """
    Synthesizes conversational responses strictly grounded in executed AgentResults.
    Never hallucinates missing telemetry, preserves uncertainty, and generates
    backend-neutral structured map actions.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize the synthesizer.

        Args:
            llm_client: LLMClient abstraction. If None or on failure, uses deterministic synthesis.
        """
        self.llm_client = llm_client

    async def synthesize(
        self,
        result: OrchestrationResult,
        request: PlannerRequest,
        reasoning_result: Optional[Any] = None,
        evidence_context: Optional[Any] = None,
    ) -> OrcaResponse:
        """
        Produce a validated OrcaResponse with natural-language synthesis,
        deterministic confidence, preserved evidence, structured map actions,
        collaborative multi-agent reasoning (Phase 5), and authoritative citations (Phase 6).

        Args:
            result: OrchestrationResult with all executed agent results.
            request: Initial PlannerRequest.
            reasoning_result: Optional Phase 5 ReasoningResult.
            evidence_context: Optional Phase 6 EvidenceContext.

        Returns:
            OrcaResponse ready for frontend consumption or decision support.
        """
        # Resolve evidence_context from reasoning_result if not passed explicitly
        if evidence_context is None and reasoning_result is not None:
            evidence_context = getattr(reasoning_result, "evidence_context", None)

        # 1. Collect data freshness states across all agents
        data_freshness: Dict[str, DataStatus] = {}
        for agent_name, agent_res in result.agent_results.items():
            if agent_res.evidence:
                data_freshness[agent_name] = agent_res.evidence.data_status
            elif agent_res.status == AgentStatus.FAILED:
                data_freshness[agent_name] = DataStatus.ERROR
            else:
                data_freshness[agent_name] = DataStatus.LIVE

        # 2. Deterministically compute composite confidence score (or adopt reasoning confidence)
        if reasoning_result is not None and hasattr(reasoning_result, "confidence"):
            confidence = reasoning_result.confidence
        else:
            confidence = self._calculate_deterministic_confidence(result, data_freshness)

        # 3. Generate structured backend-neutral map actions
        map_actions = self._generate_map_actions(result, request)

        # 4. Merge warnings from reasoning if available
        combined_warnings = list(result.warnings)
        if reasoning_result is not None and hasattr(reasoning_result, "consistency"):
            for w in reasoning_result.consistency.warnings:
                if w not in combined_warnings:
                    combined_warnings.append(w)

        # 5. Extract citations if present
        citations: List[Any] = []
        if evidence_context is not None and hasattr(evidence_context, "citations"):
            citations = list(evidence_context.citations)

        # 6. Generate grounded natural-language answer
        answer = await self._generate_grounded_answer(
            result, request, data_freshness, reasoning_result=reasoning_result, evidence_context=evidence_context
        )

        return OrcaResponse(
            answer=answer,
            intent=result.plan.intent,
            confidence=confidence,
            agent_results=result.agent_results,
            evidence=result.evidence,
            warnings=combined_warnings,
            map_actions=map_actions,
            data_freshness=data_freshness,
            reasoning=reasoning_result,
            citations=citations,
            evidence_context=evidence_context,
        )

    def _calculate_deterministic_confidence(
        self,
        result: OrchestrationResult,
        data_freshness: Dict[str, DataStatus],
    ) -> float:
        """
        Deterministic confidence calculation:
        - Base: Mean of individual agent confidences.
        - Penalized if critical agents failed or data is stale/unavailable.
        - Never manufactured or guessed by the LLM.
        """
        if not result.agent_results:
            return 0.0

        confidences = [res.confidence for res in result.agent_results.values()]
        mean_conf = sum(confidences) / len(confidences)

        # Apply strict caps based on truth status
        has_failed = any(res.status == AgentStatus.FAILED for res in result.agent_results.values())
        has_unavailable = any(status == DataStatus.UNAVAILABLE for status in data_freshness.values())
        has_stale = any(status == DataStatus.STALE for status in data_freshness.values())

        if has_failed:
            # Significant failure in required capability
            return round(min(mean_conf, 0.35), 2)
        elif has_unavailable and has_stale:
            return round(min(mean_conf, 0.60), 2)
        elif has_unavailable:
            return round(min(mean_conf, 0.65), 2)
        elif has_stale:
            return round(min(mean_conf, 0.75), 2)

        return round(min(1.0, max(0.0, mean_conf)), 2)

    def _generate_map_actions(
        self,
        result: OrchestrationResult,
        request: PlannerRequest,
    ) -> List[MapAction]:
        """
        Produce backend-neutral map actions from actual agent results.
        Only uses factual coordinates returned by agents; never fabricates coordinates.
        """
        actions: List[MapAction] = []
        all_lats: List[float] = [request.latitude]
        all_lons: List[float] = [request.longitude]

        # 1. Show Origin / Vessel Location
        actions.append(MapAction(
            action_type="show_origin",
            data={
                "latitude": request.latitude,
                "longitude": request.longitude,
                "label": "Vessel / Assessment Position",
            },
        ))

        # 2. Show PFZ if present in results
        pfz_res = result.agent_results.get("pfz")
        if pfz_res and pfz_res.data:
            nearest = pfz_res.data.get("nearest_advisory")
            if nearest and isinstance(nearest, dict):
                coords = nearest.get("lc_coordinates") or {}
                if "latitude" in coords and "longitude" in coords:
                    all_lats.append(float(coords["latitude"]))
                    all_lons.append(float(coords["longitude"]))
                    actions.append(MapAction(
                        action_type="show_pfz",
                        data={
                            "landing_center": nearest.get("landing_center"),
                            "coordinates": coords,
                            "bearing_degrees": nearest.get("bearing_degrees"),
                            "distance_from_query_km": nearest.get("distance_from_query_km"),
                            "advisory_distance_from_km": nearest.get("advisory_distance_from_km"),
                            "advisory_distance_to_km": nearest.get("advisory_distance_to_km"),
                            "reference_layer_date": nearest.get("reference_layer_date"),
                        },
                    ))

        # 3. Show Route if present in results
        route_res = result.agent_results.get("route")
        if route_res and route_res.data:
            routes = route_res.data.get("routes") or []
            rec_id = route_res.data.get("recommended_route_id")
            dest_coords = route_res.data.get("destination_coordinates") or {}
            if "latitude" in dest_coords and "longitude" in dest_coords:
                all_lats.append(float(dest_coords["latitude"]))
                all_lons.append(float(dest_coords["longitude"]))
                actions.append(MapAction(
                    action_type="show_destination",
                    data={
                        "latitude": float(dest_coords["latitude"]),
                        "longitude": float(dest_coords["longitude"]),
                        "label": route_res.data.get("destination_name", "Target Destination"),
                    },
                ))

            if routes:
                actions.append(MapAction(
                    action_type="show_route",
                    data={
                        "recommended_route_id": rec_id,
                        "routes_count": len(routes),
                        "routes_summary": [
                            {
                                "id": r.get("id"),
                                "name": r.get("name"),
                                "distance_nm": r.get("distance_nm"),
                                "risk_score": r.get("risk_score"),
                                "risk_level": r.get("risk_level"),
                            }
                            for r in routes
                        ],
                    },
                ))

        # 4. Show explicit destination from request if present and not already added
        if request.destination_latitude is not None and request.destination_longitude is not None:
            if not any(a.action_type == "show_destination" for a in actions):
                all_lats.append(request.destination_latitude)
                all_lons.append(request.destination_longitude)
                actions.append(MapAction(
                    action_type="show_destination",
                    data={
                        "latitude": request.destination_latitude,
                        "longitude": request.destination_longitude,
                        "label": "Requested Destination",
                    },
                ))

        # 5. Fit Bounds enclosing all displayed points
        if len(all_lats) > 1:
            actions.append(MapAction(
                action_type="fit_bounds",
                data={
                    "southwest": [min(all_lats), min(all_lons)],
                    "northeast": [max(all_lats), max(all_lons)],
                },
            ))

        return actions

    async def _generate_grounded_answer(
        self,
        result: OrchestrationResult,
        request: PlannerRequest,
        data_freshness: Dict[str, DataStatus],
        reasoning_result: Optional[Any] = None,
        evidence_context: Optional[Any] = None,
    ) -> str:
        """
        Synthesize the final answer using the LLM with strict factual grounding,
        falling back to deterministic synthesis if the LLM is absent or encounters errors.
        """
        # Attempt LLM synthesis if client is available
        if self.llm_client is not None:
            try:
                return await self._generate_llm_synthesis(
                    result, request, data_freshness, reasoning_result=reasoning_result, evidence_context=evidence_context
                )
            except Exception:
                # LLM synthesis failure -> safe fallback response preserving factual results
                pass

        return self._generate_deterministic_synthesis(
            result, request, data_freshness, reasoning_result=reasoning_result, evidence_context=evidence_context
        )

    async def _generate_llm_synthesis(
        self,
        result: OrchestrationResult,
        request: PlannerRequest,
        data_freshness: Dict[str, DataStatus],
        reasoning_result: Optional[Any] = None,
        evidence_context: Optional[Any] = None,
    ) -> str:
        """Prompt the LLM with strict grounding constraints."""
        system_prompt = (
            "You are the ORCA Marine Intelligent Decision Support Synthesizer.\n"
            "Your task is to synthesize a professional, natural-language maritime brief answering the mariner's query.\n\n"
            "CRITICAL OPERATIONAL RULES:\n"
            "1. You are a SYNTHESIZER, NOT A DATA SOURCE. You must ONLY use the facts provided in the AGENT RESULTS and REASONING FACTORS below.\n"
            "2. DO NOT invent, hallucinate, extrapolate, or fabricate any numbers, coordinates, wind speeds, wave heights, SST, or distances.\n"
            "3. RAG/Contextual Reference material is for explanatory background only. NEVER use reference documents to replace or fabricate live telemetry numbers.\n"
            "4. If an agent returned UNAVAILABLE or FAILED, explicitly state that the information is currently unavailable from official sources.\n"
            "5. If PFZ or other telemetry has a historical reference date or is STALE, inform the mariner clearly of that provenance.\n"
            "6. If GIS is UNAVAILABLE, state that official maritime boundary restriction clearance could not be verified.\n"
            "7. Separate operational recommendations from uncertainty disclosures. Be clear, concise, and nautical."
        )

        facts_summary = self._format_agent_results_for_prompt(result, data_freshness)
        reasoning_summary = ""
        if reasoning_result is not None:
            reasoning_summary = self._format_reasoning_for_prompt(reasoning_result)

        ref_summary = ""
        if evidence_context is not None and hasattr(evidence_context, "citations") and evidence_context.citations:
            ref_lines = ["\nAUTHORITATIVE BACKGROUND REFERENCES (For context only — do NOT substitute live numbers):"]
            for c in evidence_context.citations:
                ref_lines.append(f"- {c.title} ({c.publisher}): \"{c.relevant_chunk[:200]}\"")
            ref_summary = "\n".join(ref_lines)

        user_prompt = (
            f"Mariner Query: \"{request.query}\"\n"
            f"Vessel Position: ({request.latitude:.4f}, {request.longitude:.4f})\n"
            f"Detected Intent: {result.plan.intent}\n\n"
            f"VERIFIED AGENT RESULTS:\n{facts_summary}\n"
            f"{reasoning_summary}\n"
            f"{ref_summary}\n\n"
            "Synthesize a clear, direct answer to the mariner's query based strictly on the verified facts above."
        )

        assert self.llm_client is not None
        return await self.llm_client.generate_text(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=800,
        )

    def _format_agent_results_for_prompt(
        self,
        result: OrchestrationResult,
        data_freshness: Dict[str, DataStatus],
    ) -> str:
        """Format agent results into structured factual blocks for the LLM synthesizer."""
        lines = []
        for name, agent_res in result.agent_results.items():
            freshness = data_freshness.get(name, DataStatus.LIVE).value
            status = agent_res.status.value
            lines.append(f"### AGENT: {name.upper()} [Status: {status} | Freshness: {freshness} | Confidence: {agent_res.confidence}]")
            if agent_res.message:
                lines.append(f"Summary: {agent_res.message}")
            if agent_res.errors:
                lines.append(f"Errors: {', '.join(agent_res.errors)}")
            if agent_res.evidence:
                lines.append(
                    f"Evidence: source='{agent_res.evidence.source}', observed_at='{agent_res.evidence.observed_at or 'current'}'"
                )
            if agent_res.data:
                # Key domain highlights
                if name == "weather":
                    curr = agent_res.data.get("current", {})
                    lines.append(f"Telemetry: temp={curr.get('temperature_c')}C, wind={curr.get('wind_speed_knots')} kn, gusts={curr.get('wind_gusts_knots')} kn, dir={curr.get('wind_direction_compass')}")
                elif name == "marine":
                    curr = agent_res.data.get("current", {})
                    lines.append(f"Telemetry: wave_height={curr.get('wave_height_m')}m, swell_height={curr.get('swell_wave_height_m')}m, period={curr.get('dominant_wave_period_s')}s, sst={curr.get('sea_surface_temperature_c')}C")
                elif name == "chlorophyll":
                    lines.append(f"Telemetry: available={agent_res.data.get('available')}, chlorophyll_a={agent_res.data.get('chlorophyll_a_mg_m3')}, reason='{agent_res.data.get('reason', '')}'")
                elif name == "pfz":
                    lines.append(f"Telemetry: available={agent_res.data.get('available')}, total_active={agent_res.data.get('total_active_advisories_found')}")
                    nearest = agent_res.data.get("nearest_advisory")
                    if nearest and isinstance(nearest, dict):
                        lines.append(f"Nearest Advisory: {nearest.get('landing_center')} ({nearest.get('distance_from_query_km')} km), bearing {nearest.get('bearing_degrees')} deg, reference_date='{nearest.get('reference_layer_date')}'")
                elif name == "hazard":
                    lines.append(f"Telemetry: state='{agent_res.data.get('hazard_state')}', alerts_count={len(agent_res.data.get('alerts', []))}")
                elif name == "gis":
                    lines.append(f"Telemetry: status='{agent_res.data.get('restriction_status', agent_res.data.get('status'))}', zones_count={len(agent_res.data.get('zones', []))}")
                elif name == "route":
                    lines.append(f"Telemetry: rec_route='{agent_res.data.get('recommended_route_id')}', total_routes={len(agent_res.data.get('routes', []))}")
            lines.append("")
        return "\n".join(lines)

    def _format_reasoning_for_prompt(self, reasoning_result: Any) -> str:
        """Format Phase 5 collaborative reasoning results for LLM synthesis prompt."""
        lines = ["\n### COLLABORATIVE REASONING & DECISION FACTORS (PHASE 5):"]
        if hasattr(reasoning_result, "decision_factors"):
            lines.append("Key Decision Factors:")
            for f in reasoning_result.decision_factors:
                lines.append(f"- [{f.category.value if hasattr(f.category, 'value') else f.category}] {f.factor}: {f.value} (Impact: {f.impact.value if hasattr(f.impact, 'value') else f.impact}, Agent: {f.source_agent})")
        if hasattr(reasoning_result, "consistency") and reasoning_result.consistency.conflicts:
            lines.append("Detected Conflicts & Integrity Warnings:")
            for c in reasoning_result.consistency.conflicts:
                lines.append(f"- [{c.severity.value if hasattr(c.severity, 'value') else c.severity}] {c.conflict_type}: {c.description}")
        if hasattr(reasoning_result, "conclusions") and reasoning_result.conclusions:
            lines.append("Operational Conclusions:")
            for conc in reasoning_result.conclusions:
                lines.append(f"- {conc}")
        if hasattr(reasoning_result, "uncertainties") and reasoning_result.uncertainties:
            lines.append("Surfaced Uncertainties & Gaps:")
            for u in reasoning_result.uncertainties:
                lines.append(f"- {u}")
        return "\n".join(lines)

    def _generate_deterministic_synthesis(
        self,
        result: OrchestrationResult,
        request: PlannerRequest,
        data_freshness: Dict[str, DataStatus],
        reasoning_result: Optional[Any] = None,
        evidence_context: Optional[Any] = None,
    ) -> str:
        """
        Factual deterministic synthesis engine.
        Guarantees that when an LLM is offline or unconfigured, the mariner still receives
        a comprehensive, perfectly grounded operational report without data fabrication.
        """
        paragraphs = []

        # 1. Overall assessment header
        intent_title = result.plan.intent.replace("_", " ").title()
        paragraphs.append(
            f"**ORCA Marine Decision Report — {intent_title}**\n"
            f"Location: ({request.latitude:.4f}°N, {request.longitude:.4f}°E)."
        )

        # 2. Weather & Atmospheric
        weather_res = result.agent_results.get("weather")
        if weather_res:
            if weather_res.status == AgentStatus.SUCCESS and weather_res.data:
                curr = weather_res.data.get("current", {})
                temp = curr.get("temperature_c") if curr.get("temperature_c") is not None else curr.get("temperature", "?")
                w_spd = curr.get("wind_speed_knots") if curr.get("wind_speed_knots") is not None else curr.get("wind_speed", "?")
                w_gust = curr.get("wind_gusts_knots") if curr.get("wind_gusts_knots") is not None else curr.get("wind_gusts", "?")
                w_dir = curr.get("wind_direction_compass") or curr.get("wind_direction", "N/A")
                w_str = (
                    f"**Atmospheric Weather:** Temperature {temp}°C, "
                    f"wind speed {w_spd} knots from {w_dir}, "
                    f"gusts up to {w_gust} knots."
                )
                paragraphs.append(w_str)
            elif weather_res.status == AgentStatus.FAILED:
                paragraphs.append("**Atmospheric Weather:** Live weather telemetry could not be retrieved.")

        # 3. Oceanographic & Sea State
        marine_res = result.agent_results.get("marine")
        if marine_res:
            if marine_res.status == AgentStatus.SUCCESS and marine_res.data:
                curr = marine_res.data.get("current", {})
                wh = curr.get("wave_height_m") if curr.get("wave_height_m") is not None else curr.get("wave_height", "?")
                wp = curr.get("dominant_wave_period_s") if curr.get("dominant_wave_period_s") is not None else (curr.get("wave_period") or curr.get("dominant_wave_period", "?"))
                swh = curr.get("swell_wave_height_m") if curr.get("swell_wave_height_m") is not None else curr.get("swell_wave_height", "?")
                sst = curr.get("sea_surface_temperature_c") if curr.get("sea_surface_temperature_c") is not None else (curr.get("sea_surface_temperature") or curr.get("sst", "?"))
                m_str = (
                    f"**Ocean Conditions:** Significant wave height is {wh} m "
                    f"with dominant wave period of {wp} s. "
                    f"Swell wave height is {swh} m. "
                    f"Sea Surface Temperature (SST) is {sst}°C."
                )
                paragraphs.append(m_str)
            elif marine_res.status == AgentStatus.FAILED:
                paragraphs.append("**Ocean Conditions:** Oceanographic wave and SST telemetry could not be retrieved.")

        # 4. Marine Hazards
        hazard_res = result.agent_results.get("hazard")
        if hazard_res:
            if hazard_res.status == AgentStatus.SUCCESS and hazard_res.data:
                h_state = hazard_res.data.get("hazard_state", "UNKNOWN")
                alerts = hazard_res.data.get("alerts", [])
                if alerts:
                    alert_desc = "; ".join([a.get("headline", a.get("event", "Hazard alert")) for a in alerts])
                    paragraphs.append(f"**Hazard Warnings:** Alert state '{h_state}'. Active alerts: {alert_desc}.")
                else:
                    paragraphs.append(f"**Hazard Assessment:** {h_state}. No severe meteorological or sea squall warnings active.")
            elif hazard_res.status == AgentStatus.FAILED:
                paragraphs.append("**Hazard Assessment:** Real-time hazard evaluation was unavailable.")

        # 5. Potential Fishing Zones (PFZ)
        pfz_res = result.agent_results.get("pfz")
        if pfz_res:
            if pfz_res.status in (AgentStatus.SUCCESS, AgentStatus.PARTIAL) and pfz_res.data:
                if pfz_res.data.get("available"):
                    nearest = pfz_res.data.get("nearest_advisory")
                    ref_layer = pfz_res.data.get("advisory_metadata", {}).get("reference_layer_date") or "historical INCOIS layer"
                    if nearest and isinstance(nearest, dict):
                        paragraphs.append(
                            f"**Potential Fishing Zones (INCOIS):** Reference advisory identified near "
                            f"{nearest.get('landing_center')} sector ({nearest.get('distance_from_query_km')} km from assessment position, "
                            f"bearing {nearest.get('bearing_degrees')}° {nearest.get('direction', '')}). "
                            f"Note: This is based on official INCOIS reference layer ({ref_layer})."
                        )
                    else:
                        paragraphs.append(
                            f"**Potential Fishing Zones (INCOIS):** Regional frontal vectors active on map ({ref_layer})."
                        )
                else:
                    paragraphs.append(
                        "**Potential Fishing Zones (INCOIS):** No localized INCOIS PFZ advisory targets found within the search perimeter."
                    )
            elif pfz_res.status == AgentStatus.FAILED:
                paragraphs.append("**Potential Fishing Zones (INCOIS):** PFZ advisory telemetry could not be accessed.")

        # 6. Satellite Chlorophyll
        chloro_res = result.agent_results.get("chlorophyll")
        if chloro_res:
            if chloro_res.data and chloro_res.data.get("available"):
                val = chloro_res.data.get("chlorophyll_a_mg_m3")
                paragraphs.append(f"**Satellite Chlorophyll-a:** {val:.2f} mg/m³.")
            else:
                # Truthful disclosure of unavailable satellite data
                paragraphs.append(
                    "**Satellite Chlorophyll-a:** Current satellite ocean-color chlorophyll concentration is unavailable from configured sources."
                )

        # 7. GIS Maritime Boundaries
        gis_res = result.agent_results.get("gis")
        if gis_res:
            if data_freshness.get("gis") == DataStatus.UNAVAILABLE or gis_res.status == AgentStatus.PARTIAL:
                paragraphs.append(
                    "**Maritime Boundaries (GIS):** ORCA could not verify official maritime restriction polygons for this location (GIS source status: UNAVAILABLE)."
                )
            elif gis_res.status == AgentStatus.SUCCESS and gis_res.data:
                paragraphs.append(f"**Maritime Boundaries (GIS):** {gis_res.message or 'Boundary check completed.'}")

        # 8. Route Intelligence
        route_res = result.agent_results.get("route")
        if route_res:
            if route_res.status == AgentStatus.SUCCESS and route_res.data:
                rec_id = route_res.data.get("recommended_route_id")
                routes = route_res.data.get("routes", [])
                rec_route = next((r for r in routes if r.get("id") == rec_id), None)
                if rec_route:
                    paragraphs.append(
                        f"**Route Recommendation:** Recommended corridor '{rec_route.get('name')}' "
                        f"(Distance: {rec_route.get('distance_nm')} nm, Risk Score: {rec_route.get('risk_score')}/100 - {rec_route.get('risk_level')})."
                    )
                else:
                    paragraphs.append(f"**Route Recommendation:** {len(routes)} candidate corridors evaluated.")
            elif route_res.status == AgentStatus.FAILED:
                paragraphs.append(f"**Route Recommendation:** Route evaluation could not be completed: {route_res.message}")

        # 9. Warnings & Caveats
        if result.warnings:
            unique_warnings = list(dict.fromkeys(result.warnings))
            paragraphs.append(f"**Operational Notices:** {' '.join(unique_warnings)}")

        # 10. Phase 5 Multi-Agent Reasoning Integration
        if reasoning_result is not None:
            if hasattr(reasoning_result, "conclusions") and reasoning_result.conclusions:
                conc_text = "\n".join([f"• {c}" for c in reasoning_result.conclusions])
                paragraphs.append(f"**Operational Reasoning Conclusions:**\n{conc_text}")

            if hasattr(reasoning_result, "consistency") and reasoning_result.consistency.conflicts:
                conflict_text = "\n".join([f"• [{c.severity.value if hasattr(c.severity, 'value') else c.severity}] {c.description}" for c in reasoning_result.consistency.conflicts])
                paragraphs.append(f"**Cross-Agent Consistency & Conflicts:**\n{conflict_text}")

            if hasattr(reasoning_result, "uncertainties") and reasoning_result.uncertainties:
                unc_text = "\n".join([f"• {u}" for u in reasoning_result.uncertainties])
                paragraphs.append(f"**Information Gaps & Telemetry Uncertainty:**\n{unc_text}")

            if hasattr(reasoning_result, "required_followups") and reasoning_result.required_followups:
                flw_text = "\n".join([f"• {f}" for f in reasoning_result.required_followups])
                paragraphs.append(f"**Actionable Mariner Verification Checks:**\n{flw_text}")

        # 11. Phase 6 Contextual Knowledge & Authoritative Reference Citations
        citations = []
        if evidence_context is not None and hasattr(evidence_context, "citations"):
            citations = evidence_context.citations
        elif reasoning_result is not None and hasattr(reasoning_result, "evidence_context"):
            ev_ctx = getattr(reasoning_result, "evidence_context", None)
            if ev_ctx is not None and hasattr(ev_ctx, "citations"):
                citations = ev_ctx.citations

        if citations:
            status = getattr(evidence_context, "retrieval_status", None)
            status_val = getattr(status, "value", str(status)) if status is not None else "SUCCESS"
            if status_val == "SUCCESS":
                citation_lines = []
                for idx, c in enumerate(citations, 1):
                    ref_suffix = f" — [{c.reference}]" if getattr(c, "reference", None) else ""
                    auth_val = getattr(c.authority_level, "value", str(c.authority_level)) if hasattr(c, "authority_level") else "VERIFIED_REFERENCE"
                    citation_lines.append(
                        f"{idx}. **{c.title}** ({c.publisher}, Authority: `{auth_val}`){ref_suffix}\n"
                        f"   *Guidance:* \"{c.relevant_chunk}\""
                    )
                paragraphs.append(f"**Authoritative References & Guidance:**\n" + "\n".join(citation_lines))

        return "\n\n".join(paragraphs)
