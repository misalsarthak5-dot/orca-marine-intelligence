import asyncio
import sys

# Ensure UTF-8 stdout on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from services.weather_service import get_weather_data
from services.marine_service import get_marine_data
from services.safety_service import calculate_safety_assessment
from services.hazard_service import evaluate_hazards
from services.pfz_service import get_pfz_assessment
from services.route_service import analyze_routes_service
from services.orca_service import process_orca_query

LOCATIONS = [
    {"id": "mumbai", "name": "Mumbai", "lat": 19.08, "lon": 72.88},
    {"id": "ratnagiri", "name": "Ratnagiri", "lat": 16.99, "lon": 73.31},
    {"id": "goa", "name": "Goa", "lat": 15.50, "lon": 73.83},
    {"id": "mangalore", "name": "Mangalore", "lat": 12.91, "lon": 74.86},
    {"id": "kochi", "name": "Kochi", "lat": 9.93, "lon": 76.27},
    {"id": "chennai", "name": "Chennai", "lat": 13.08, "lon": 80.27},
    {"id": "visakhapatnam", "name": "Visakhapatnam", "lat": 17.69, "lon": 83.22},
    {"id": "puri", "name": "Puri", "lat": 19.81, "lon": 85.83},
    {"id": "kolkata", "name": "Kolkata", "lat": 21.63, "lon": 88.06},
    {"id": "port_blair", "name": "Port Blair", "lat": 11.62, "lon": 92.73},
]

async def run_all_tests():
    print("=" * 70)
    print("ORCA 10-LOCATION SYSTEM COMPREHENSIVE VERIFICATION")
    print("=" * 70)
    
    passed_count = 0
    total_locations = len(LOCATIONS)
    
    for loc in LOCATIONS:
        name = loc["name"]
        lat = loc["lat"]
        lon = loc["lon"]
        print(f"\n[TESTING] {name.upper()} ({lat}, {lon})")
        
        try:
            # 1. Weather
            w = await get_weather_data(lat, lon)
            w_curr = w.get("current", {})
            temp = w_curr.get("temperature")
            wind = w_curr.get("wind_speed")
            print(f"  [PASS] Weather: Temp={temp} C, Wind={wind} kts", flush=True)
            
            # 2. Marine
            m = await get_marine_data(lat, lon)
            m_curr = m.get("current", {})
            wave = m_curr.get("wave_height")
            sst = m_curr.get("sea_surface_temperature")
            print(f"  [PASS] Marine: Wave={wave}m, SST={sst} C", flush=True)
            
            # 3. Safety
            s = await calculate_safety_assessment(lat, lon)
            risk = s.get("risk_level")
            print(f"  [PASS] Safety Assessment: Risk={risk}", flush=True)
            
            # 4. Hazards
            h = await evaluate_hazards(lat, lon)
            hazards_count = h.get("active_conditions_count", 0)
            print(f"  [PASS] Hazards: Active count={hazards_count}, Headline='{h.get('headline')}'", flush=True)
            
            # 5. PFZ
            pfz = await get_pfz_assessment(lat, lon)
            nearest = pfz.get("nearest_advisory")
            reg_lines = pfz.get("total_regional_lines", 0)
            nat_lines = pfz.get("total_nationwide_lines", 0)
            local_advisory_name = nearest.get("landing_center") if nearest else "None identified"
            print(f"  [PASS] PFZ: Local Advisory='{local_advisory_name}', Regional Vectors={reg_lines}, Nationwide Vectors={nat_lines}", flush=True)
            
            # 6. Route Intelligence
            if nearest:
                dest_lat = nearest.get("latitude", lat + 0.2)
                dest_lon = nearest.get("longitude", lon + 0.2)
                dest_name = f"{nearest.get('landing_center')} PFZ Target"
            else:
                dest_lat = lat + 0.15
                dest_lon = lon + 0.15
                dest_name = f"{name} Custom Waypoint"
                
            routes_res = await analyze_routes_service(
                origin_lat=lat,
                origin_lon=lon,
                destination_lat=dest_lat,
                destination_lon=dest_lon,
                destination_name=dest_name,
                time_window="current"
            )
            candidate_routes = routes_res.get("routes", [])
            rec_id = routes_res.get("recommended_route_id")
            print(f"  [PASS] Route Intelligence: Generated {len(candidate_routes)} corridors, Recommended='{rec_id}'", flush=True)
            
            # 7. Ask ORCA Query
            q_res = await process_orca_query(
                query=f"What are the marine and PFZ conditions near {name}?",
                language="en",
                lat=lat,
                lon=lon,
                location_name=name
            )
            ans = q_res.get("content", "")
            title = q_res.get("verdict_title", "")
            print(f"  [PASS] Ask ORCA: Verdict Title='{title}'", flush=True)
            print(f"         Excerpt: {ans[:90].replace(chr(10), ' ')}...", flush=True)
            
            passed_count += 1
        except Exception as e:
            print(f"  [FAIL] on {name}: {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70, flush=True)
    print(f"TEST RESULTS: {passed_count}/{total_locations} LOCATIONS PASSED SUCCESSFULLY", flush=True)
    print("=" * 70, flush=True)

if __name__ == "__main__":
    asyncio.run(run_all_tests())
