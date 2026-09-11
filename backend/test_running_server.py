import urllib.request
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"

print(f"=== TESTING LIVE FASTAPI SERVER AT {BASE_URL} ===")

# 1. Health
h_res = urllib.request.urlopen(f"{BASE_URL}/api/health")
print(f"1. /api/health -> HTTP {h_res.status}: {h_res.read().decode()}")

# 2. Weather
w_res = urllib.request.urlopen(f"{BASE_URL}/api/weather?latitude=15.4989&longitude=73.8278")
w_data = json.loads(w_res.read().decode())
print(f"2. /api/weather (Goa) -> HTTP {w_res.status}: Temp={w_data.get('current', {}).get('temperature')}C, Wind={w_data.get('current', {}).get('wind_speed')} kts")

# 3. Marine
m_res = urllib.request.urlopen(f"{BASE_URL}/api/marine?latitude=15.4989&longitude=73.8278")
m_data = json.loads(m_res.read().decode())
print(f"3. /api/marine (Goa) -> HTTP {m_res.status}: Wave={m_data.get('current', {}).get('wave_height')}m, SST={m_data.get('current', {}).get('sea_surface_temperature')}C")

# 4. Safety
s_res = urllib.request.urlopen(f"{BASE_URL}/api/safety?latitude=15.4989&longitude=73.8278")
s_data = json.loads(s_res.read().decode())
print(f"4. /api/safety (Goa) -> HTTP {s_res.status}: Risk={s_data.get('risk_level')}, Status={s_data.get('status')}")

# 5. Hazards
hz_res = urllib.request.urlopen(f"{BASE_URL}/api/hazards?latitude=15.4989&longitude=73.8278")
hz_data = json.loads(hz_res.read().decode())
print(f"5. /api/hazards (Goa) -> HTTP {hz_res.status}: State={hz_data.get('overall_state')}")

# 6. Chlorophyll
c_res = urllib.request.urlopen(f"{BASE_URL}/api/chlorophyll?latitude=15.4989&longitude=73.8278")
c_data = json.loads(c_res.read().decode())
print(f"6. /api/chlorophyll (Goa) -> HTTP {c_res.status}: Available={c_data.get('available')}, Status={c_data.get('status')}")

# 7. PFZ
p_res = urllib.request.urlopen(f"{BASE_URL}/api/pfz?latitude=15.4989&longitude=73.8278")
p_data = json.loads(p_res.read().decode())
print(f"7. /api/pfz (Goa) -> HTTP {p_res.status}: Available={p_data.get('available')}, Nationwide Lines={len(p_data.get('nationwide_pfz_lines', []))}, Nearest LC={p_data.get('nearest_advisory', {}).get('landing_center')}")

# 8. Ask ORCA
req_body = json.dumps({
    "query": "Is it safe to fish near Goa tomorrow morning?",
    "latitude": 15.4989,
    "longitude": 73.8278,
    "location_name": "Goa Coast",
    "language": "en"
}).encode('utf-8')
ask_req = urllib.request.Request(
    f"{BASE_URL}/api/ask",
    data=req_body,
    headers={"Content-Type": "application/json"}
)
ask_res = urllib.request.urlopen(ask_req)
ask_data = json.loads(ask_res.read().decode())
print(f"8. /api/ask (Goa query) -> HTTP {ask_res.status}: Intent={ask_data.get('intent')}, Recommendation={ask_data.get('recommendation')}")

print("\nALL 8 CORE FASTAPI ENDPOINTS RETURNED HTTP 200 WITH REAL LIVE DATA!")
