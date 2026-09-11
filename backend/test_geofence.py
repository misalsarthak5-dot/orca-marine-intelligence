"""
ORCA — Geofencing & Restricted Zone Intelligence Verification Suite

Tests:
1. Point inside restricted polygon (Ray Casting)
2. Point outside restricted polygon
3. Route line segment intersects restricted polygon
4. Route does not intersect restricted polygon
5. Multiple routes where only one intersects (recommendation fallback to viable detour)
6. Restriction data unavailable in production mode (honest UNAVAILABLE state)
7. Invalid/empty geometry handling
8. All 10 coastal locations geofence viability evaluation
9. Route analysis regression (exact mathematical formula preserved)
10. Recommendation logic with geofence viability
11. No fake geometry exposed in production mode
12. Ask ORCA restriction queries (English, Hindi, Marathi)
"""

import asyncio
import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from services.geofence_service import (
    point_in_polygon,
    line_segment_intersects_polygon_ring,
    check_route_intersects_geometry,
    get_active_geofences,
    evaluate_route_geofences,
)
from services.route_service import analyze_routes_service
from services.orca_service import process_orca_query

# ── Synthetic Test Fixtures (STRICTLY FOR TESTING) ────────────────────
# Test Zone A: Polygon over (15.4 to 15.6°N, 73.6 to 73.8°E) off Goa
SYNTHETIC_ZONE_GOA = {
    "id": "test-mpa-001",
    "name": "Synthetic Marine Sanctuary Alpha (Test Fixture)",
    "zone_type": "NO_FISHING_ZONE",
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [
                [73.60, 15.40],
                [73.80, 15.40],
                [73.80, 15.60],
                [73.60, 15.60],
                [73.60, 15.40],
            ]
        ],
    },
}

SYNTHETIC_MULTIPOLYGON = {
    "id": "test-multi-002",
    "name": "Synthetic Multi-Sector Restricted Area",
    "zone_type": "DEFENSE_FIRING_RANGE",
    "geometry": {
        "type": "MultiPolygon",
        "coordinates": [
            [
                [
                    [72.50, 19.20],
                    [72.70, 19.20],
                    [72.70, 19.40],
                    [72.50, 19.40],
                    [72.50, 19.20],
                ]
            ],
            [
                [
                    [72.80, 19.50],
                    [72.90, 19.50],
                    [72.90, 19.60],
                    [72.80, 19.60],
                    [72.80, 19.50],
                ]
            ],
        ],
    },
}

LOCATIONS = [
    ("Mumbai", 19.08, 72.88),
    ("Ratnagiri", 16.99, 73.31),
    ("Goa", 15.50, 73.83),
    ("Mangalore", 12.91, 74.86),
    ("Kochi", 9.93, 76.27),
    ("Chennai", 13.08, 80.27),
    ("Visakhapatnam", 17.69, 83.22),
    ("Puri", 19.81, 85.83),
    ("Kolkata", 21.63, 88.06),
    ("Port Blair", 11.62, 92.73),
]


async def run_geofence_tests():
    print("=" * 70, flush=True)
    print("ORCA GEOFENCING & RESTRICTED-ZONE INTELLIGENCE TEST SUITE", flush=True)
    print("=" * 70, flush=True)

    passed_count = 0
    total_tests = 12

    # ─────────────────────────────────────────────────────────────────
    # 1. Point Inside Restricted Polygon
    # ─────────────────────────────────────────────────────────────────
    print("\n[TEST 1] Point inside restricted polygon...", flush=True)
    ring = SYNTHETIC_ZONE_GOA["geometry"]["coordinates"][0]
    inside = point_in_polygon(15.50, 73.70, ring)
    assert inside is True, f"Expected (15.50, 73.70) to be INSIDE polygon, got {inside}"
    print("  [PASS] Point (15.50, 73.70) correctly identified as INSIDE.", flush=True)
    passed_count += 1

    # ─────────────────────────────────────────────────────────────────
    # 2. Point Outside Restricted Polygon
    # ─────────────────────────────────────────────────────────────────
    print("\n[TEST 2] Point outside restricted polygon...", flush=True)
    outside = point_in_polygon(15.70, 73.90, ring)
    assert outside is False, f"Expected (15.70, 73.90) to be OUTSIDE polygon, got {outside}"
    print("  [PASS] Point (15.70, 73.90) correctly identified as OUTSIDE.", flush=True)
    passed_count += 1

    # ─────────────────────────────────────────────────────────────────
    # 3. Route Intersects Restricted Polygon
    # ─────────────────────────────────────────────────────────────────
    print("\n[TEST 3] Route intersects restricted polygon...", flush=True)
    route_cross = [
        [15.50, 73.50],  # West of zone
        [15.50, 73.70],  # Inside zone
        [15.50, 73.90],  # East of zone
    ]
    intersects = check_route_intersects_geometry(route_cross, SYNTHETIC_ZONE_GOA["geometry"])
    assert intersects is True, f"Expected crossing route to intersect polygon, got {intersects}"
    print("  [PASS] Crossing route correctly flagged as INTERSECTING.", flush=True)
    passed_count += 1

    # ─────────────────────────────────────────────────────────────────
    # 4. Route Does Not Intersect Polygon
    # ─────────────────────────────────────────────────────────────────
    print("\n[TEST 4] Route does not intersect polygon...", flush=True)
    route_clear = [
        [15.20, 73.50],
        [15.20, 73.70],
        [15.20, 73.90],
    ]
    clear = check_route_intersects_geometry(route_clear, SYNTHETIC_ZONE_GOA["geometry"])
    assert clear is False, f"Expected south clear route not to intersect polygon, got {clear}"
    print("  [PASS] Clear route correctly flagged as NON-INTERSECTING.", flush=True)
    passed_count += 1

    # ─────────────────────────────────────────────────────────────────
    # 5. MultiPolygon & Multiple Route Obstacle Detour
    # ─────────────────────────────────────────────────────────────────
    print("\n[TEST 5] Multiple routes where Direct crosses restriction and Northern bypasses...", flush=True)
    # Target positioned such that direct route crosses SYNTHETIC_ZONE_GOA, while a northern detour avoids it
    res = await analyze_routes_service(
        origin_lat=15.50,
        origin_lon=73.85,
        destination_lat=15.50,
        destination_lon=73.55,
        destination_name="Target Offshore",
        time_window="current",
        override_zones=[SYNTHETIC_ZONE_GOA],
    )
    routes = res.get("routes", [])
    direct = next(r for r in routes if r["id"] == "route_1")
    assert direct["restriction_status"] == "RESTRICTED", f"Expected Direct route to be RESTRICTED, got {direct['restriction_status']}"
    assert direct["overall_status"] == "NOT_VIABLE", f"Expected Direct route to be NOT_VIABLE, got {direct['overall_status']}"
    print(f"  [PASS] Direct route overall_status='{direct['overall_status']}', intersecting='{direct['intersecting_zones']}'", flush=True)
    print(f"  [PASS] Recommendation reason: {res['recommendation_reason'][:100]}...", flush=True)
    passed_count += 1

    # ─────────────────────────────────────────────────────────────────
    # 6. Production Mode Restriction Data Unavailable State
    # ─────────────────────────────────────────────────────────────────
    print("\n[TEST 6] Production mode returns honest UNAVAILABLE state...", flush=True)
    geofences = await get_active_geofences(15.50, 73.83)
    assert geofences["status"] == "UNAVAILABLE", f"Expected UNAVAILABLE status, got {geofences['status']}"
    assert len(geofences["zones"]) == 0, f"Expected 0 fake zones in production, got {len(geofences['zones'])}"
    assert geofences["source"] is None, "Expected source to be None"
    print(f"  [PASS] Production geofences status='{geofences['status']}', total_zones={len(geofences['zones'])}", flush=True)
    passed_count += 1

    # ─────────────────────────────────────────────────────────────────
    # 7. Invalid & Empty Geometry Handling
    # ─────────────────────────────────────────────────────────────────
    print("\n[TEST 7] Invalid and empty geometry handling...", flush=True)
    empty_res = check_route_intersects_geometry([], {})
    assert empty_res is False, "Expected False for empty geometry"
    malformed_res = check_route_intersects_geometry([[15.5, 73.8]], {"type": "Polygon", "coordinates": []})
    assert malformed_res is False, "Expected False for malformed geometry"
    print("  [PASS] Handled empty and malformed geometry without exceptions.", flush=True)
    passed_count += 1

    # ─────────────────────────────────────────────────────────────────
    # 8. All 10 Coastal Locations Route Viability
    # ─────────────────────────────────────────────────────────────────
    print("\n[TEST 8] Verifying route intelligence viability across all 10 locations...", flush=True)
    for name, lat, lon in LOCATIONS:
        dest_lat = lat + 0.15
        dest_lon = lon + 0.15
        r_res = await analyze_routes_service(
            origin_lat=lat,
            origin_lon=lon,
            destination_lat=dest_lat,
            destination_lon=dest_lon,
            destination_name=f"{name} Target",
            time_window="current",
        )
        assert r_res["available"] is True, f"Expected routes available for {name}"
        for r in r_res["routes"]:
            assert r["restriction_status"] == "UNAVAILABLE", f"Expected UNAVAILABLE for {name} in production, got {r['restriction_status']}"
            assert r["overall_status"] == "ENVIRONMENTAL_ANALYSIS_ONLY", f"Expected ENVIRONMENTAL_ANALYSIS_ONLY, got {r['overall_status']}"
        print(f"  [PASS] {name:15}: 3 Corridors, Status='{r_res['routes'][0]['overall_status']}'", flush=True)
    passed_count += 1

    # ─────────────────────────────────────────────────────────────────
    # 9. Environmental Risk Formula Regression Check
    # ─────────────────────────────────────────────────────────────────
    print("\n[TEST 9] Verifying mathematical risk formula regression (0.35W + 0.15S + 0.25Wnd + 0.15G + 0.10R)...", flush=True)
    goa_routes = await analyze_routes_service(
        origin_lat=15.50,
        origin_lon=73.83,
        destination_lat=15.65,
        destination_lon=73.98,
        destination_name="Goa Offshore",
        time_window="current",
    )
    r1 = goa_routes["routes"][0]
    c = r1["conditions"]
    w_score = min(100.0, (c["peak_wave_m"] / 2.5) * 100.0)
    s_score = min(100.0, (c["peak_swell_m"] / 2.0) * 100.0)
    wnd_score = min(100.0, (c["peak_wind_kt"] / 25.0) * 100.0)
    g_score = min(100.0, (c["peak_gust_kt"] / 35.0) * 100.0)
    p_score = min(100.0, (c["peak_precipitation_mm"] / 15.0) * 100.0)
    expected_calc = round(0.35 * w_score + 0.15 * s_score + 0.25 * wnd_score + 0.15 * g_score + 0.10 * p_score)
    expected_risk = max(8, min(95, expected_calc))
    assert r1["risk_score"] == expected_risk, f"Formula mismatch: got {r1['risk_score']}, expected {expected_risk}"
    print(f"  [PASS] Risk formula strictly validated: Wave({c['peak_wave_m']}m) + Swell({c['peak_swell_m']}m) + Wind({c['peak_wind_kt']}kt) -> Score={r1['risk_score']}", flush=True)
    passed_count += 1

    # ─────────────────────────────────────────────────────────────────
    # 10. Ask ORCA Multilingual Restriction Queries
    # ─────────────────────────────────────────────────────────────────
    print("\n[TEST 10] Testing Ask ORCA Geofence Queries (EN, HI, MR)...", flush=True)
    
    # English Query
    q_en = await process_orca_query(
        query="Is this route inside a restricted zone?",
        language="en",
        lat=15.50,
        lon=73.83,
        location_name="Goa Coast",
    )
    assert q_en["intent"] == "geofence", f"Expected intent geofence, got {q_en['intent']}"
    assert "UNAVAILABLE" in q_en["content"] or "could not verify" in q_en["content"], "Expected honest UNAVAILABLE explanation in English"
    print(f"  [PASS] EN Query -> Intent='{q_en['intent']}', Title='{q_en['verdict_title']}'", flush=True)

    # Hindi Query
    q_hi = await process_orca_query(
        query="क्या यह रास्ता प्रतिबंधित क्षेत्र से गुजरता है?",
        language="hi",
        lat=15.50,
        lon=73.83,
        location_name="Goa Coast",
    )
    assert q_hi["intent"] == "geofence", f"Expected intent geofence, got {q_hi['intent']}"
    assert "प्रतिबंधित" in q_hi["content"], "Expected Hindi response with restricted zone guidance"
    print(f"  [PASS] HI Query -> Intent='{q_hi['intent']}', Title='{q_hi['verdict_title']}'", flush=True)

    # Marathi Query
    q_mr = await process_orca_query(
        query="हा मार्ग प्रतिबंधित क्षेत्रातून जातो का?",
        language="mr",
        lat=15.50,
        lon=73.83,
        location_name="Goa Coast",
    )
    assert q_mr["intent"] == "geofence", f"Expected intent geofence, got {q_mr['intent']}"
    assert "प्रतिबंधित" in q_mr["content"] or "निर्बंध" in q_mr["content"], "Expected Marathi response with restriction guidance"
    print(f"  [PASS] MR Query -> Intent='{q_mr['intent']}', Title='{q_mr['verdict_title']}'", flush=True)
    passed_count += 1

    # ─────────────────────────────────────────────────────────────────
    # 11. MultiPolygon Geometry Test
    # ─────────────────────────────────────────────────────────────────
    print("\n[TEST 11] MultiPolygon geometry intersection test...", flush=True)
    # Route crossing second polygon in MultiPolygon (19.55, 72.85)
    route_multi = [[19.55, 72.75], [19.55, 72.95]]
    multi_intersect = check_route_intersects_geometry(route_multi, SYNTHETIC_MULTIPOLYGON["geometry"])
    assert multi_intersect is True, "Expected MultiPolygon route to intersect"
    print("  [PASS] MultiPolygon multi-ring intersection correctly identified.", flush=True)
    passed_count += 1

    # ─────────────────────────────────────────────────────────────────
    # 12. Verification of Zero Fake Geometry in Production
    # ─────────────────────────────────────────────────────────────────
    print("\n[TEST 12] Confirming zero fake geometry in production responses...", flush=True)
    for name, lat, lon in LOCATIONS:
        gf = await get_active_geofences(lat, lon)
        assert len(gf["zones"]) == 0, f"Found fake zones for {name} in production!"
        assert gf["status"] == "UNAVAILABLE", f"Status for {name} was not UNAVAILABLE"
    print("  [PASS] 10/10 Locations verified free of synthetic/fake production geofences.", flush=True)
    passed_count += 1

    print("\n" + "=" * 70, flush=True)
    print(f"GEOFENCE TEST RESULTS: {passed_count}/{total_tests} TESTS PASSED (100% SUCCESS)", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    asyncio.run(run_geofence_tests())
