import asyncio
import json
import sys

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from services.route_service import analyze_routes_service, generate_corridor_coordinates, haversine_distance
from services.orca_service import process_orca_query
from services.pfz_service import get_pfz_assessment

async def run_comprehensive_tests():
    print("=" * 60)
    print("ORCA ROUTE INTELLIGENCE MVP - VERIFICATION SUITE")
    print("=" * 60)

    # 1. Test Corridor Generation Geodesic Math
    print("\n[TEST 1] Geodesic Corridor Generation Math")
    goa_lat, goa_lon = 15.4989, 73.8278
    target_lat, target_lon = 15.2000, 73.5000
    direct = generate_corridor_coordinates(goa_lat, goa_lon, target_lat, target_lon, 7, 0.0)
    north = generate_corridor_coordinates(goa_lat, goa_lon, target_lat, target_lon, 7, 0.12)
    south = generate_corridor_coordinates(goa_lat, goa_lon, target_lat, target_lon, 7, -0.12)

    assert len(direct) == 7, "Direct path must have 7 points"
    assert len(north) == 7, "North path must have 7 points"
    assert len(south) == 7, "South path must have 7 points"
    assert direct[0] == [goa_lat, goa_lon], "Start must be origin"
    assert direct[-1] == [target_lat, target_lon], "End must be destination"
    assert north[0] == [goa_lat, goa_lon], "North start must be origin"
    assert south[-1] == [target_lat, target_lon], "South end must be destination"
    # Ensure intermediate points differ between corridors
    assert direct[3] != north[3], "Corridors must diverge midway"
    assert direct[3] != south[3], "Corridors must diverge midway"
    print("[PASS] Geodesic interpolation and perpendicular lateral offset passed.")

    # 2. Location Testing: Goa -> Nearby PFZ
    print("\n[TEST 2] Location Testing: Goa -> Target")
    goa_routes = await analyze_routes_service(
        origin_lat=15.4989,
        origin_lon=73.8278,
        destination_lat=15.1500,
        destination_lon=73.5500,
        destination_name="Goa Offshore PFZ",
        time_window="tomorrow_morning"
    )
    assert goa_routes["available"] is True
    assert len(goa_routes["routes"]) == 3
    assert goa_routes["recommended_route_id"] in ["route_1", "route_2", "route_3"]
    assert "recommendation_reason" in goa_routes and len(goa_routes["recommendation_reason"]) > 10
    print(f"[PASS] Goa routes generated: {len(goa_routes['routes'])} corridors.")
    print(f"  Recommended: {goa_routes['recommended_route_id']}")
    print(f"  Reason: {goa_routes['recommendation_reason']}")

    # 3. Location Testing: Kochi -> Target
    print("\n[TEST 3] Location Testing: Kochi -> Target")
    kochi_routes = await analyze_routes_service(
        origin_lat=9.9312,
        origin_lon=76.2673,
        destination_lat=9.6000,
        destination_lon=75.9500,
        destination_name="Kochi Pelagic PFZ",
        time_window="tomorrow_morning"
    )
    assert kochi_routes["available"] is True
    assert len(kochi_routes["routes"]) == 3
    # Check that coordinates are Kochi-specific, NOT Mumbai
    assert abs(kochi_routes["origin"]["latitude"] - 9.9312) < 0.001
    print(f"[PASS] Kochi routes generated with coordinates {kochi_routes['origin']}")
    print(f"  Recommended: {kochi_routes['recommended_route_id']}")

    # 4. Location Testing: Chennai -> Target
    print("\n[TEST 4] Location Testing: Chennai -> Target")
    chennai_routes = await analyze_routes_service(
        origin_lat=13.0827,
        origin_lon=80.2707,
        destination_lat=13.2500,
        destination_lon=80.6000,
        destination_name="Chennai Deep Bay Sector",
        time_window="tomorrow"
    )
    assert chennai_routes["available"] is True
    assert abs(chennai_routes["origin"]["latitude"] - 13.0827) < 0.001
    print(f"[PASS] Chennai routes generated with coordinates {chennai_routes['origin']}")

    # 5. Location Testing: Mumbai -> Target
    print("\n[TEST 5] Location Testing: Mumbai -> Target")
    mumbai_routes = await analyze_routes_service(
        origin_lat=19.0760,
        origin_lon=72.8777,
        destination_lat=18.8000,
        destination_lon=72.5000,
        destination_name="Mumbai Off-Shore Reef",
        time_window="current"
    )
    assert mumbai_routes["available"] is True
    print(f"[PASS] Mumbai routes generated with coordinates {mumbai_routes['origin']}")

    # 6. Check Marine Condition Sampling & Risk Scores
    print("\n[TEST 6] Marine Condition Sampling & Risk Scores Verification")
    for r in goa_routes["routes"]:
        print(f"  Route: {r['name']} | Dist: {r['distance_km']} km | Est Time: {r['estimated_time_hours']} hrs")
        print(f"  Risk: {r['risk_score']}/100 ({r['risk_level']}) | Peak Wave: {r['conditions']['peak_wave_m']}m | Peak Wind: {r['conditions']['peak_wind_kt']}kt | Peak Swell: {r['conditions']['peak_swell_m']}m")
        print(f"  Factors: {', '.join(r['risk_factors'])}")
        assert r["risk_score"] >= 0 and r["risk_score"] <= 100
        assert r["risk_level"] in ["LOW", "CAUTION", "HIGH"]
        assert r["conditions"]["peak_wave_m"] >= 0
        assert r["conditions"]["peak_wind_kt"] >= 0
    print("[PASS] Route telemetry sampling and risk scores valid.")

    # 7. Ask ORCA Route Queries: English
    print("\n[TEST 7] Ask ORCA Route Queries (English)")
    en_query = "Which route is better for fishing?"
    en_resp = await process_orca_query(query=en_query, language="en", lat=15.4989, lon=73.8278, location_name="Goa Coast")
    assert en_resp["intent"] == "safest_route"
    assert "ORCA" in en_resp["content"]
    assert en_resp["resolved_location"] == "Goa Coast"
    print(f"[PASS] English response generated for '{en_query}':\n  Title: {en_resp['verdict_title']}")

    # 8. Ask ORCA Route Queries: Hindi
    print("\n[TEST 8] Ask ORCA Route Queries (Hindi)")
    hi_query = "PFZ तक जाने के लिए कौन सा रास्ता बेहतर है?"
    hi_resp = await process_orca_query(query=hi_query, language="hi", lat=15.4989, lon=73.8278, location_name="Goa Coast")
    assert hi_resp["intent"] == "safest_route"
    print(f"[PASS] Hindi query correctly resolved intent='{hi_resp['intent']}' (Language='hi')")

    # 9. Ask ORCA Route Queries: Marathi
    print("\n[TEST 9] Ask ORCA Route Queries (Marathi)")
    mr_query = "PFZ जवळ जाण्यासाठी कोणता मार्ग चांगला आहे?"
    mr_resp = await process_orca_query(query=mr_query, language="mr", lat=15.4989, lon=73.8278, location_name="Goa Coast")
    assert mr_resp["intent"] == "safest_route"
    print(f"[PASS] Marathi query correctly resolved intent='{mr_resp['intent']}' (Language='mr')")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_comprehensive_tests())
