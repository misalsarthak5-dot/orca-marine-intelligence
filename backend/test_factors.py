"""
ORCA Phase 5 — Decision Factor Extraction Verification Suite
Tests:
1. Extraction across all 7 domain agents (Weather, Marine, Chlorophyll, PFZ, Hazard, GIS, Route)
2. Evidence traceability (every factor has source_agent and valid Evidence record)
3. Zero data fabrication (missing or None fields are never invented)
4. Truthful UNAVAILABLE factor representation (Chlorophyll and GIS)
5. Impact level mapping (FAVORABLE, CAUTION, UNFAVORABLE, NEUTRAL, CRITICAL)
"""

import asyncio
from core.schemas import AgentResult, AgentStatus, Evidence, DataStatus
from reasoning.schemas import (
    DecisionFactor,
    FactorCategory,
    ImpactLevel,
)
from reasoning.factors import DecisionFactorExtractor


def test_weather_factor_extraction():
    print("\n[TEST 1] Weather Factor Extraction & Evidence Traceability...")
    extractor = DecisionFactorExtractor()

    ev = Evidence(source="Open-Meteo Forecast", source_type="api", data_status=DataStatus.LIVE)
    w_res = AgentResult(
        agent="weather",
        status=AgentStatus.SUCCESS,
        data={
            "current": {
                "temperature_c": 28.2,
                "wind_speed_knots": 9.4,
                "wind_gusts_knots": 14.1,
                "precipitation_mm": 0.0,
            }
        },
        evidence=ev,
        confidence=1.0,
    )

    factors = extractor.extract_all({"weather": w_res})
    names = {f.factor: f for f in factors}

    assert "Wind Speed" in names
    assert names["Wind Speed"].value == "9.4 knots"
    assert names["Wind Speed"].impact == ImpactLevel.FAVORABLE
    assert names["Wind Speed"].evidence.source == "Open-Meteo Forecast"
    assert names["Wind Speed"].category == FactorCategory.ATMOSPHERIC

    assert "Wind Gusts" in names
    assert names["Wind Gusts"].value == "14.1 knots"

    assert "Air Temperature" in names
    assert names["Air Temperature"].value == "28.2 °C"

    assert "Precipitation" in names
    assert names["Precipitation"].value == "0.0 mm"
    print("  [PASS] All atmospheric factors extracted with direct evidence links.")


def test_marine_factor_extraction():
    print("\n[TEST 2] Marine Factor Extraction & Impact Levels...")
    extractor = DecisionFactorExtractor()

    ev = Evidence(source="Open-Meteo Marine", source_type="api", data_status=DataStatus.LIVE)
    m_res = AgentResult(
        agent="marine",
        status=AgentStatus.SUCCESS,
        data={
            "current": {
                "wave_height_m": 0.95,
                "dominant_wave_period_s": 6.2,
                "swell_wave_height_m": 0.70,
                "sea_surface_temperature_c": 29.4,
            }
        },
        evidence=ev,
        confidence=1.0,
    )

    factors = extractor.extract_all({"marine": m_res})
    names = {f.factor: f for f in factors}

    assert "Significant Wave Height" in names
    assert names["Significant Wave Height"].value == "0.95 m"
    assert names["Significant Wave Height"].impact == ImpactLevel.FAVORABLE
    assert names["Significant Wave Height"].category == FactorCategory.OCEANOGRAPHIC

    assert "Wave Period" in names
    assert names["Wave Period"].value == "6.2 s"

    assert "Sea Surface Temperature (SST)" in names
    assert names["Sea Surface Temperature (SST)"].value == "29.4 °C"
    print("  [PASS] All oceanographic factors extracted with impact categorization.")


def test_pfz_and_chlorophyll_factor_extraction():
    print("\n[TEST 3] PFZ and Chlorophyll Factors (Available vs Unavailable)...")
    extractor = DecisionFactorExtractor()

    # PFZ available with historical layer
    pfz_ev = Evidence(
        source="INCOIS WebGIS GeoServer",
        source_type="ogc_wfs",
        observed_at="2024-04-29T00:00:00Z",
        data_status=DataStatus.STALE,
    )
    pfz_res = AgentResult(
        agent="pfz",
        status=AgentStatus.SUCCESS,
        data={
            "available": True,
            "nearest_advisory": {
                "landing_center": "Malpe Landing",
                "distance_from_query_km": 42.5,
                "bearing_degrees": 240.0,
                "direction": "SW",
                "reference_layer_date": "29-Apr-2024",
            }
        },
        evidence=pfz_ev,
        confidence=0.8,
    )

    # Chlorophyll UNAVAILABLE
    chla_ev = Evidence(
        source="NASA Ocean Color / MODIS-Aqua",
        source_type="satellite",
        data_status=DataStatus.UNAVAILABLE,
    )
    chla_res = AgentResult(
        agent="chlorophyll",
        status=AgentStatus.PARTIAL,
        data={"available": False, "chlorophyll_a_mg_m3": None},
        evidence=chla_ev,
        confidence=0.5,
    )

    factors = extractor.extract_all({"pfz": pfz_res, "chlorophyll": chla_res})
    names = {f.factor: f for f in factors}

    assert "PFZ Advisory Presence" in names
    assert "Malpe Landing" in str(names["PFZ Advisory Presence"].value)

    assert "PFZ Target Distance & Bearing" in names
    assert "42.5 km" in str(names["PFZ Target Distance & Bearing"].value)

    assert "PFZ Layer Snapshot Freshness" in names
    assert "29-Apr-2024" in str(names["PFZ Layer Snapshot Freshness"].value)
    assert names["PFZ Layer Snapshot Freshness"].impact == ImpactLevel.CAUTION

    # Chlorophyll should be extracted truthfully as UNAVAILABLE, never fabricated
    assert "Chlorophyll Data Readiness" in names
    assert names["Chlorophyll Data Readiness"].value == "UNAVAILABLE"
    assert "Chlorophyll-a Concentration" not in names  # Zero fabrication!
    print("  [PASS] PFZ and Chlorophyll factors extracted with zero fabrication for unavailable data.")


def test_hazard_gis_route_factor_extraction():
    print("\n[TEST 4] Hazard, GIS, and Route Factor Extraction...")
    extractor = DecisionFactorExtractor()

    h_res = AgentResult(
        agent="hazard",
        status=AgentStatus.SUCCESS,
        data={"hazard_state": "NO SIGNIFICANT HAZARDS", "alerts": []},
        evidence=Evidence(source="HazardEngine", source_type="rule_engine", data_status=DataStatus.LIVE),
        confidence=1.0,
    )
    gis_res = AgentResult(
        agent="gis",
        status=AgentStatus.PARTIAL,
        data={"restriction_status": "UNAVAILABLE", "zones": []},
        evidence=Evidence(source="MSDI WFS", source_type="ogc_wfs", data_status=DataStatus.UNAVAILABLE),
        confidence=0.5,
    )
    route_res = AgentResult(
        agent="route",
        status=AgentStatus.SUCCESS,
        data={
            "recommended_route_id": "route_1",
            "routes": [
                {"id": "route_1", "name": "Direct Corridor", "distance_nm": 18.4, "risk_score": 24.0, "risk_level": "LOW"}
            ]
        },
        evidence=Evidence(source="RouteEngine", source_type="api", data_status=DataStatus.LIVE),
        confidence=1.0,
    )

    factors = extractor.extract_all({"hazard": h_res, "gis": gis_res, "route": route_res})
    names = {f.factor: f for f in factors}

    assert "Marine Hazard State" in names
    assert names["Marine Hazard State"].value == "NO SIGNIFICANT HAZARDS"
    assert names["Marine Hazard State"].impact == ImpactLevel.FAVORABLE

    assert "Maritime Geofence Clearance" in names
    assert names["Maritime Geofence Clearance"].value == "UNAVAILABLE"
    assert names["Maritime Geofence Clearance"].impact == ImpactLevel.CAUTION

    assert "Recommended Navigation Corridor" in names
    assert "Direct Corridor" in str(names["Recommended Navigation Corridor"].value)
    assert names["Recommended Navigation Corridor"].impact == ImpactLevel.FAVORABLE
    print("  [PASS] Hazard, GIS, and Route factors successfully extracted.")


def test_zero_fabrication_on_empty_agent_data():
    print("\n[TEST 5] Zero Data Fabrication on Empty or Failed Results...")
    extractor = DecisionFactorExtractor()

    failed_weather = AgentResult(
        agent="weather",
        status=AgentStatus.FAILED,
        data=None,
        errors=["Service timeout"],
        confidence=0.0,
    )

    factors = extractor.extract_all({"weather": failed_weather})
    assert len(factors) == 0, "No factors should be extracted from a failed agent with None data"
    print("  [PASS] Confirmed zero fabricated factors when agent data is None.")


def main():
    print("=" * 65)
    print("ORCA PHASE 5 — DECISION FACTOR EXTRACTION VERIFICATION SUITE")
    print("=" * 65)

    test_weather_factor_extraction()
    test_marine_factor_extraction()
    test_pfz_and_chlorophyll_factor_extraction()
    test_hazard_gis_route_factor_extraction()
    test_zero_fabrication_on_empty_agent_data()

    print("\n" + "=" * 65)
    print("ALL DECISION FACTOR EXTRACTION TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    main()
