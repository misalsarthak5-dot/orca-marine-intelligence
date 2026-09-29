"""
ORCA Decision Factor Extraction — Phase 5
Extracts grounded, factual decision factors from domain AgentResults.
Enforces strict evidence traceability without inventing missing data.
"""

from typing import Dict, Any, List, Optional
from core.schemas import AgentResult, AgentStatus, Evidence, DataStatus
from .schemas import DecisionFactor, FactorCategory, ImpactLevel


class DecisionFactorExtractor:
    """
    Inspects AgentResults and extracts standardized, traceable DecisionFactors.
    Never fabricates values for absent or unobserved fields.
    """

    def extract_all(self, agent_results: Dict[str, AgentResult]) -> List[DecisionFactor]:
        """
        Extract all factual decision factors across available domain agents.

        Args:
            agent_results: Mapping of agent canonical name to AgentResult.

        Returns:
            List of DecisionFactor objects with provenance links.
        """
        factors: List[DecisionFactor] = []

        if "weather" in agent_results:
            factors.extend(self._extract_weather_factors(agent_results["weather"]))

        if "marine" in agent_results:
            factors.extend(self._extract_marine_factors(agent_results["marine"]))

        if "chlorophyll" in agent_results:
            factors.extend(self._extract_chlorophyll_factors(agent_results["chlorophyll"]))

        if "pfz" in agent_results:
            factors.extend(self._extract_pfz_factors(agent_results["pfz"]))

        if "hazard" in agent_results:
            factors.extend(self._extract_hazard_factors(agent_results["hazard"]))

        if "gis" in agent_results:
            factors.extend(self._extract_gis_factors(agent_results["gis"]))

        if "route" in agent_results:
            factors.extend(self._extract_route_factors(agent_results["route"]))

        return factors

    def _extract_weather_factors(self, res: AgentResult) -> List[DecisionFactor]:
        """Extract atmospheric conditions: wind speed, gusts, direction, temperature, precipitation."""
        factors: List[DecisionFactor] = []
        if res.status != AgentStatus.SUCCESS or not res.data:
            return factors

        curr = res.data.get("current", {})
        ev = res.evidence
        conf = res.confidence

        # 1. Wind Speed
        w_spd_raw = curr.get("wind_speed_knots") if curr.get("wind_speed_knots") is not None else curr.get("wind_speed")
        if w_spd_raw is not None:
            w_spd = float(w_spd_raw)
            impact = ImpactLevel.FAVORABLE if w_spd <= 15.0 else (ImpactLevel.CAUTION if w_spd <= 22.0 else ImpactLevel.UNFAVORABLE)
            factors.append(DecisionFactor(
                factor="Wind Speed",
                category=FactorCategory.ATMOSPHERIC,
                value=f"{w_spd:.1f} knots",
                source_agent="weather",
                evidence=ev,
                impact=impact,
                confidence=conf,
                explanation=f"Surface wind speed of {w_spd:.1f} kn affects small craft handling and vessel drift.",
            ))

        # 2. Wind Gusts
        w_gust_raw = curr.get("wind_gusts_knots") if curr.get("wind_gusts_knots") is not None else curr.get("wind_gusts")
        if w_gust_raw is not None:
            w_gust = float(w_gust_raw)
            impact = ImpactLevel.FAVORABLE if w_gust <= 20.0 else (ImpactLevel.CAUTION if w_gust <= 28.0 else ImpactLevel.UNFAVORABLE)
            factors.append(DecisionFactor(
                factor="Wind Gusts",
                category=FactorCategory.ATMOSPHERIC,
                value=f"{w_gust:.1f} knots",
                source_agent="weather",
                evidence=ev,
                impact=impact,
                confidence=conf,
                explanation=f"Peak gusts reaching {w_gust:.1f} kn dictate rig safety and squall readiness.",
            ))

        # 3. Air Temperature
        temp_raw = curr.get("temperature_c") if curr.get("temperature_c") is not None else curr.get("temperature")
        if temp_raw is not None:
            factors.append(DecisionFactor(
                factor="Air Temperature",
                category=FactorCategory.ATMOSPHERIC,
                value=f"{float(temp_raw):.1f} °C",
                source_agent="weather",
                evidence=ev,
                impact=ImpactLevel.NEUTRAL,
                confidence=conf,
            ))

        # 4. Precipitation
        precip_raw = curr.get("precipitation_mm") if curr.get("precipitation_mm") is not None else curr.get("precipitation")
        if precip_raw is not None:
            precip = float(precip_raw)
            impact = ImpactLevel.FAVORABLE if precip == 0.0 else (ImpactLevel.CAUTION if precip < 5.0 else ImpactLevel.UNFAVORABLE)
            factors.append(DecisionFactor(
                factor="Precipitation",
                category=FactorCategory.ATMOSPHERIC,
                value=f"{precip:.1f} mm",
                source_agent="weather",
                evidence=ev,
                impact=impact,
                confidence=conf,
            ))

        return factors

    def _extract_marine_factors(self, res: AgentResult) -> List[DecisionFactor]:
        """Extract oceanographic telemetry: wave height, period, swell, SST."""
        factors: List[DecisionFactor] = []
        if res.status != AgentStatus.SUCCESS or not res.data:
            return factors

        curr = res.data.get("current", {})
        ev = res.evidence
        conf = res.confidence

        # 1. Significant Wave Height
        wh_raw = curr.get("wave_height_m") if curr.get("wave_height_m") is not None else curr.get("wave_height")
        if wh_raw is not None:
            wh = float(wh_raw)
            impact = ImpactLevel.FAVORABLE if wh <= 1.25 else (ImpactLevel.CAUTION if wh <= 2.0 else ImpactLevel.UNFAVORABLE)
            factors.append(DecisionFactor(
                factor="Significant Wave Height",
                category=FactorCategory.OCEANOGRAPHIC,
                value=f"{wh:.2f} m",
                source_agent="marine",
                evidence=ev,
                impact=impact,
                confidence=conf,
                explanation=f"Significant wave height of {wh:.2f} m governs deck safety and vessel pitch/roll.",
            ))

        # 2. Dominant Wave Period
        wp_raw = curr.get("dominant_wave_period_s") if curr.get("dominant_wave_period_s") is not None else (curr.get("wave_period") or curr.get("dominant_wave_period"))
        if wp_raw is not None:
            wp = float(wp_raw)
            factors.append(DecisionFactor(
                factor="Wave Period",
                category=FactorCategory.OCEANOGRAPHIC,
                value=f"{wp:.1f} s",
                source_agent="marine",
                evidence=ev,
                impact=ImpactLevel.NEUTRAL,
                confidence=conf,
            ))

        # 3. Swell Wave Height
        swh_raw = curr.get("swell_wave_height_m") if curr.get("swell_wave_height_m") is not None else curr.get("swell_wave_height")
        if swh_raw is not None:
            swh = float(swh_raw)
            impact = ImpactLevel.FAVORABLE if swh <= 1.0 else (ImpactLevel.CAUTION if swh <= 1.8 else ImpactLevel.UNFAVORABLE)
            factors.append(DecisionFactor(
                factor="Swell Wave Height",
                category=FactorCategory.OCEANOGRAPHIC,
                value=f"{swh:.2f} m",
                source_agent="marine",
                evidence=ev,
                impact=impact,
                confidence=conf,
            ))

        # 4. Sea Surface Temperature
        sst_raw = curr.get("sea_surface_temperature_c") if curr.get("sea_surface_temperature_c") is not None else (curr.get("sea_surface_temperature") or curr.get("sst"))
        if sst_raw is not None:
            sst = float(sst_raw)
            factors.append(DecisionFactor(
                factor="Sea Surface Temperature (SST)",
                category=FactorCategory.OCEANOGRAPHIC,
                value=f"{sst:.1f} °C",
                source_agent="marine",
                evidence=ev,
                impact=ImpactLevel.NEUTRAL,
                confidence=conf,
                explanation=f"SST of {sst:.1f} °C is a key biological indicator for pelagic fish distribution.",
            ))

        return factors

    def _extract_chlorophyll_factors(self, res: AgentResult) -> List[DecisionFactor]:
        """Extract satellite chlorophyll-a concentration and source readiness."""
        factors: List[DecisionFactor] = []
        ev = res.evidence
        conf = res.confidence

        if res.data and res.data.get("available") and res.data.get("chlorophyll_a_mg_m3") is not None:
            chla = float(res.data["chlorophyll_a_mg_m3"])
            factors.append(DecisionFactor(
                factor="Chlorophyll-a Concentration",
                category=FactorCategory.FISHERY,
                value=f"{chla:.2f} mg/m³",
                source_agent="chlorophyll",
                evidence=ev,
                impact=ImpactLevel.FAVORABLE if chla >= 0.2 else ImpactLevel.NEUTRAL,
                confidence=conf,
                explanation=f"Ocean-color chlorophyll concentration of {chla:.2f} mg/m³ indicates primary biological productivity.",
            ))
        else:
            # Truthful disclosure factor
            factors.append(DecisionFactor(
                factor="Chlorophyll Data Readiness",
                category=FactorCategory.FISHERY,
                value="UNAVAILABLE",
                source_agent="chlorophyll",
                evidence=ev,
                impact=ImpactLevel.NEUTRAL,
                confidence=conf,
                explanation="Satellite ocean-color chlorophyll concentration is unavailable; cannot be used as an active factor.",
            ))

        return factors

    def _extract_pfz_factors(self, res: AgentResult) -> List[DecisionFactor]:
        """Extract INCOIS PFZ presence, distance, bearing, landing centre, and freshness."""
        factors: List[DecisionFactor] = []
        ev = res.evidence
        conf = res.confidence

        if not res.data:
            return factors

        available = res.data.get("available", False)
        nearest = res.data.get("nearest_advisory")

        if available and nearest and isinstance(nearest, dict):
            lc = nearest.get("landing_center", "Unknown Sector")
            dist = nearest.get("distance_from_query_km", 0.0)
            bearing = nearest.get("bearing_degrees", 0.0)
            direction = nearest.get("direction", "")
            ref_date = nearest.get("reference_layer_date") or res.data.get("advisory_metadata", {}).get("reference_layer_date")

            factors.append(DecisionFactor(
                factor="PFZ Advisory Presence",
                category=FactorCategory.FISHERY,
                value=f"Identified near {lc}",
                source_agent="pfz",
                evidence=ev,
                impact=ImpactLevel.FAVORABLE,
                confidence=conf,
                explanation=f"INCOIS landing centre reference advisory identified for {lc}.",
            ))

            factors.append(DecisionFactor(
                factor="PFZ Target Distance & Bearing",
                category=FactorCategory.FISHERY,
                value=f"{dist:.1f} km at {bearing:.0f}° ({direction})",
                source_agent="pfz",
                evidence=ev,
                impact=ImpactLevel.FAVORABLE if dist <= 50.0 else ImpactLevel.NEUTRAL,
                confidence=conf,
                explanation=f"Target distance is {dist:.1f} km from current position along {direction} bearing.",
            ))

            if ref_date:
                factors.append(DecisionFactor(
                    factor="PFZ Layer Snapshot Freshness",
                    category=FactorCategory.FISHERY,
                    value=str(ref_date),
                    source_agent="pfz",
                    evidence=ev,
                    impact=ImpactLevel.CAUTION if (ev and ev.data_status == DataStatus.STALE) else ImpactLevel.NEUTRAL,
                    confidence=conf,
                    explanation=f"Derived from official INCOIS reference layer ({ref_date}).",
                ))
        else:
            factors.append(DecisionFactor(
                factor="PFZ Advisory Presence",
                category=FactorCategory.FISHERY,
                value="NO ACTIVE LOCALIZED ADVISORY",
                source_agent="pfz",
                evidence=ev,
                impact=ImpactLevel.NEUTRAL,
                confidence=conf,
                explanation="No localized INCOIS PFZ landing centre advisories found within search radius.",
            ))

        return factors

    def _extract_hazard_factors(self, res: AgentResult) -> List[DecisionFactor]:
        """Extract hazard state, active alerts, and severity."""
        factors: List[DecisionFactor] = []
        ev = res.evidence
        conf = res.confidence

        if not res.data:
            return factors

        h_state = res.data.get("hazard_state", "UNKNOWN")
        alerts = res.data.get("alerts", [])

        is_high = h_state in ("HIGH", "CRITICAL", "DANGER") or any(a.get("severity", "").upper() == "HIGH" for a in alerts)
        is_caution = h_state in ("CAUTION", "MODERATE", "ADVISORY")

        impact = ImpactLevel.CRITICAL if is_high else (ImpactLevel.CAUTION if is_caution else ImpactLevel.FAVORABLE)

        factors.append(DecisionFactor(
            factor="Marine Hazard State",
            category=FactorCategory.HAZARD,
            value=h_state,
            source_agent="hazard",
            evidence=ev,
            impact=impact,
            confidence=conf,
            explanation=f"Evaluated overall hazard state is '{h_state}' with {len(alerts)} active alert(s).",
        ))

        return factors

    def _extract_gis_factors(self, res: AgentResult) -> List[DecisionFactor]:
        """Extract geofence status, restriction clearance, and spatial warnings."""
        factors: List[DecisionFactor] = []
        ev = res.evidence
        conf = res.confidence

        if not res.data:
            factors.append(DecisionFactor(
                factor="Maritime Geofence Clearance",
                category=FactorCategory.RESTRICTION_GEOFENCE,
                value="UNAVAILABLE",
                source_agent="gis",
                evidence=ev,
                impact=ImpactLevel.CAUTION,
                confidence=conf,
                explanation="Maritime restriction polygons unavailable from authoritative source.",
            ))
            return factors

        status = res.data.get("restriction_status", res.data.get("status", "UNAVAILABLE"))
        zones_count = len(res.data.get("zones", []))

        impact = ImpactLevel.FAVORABLE if status == "CLEAR" else (ImpactLevel.CRITICAL if status == "INTERSECTED" else ImpactLevel.CAUTION)

        factors.append(DecisionFactor(
            factor="Maritime Geofence Clearance",
            category=FactorCategory.RESTRICTION_GEOFENCE,
            value=status,
            source_agent="gis",
            evidence=ev,
            impact=impact,
            confidence=conf,
            explanation=f"Official geofence check returned status '{status}' across {zones_count} registered zone(s).",
        ))

        return factors

    def _extract_route_factors(self, res: AgentResult) -> List[DecisionFactor]:
        """Extract candidate corridors, distance, risk score, and route status."""
        factors: List[DecisionFactor] = []
        ev = res.evidence
        conf = res.confidence

        if res.status != AgentStatus.SUCCESS or not res.data:
            factors.append(DecisionFactor(
                factor="Passage Corridor Assessment",
                category=FactorCategory.NAVIGATION_ROUTE,
                value="UNAVAILABLE / FAILED",
                source_agent="route",
                evidence=ev,
                impact=ImpactLevel.CAUTION,
                confidence=conf,
                explanation="Route corridor intelligence could not be computed.",
            ))
            return factors

        routes = res.data.get("routes", [])
        rec_id = res.data.get("recommended_route_id")
        rec_route = next((r for r in routes if r.get("id") == rec_id), (routes[0] if routes else None))

        if rec_route:
            risk_score = rec_route.get("risk_score", 50)
            risk_level = rec_route.get("risk_level", "MODERATE")
            dist_nm = rec_route.get("distance_nm", 0.0)

            impact = ImpactLevel.FAVORABLE if risk_level == "LOW" else (ImpactLevel.CAUTION if risk_level == "MODERATE" else ImpactLevel.UNFAVORABLE)

            factors.append(DecisionFactor(
                factor="Recommended Navigation Corridor",
                category=FactorCategory.NAVIGATION_ROUTE,
                value=f"{rec_route.get('name', 'Direct')} ({dist_nm:.1f} nm, Risk: {risk_score}/100 {risk_level})",
                source_agent="route",
                evidence=ev,
                impact=impact,
                confidence=conf,
                explanation=f"Optimal passage route '{rec_route.get('name')}' carries {risk_level} risk over {dist_nm:.1f} nautical miles.",
            ))

        return factors
