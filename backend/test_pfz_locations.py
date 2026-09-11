import urllib.request
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

test_locations = [
    ('Mumbai', 18.95, 72.80),
    ('Goa', 15.4989, 73.8278),
    ('Chennai', 13.0827, 80.2707),
    ('Kochi', 9.9312, 76.2673)
]

for name, lat, lon in test_locations:
    # Test GET /api/pfz
    pfz_url = f'http://localhost:8000/api/pfz?lat={lat}&lon={lon}'
    req = urllib.request.urlopen(pfz_url)
    data = json.loads(req.read().decode())
    nearest = data.get('nearest_advisory')
    lines = data.get('pfz_lines', [])
    print(f'=== {name} ({lat}, {lon}) ===')
    print(f'  Available: {data["available"]}')
    if nearest:
        print(f'  Nearest LC: {nearest["landing_center"]} ({nearest["district"]}) - Dist from query: {nearest["distance_from_query_km"]} km')
        print(f'  PFZ Vector: {nearest["advisory_distance_from_km"]}-{nearest["advisory_distance_to_km"]} km {nearest["direction"]} (Bearing: {nearest["bearing_degrees"]}°)')
        print(f'  Depth Range: {nearest["depth_from_m"]}-{nearest["depth_to_m"]} m | Validity: {nearest["validity_date"]}')
        print(f'  Target DMS: {nearest["target_dms"]}')
    else:
        print('  No landing centre advisory in radius.')
    print(f'  PFZ Lines Count: {len(lines)}')
    if lines:
        print(f'  Closest Line UID: {lines[0]["uid"]} ({lines[0]["state_name"]}) - Dist: {lines[0]["distance_km"]} km - Length: {lines[0]["length_km"]} km')

    # Test POST /api/ask with PFZ query
    ask_req = urllib.request.Request(
        'http://localhost:8000/api/ask',
        data=json.dumps({'query': f'Where is the nearest PFZ near {name}?', 'lat': lat, 'lon': lon, 'location_name': name}).encode(),
        headers={'Content-Type': 'application/json'}
    )
    ask_res = urllib.request.urlopen(ask_req)
    ask_data = json.loads(ask_res.read().decode())
    print(f'  Ask ORCA Intent: {ask_data.get("intent")}')
    print(f'  Ask ORCA Content:\n    ' + ask_data.get('content', '').replace('\n', '\n    '))
    print()
