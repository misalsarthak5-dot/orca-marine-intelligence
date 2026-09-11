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

async def fetch_with_retry(client, url, retries=3):
    for attempt in range(retries):
        res = await client.get(url)
        if res.status_code == 200:
            return res
        await asyncio.sleep(1.0 * (attempt + 1))
    return res

async def run_tests():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        print("=== 1. VERIFYING LIVE TELEMETRY & ADVISORIES ACROSS 10 COASTAL LOCATIONS ===", flush=True)
        for name, lat, lon in locations:
            w_res = await fetch_with_retry(client, f'/api/weather?latitude={lat}&longitude={lon}')
            m_res = await fetch_with_retry(client, f'/api/marine?latitude={lat}&longitude={lon}')
            s_res = await fetch_with_retry(client, f'/api/safety?latitude={lat}&longitude={lon}')
            h_res = await fetch_with_retry(client, f'/api/hazards?latitude={lat}&longitude={lon}')
            p_res = await fetch_with_retry(client, f'/api/pfz?latitude={lat}&longitude={lon}')

            assert w_res.status_code == 200, f"Weather failed for {name}: {w_res.text}"
            assert m_res.status_code == 200, f"Marine failed for {name}: {m_res.text}"
            assert s_res.status_code == 200, f"Safety failed for {name}: {s_res.text}"
            assert h_res.status_code == 200, f"Hazards failed for {name}: {h_res.text}"
            assert p_res.status_code == 200, f"PFZ failed for {name}: {p_res.text}"

            w_data = w_res.json()
            m_data = m_res.json()
            s_data = s_res.json()
            h_data = h_res.json()
            p_data = p_res.json()

            wc = w_data.get('current', {})
            mc = m_data.get('current', {})
            print(f"[{name}] ({lat:.4f}°N, {lon:.4f}°E)", flush=True)
            print(f"  Weather: Temp {wc.get('temperature')}°C, Wind {wc.get('wind_speed')} kts {wc.get('wind_direction_compass')}, Gusts {wc.get('wind_gusts')} kts, Precip {wc.get('precipitation')}mm", flush=True)
            print(f"  Marine:  Waves {mc.get('wave_height')}m, Swell {mc.get('swell_wave_height')}m, SST {mc.get('sea_surface_temperature')}°C", flush=True)
            print(f"  Safety:  {s_data.get('risk_level')} ({s_data.get('status')})", flush=True)
            print(f"  Hazards: Active count = {len(h_data.get('hazards', []))}", flush=True)
            print(f"  PFZ:     Zones = {len(p_data.get('zones', []))}, Status = {p_data.get('status')}, Advisory = {p_data.get('advisory_available')}", flush=True)
            print("", flush=True)
            await asyncio.sleep(0.3)

        print("=== 2. VERIFYING ASK ORCA LOCATION REASONING (MUMBAI -> GOA -> CHENNAI -> KOCHI) ===", flush=True)
        test_queries = [
            ("Mumbai", 19.0760, 72.8777, "Can I go fishing today?"),
            ("Goa", 15.4989, 73.8278, "Is it safe to sail?"),
            ("Chennai", 13.0827, 80.2707, "What is the wave height?"),
            ("Kochi", 9.9312, 76.2673, "Show nearest fishing zone"),
            ("Visakhapatnam", 17.6868, 83.2185, "Safest route to fishing ground"),
        ]

        for loc, lat, lon, q in test_queries:
            res = await client.post('/api/ask', json={
                "query": q,
                "latitude": lat,
                "longitude": lon,
                "location_name": f"{loc} Coast",
                "language": "en"
            })
            assert res.status_code == 200, f"Ask failed for {loc}: {res.text}"
            res_data = res.json()
            print(f"Query for [{loc}]: '{q}'", flush=True)
            print(f"  Resolved Location: {res_data.get('resolved_location')}", flush=True)
            print(f"  Coordinates: {res_data.get('latitude')}, {res_data.get('longitude')}", flush=True)
            print(f"  Recommendation: {res_data.get('recommendation')}", flush=True)
            print("", flush=True)

        print("=== 3. VERIFYING ZERO SILENT MUMBAI FALLBACK WHEN COORDS MISSING ===", flush=True)
        w_err = await client.get('/api/weather')
        print(f"GET /api/weather (no coords) -> HTTP {w_err.status_code}: {w_err.json().get('detail')}", flush=True)
        assert w_err.status_code == 400

        m_err = await client.get('/api/marine')
        print(f"GET /api/marine (no coords) -> HTTP {m_err.status_code}: {m_err.json().get('detail')}", flush=True)
        assert m_err.status_code == 400

        ask_err = await client.post('/api/ask', json={"query": "What is the wind speed?"})
        print(f"POST /api/ask (no coords) -> HTTP {ask_err.status_code}: {ask_err.json().get('detail')}", flush=True)
        assert ask_err.status_code == 400

        print("\nALL AUDIT VERIFICATION CHECKS PASSED WITH ZERO ERRORS!", flush=True)

if __name__ == '__main__':
    asyncio.run(run_tests())
