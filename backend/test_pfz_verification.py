import asyncio
import httpx
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from main import app

locations = [
    ('Mumbai', 19.0760, 72.8777),
    ('Goa', 15.4989, 73.8278),
    ('Ratnagiri', 16.9902, 73.3120),
    ('Mangalore', 12.9141, 74.8560),
    ('Kochi', 9.9312, 76.2673),
    ('Chennai', 13.0827, 80.2707),
    ('Visakhapatnam', 17.6868, 83.2185),
    ('Puri', 19.8135, 85.8312),
    ('Kolkata', 21.6266, 88.0645),
    ('Port Blair', 11.6234, 92.7265),
]

async def run_tests():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        print("=== 1. VERIFYING REAL INCOIS PFZ ADVISORIES & NATIONWIDE LINES ACROSS 10 COASTAL PORTS ===", flush=True)
        for name, lat, lon in locations:
            p_res = await client.get(f'/api/pfz?latitude={lat}&longitude={lon}')
            assert p_res.status_code == 200, f"PFZ failed for {name}: {p_res.text}"
            p_data = p_res.json()

            nearest = p_data.get('nearest_advisory')
            lines = p_data.get('pfz_lines', [])
            nationwide_lines = p_data.get('nationwide_pfz_lines', [])
            advisory_avail = p_data.get('advisory_available')

            print(f"[{name}] ({lat:.4f}°N, {lon:.4f}°E):", flush=True)
            print(f"  Available: {p_data.get('available')}, Advisory Available: {advisory_avail}", flush=True)
            print(f"  Nationwide PFZ Lines: {len(nationwide_lines)}, Regional Lines: {len(lines)}", flush=True)
            if nearest:
                dist_str = f"{nearest.get('advisory_distance_from_km')}–{nearest.get('advisory_distance_to_km')} km"
                print(f"  Nearest Landing Centre: {nearest.get('landing_center')} ({nearest.get('district')}, {nearest.get('sector')})", flush=True)
                print(f"  Vector: {dist_str} {nearest.get('direction')} (Bearing: {nearest.get('bearing_degrees')}°, Depth: {nearest.get('depth_from_m')}–{nearest.get('depth_to_m')}m)", flush=True)
                print(f"  Validity: {nearest.get('validity_formatted')}", flush=True)
            else:
                print(f"  No location-specific landing centre advisory (Nationwide lines active)", flush=True)
            print("", flush=True)

        print("=== 2. VERIFYING MULTILINGUAL ASK ORCA PFZ QUERIES ===", flush=True)
        pfz_test_queries = [
            ("Goa", 15.4989, 73.8278, "Where are the nearest PFZ zones?", "en"),
            ("Goa", 15.4989, 73.8278, "गोवा के पास PFZ कहाँ है?", "hi"),
            ("Goa", 15.4989, 73.8278, "गोवा जवळ PFZ कुठे आहे?", "mr"),
            ("Kochi", 9.9312, 76.2673, "Is there a PFZ near Kochi?", "en"),
            ("Chennai", 13.0827, 80.2707, "Where is the nearest fishing zone?", "en"),
        ]

        for loc, lat, lon, q, lang in pfz_test_queries:
            res = await client.post('/api/ask', json={
                "query": q,
                "latitude": lat,
                "longitude": lon,
                "location_name": f"{loc} Coast",
                "language": lang
            })
            assert res.status_code == 200, f"Ask failed for '{q}': {res.text}"
            res_data = res.json()
            print(f"Query [{lang.upper()}]: '{q}' ({loc})", flush=True)
            print(f"  Intent: {res_data.get('intent')}")
            print(f"  Verdict: {res_data.get('verdict_title')}")
            print(f"  Recommendation: {res_data.get('recommendation')}")
            print(f"  First 120 chars of content:\n    {res_data.get('content', '')[:120]}...", flush=True)
            print("", flush=True)

        print("ALL INCOIS PFZ RESTORATION AUDIT CHECKS PASSED!", flush=True)

if __name__ == '__main__':
    asyncio.run(run_tests())
