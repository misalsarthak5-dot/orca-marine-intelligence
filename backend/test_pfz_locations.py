import asyncio
import httpx
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from main import app

test_locations = [
    ('Mumbai', 18.95, 72.80),
    ('Goa', 15.4989, 73.8278),
    ('Chennai', 13.0827, 80.2707),
    ('Kochi', 9.9312, 76.2673)
]

async def run_tests():
    # Attempt connecting to localhost:8000, fallback to in-memory ASGITransport
    use_live_server = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as check_client:
            r = await check_client.get('http://localhost:8000/docs')
            if r.status_code == 200:
                use_live_server = True
    except Exception:
        use_live_server = False

    base_url = "http://localhost:8000" if use_live_server else "http://test"
    transport = None if use_live_server else httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url=base_url, timeout=30.0) as client:
        for name, lat, lon in test_locations:
            # Test GET /api/pfz
            pfz_res = await client.get(f'/api/pfz?lat={lat}&lon={lon}')
            assert pfz_res.status_code == 200, f"PFZ request failed for {name}: {pfz_res.text}"
            data = pfz_res.json()
            nearest = data.get('nearest_advisory')
            lines = data.get('pfz_lines', [])
            print(f'=== {name} ({lat}, {lon}) ===')
            print(f'  Available: {data["available"]}')
            if nearest:
                print(f'  Nearest LC: {nearest["landing_center"]} ({nearest["district"]}) - Dist from query: {nearest["distance_from_query_km"]} km')
                print(f'  PFZ Vector: {nearest["advisory_distance_from_km"]}-{nearest["advisory_distance_to_km"]} km {nearest["direction"]} (Bearing: {nearest["bearing_degrees"]}°)')
                print(f'  Depth Range: {nearest["depth_from_m"]}-{nearest["depth_to_m"]} m | Validity: {nearest.get("validity_formatted")}')
                print(f'  Target DMS: {nearest["target_dms"]}')
            else:
                print('  No landing centre advisory in radius.')
            print(f'  PFZ Lines Count: {len(lines)}')
            if lines:
                print(f'  Closest Line UID: {lines[0]["uid"]} ({lines[0]["state_name"]}) - Dist: {lines[0]["distance_km"]} km - Length: {lines[0]["length_km"]} km')

            # Test POST /api/ask with PFZ query
            ask_res = await client.post(
                '/api/ask',
                json={'query': f'Where is the nearest PFZ near {name}?', 'lat': lat, 'lon': lon, 'location_name': name}
            )
            assert ask_res.status_code == 200, f"Ask request failed for {name}: {ask_res.text}"
            ask_data = ask_res.json()
            print(f'  Ask ORCA Intent: {ask_data.get("intent")}')
            print(f'  Ask ORCA Content:\n    ' + ask_data.get('content', '').replace('\n', '\n    '))
            print()

if __name__ == '__main__':
    asyncio.run(run_tests())
