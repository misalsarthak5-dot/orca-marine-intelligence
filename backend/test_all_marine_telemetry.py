import urllib.request
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

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

for name, lat, lon in locations:
    try:
        w_res = urllib.request.urlopen(f'http://localhost:8000/api/weather?latitude={lat}&longitude={lon}')
        w_data = json.loads(w_res.read().decode())
        m_res = urllib.request.urlopen(f'http://localhost:8000/api/marine?latitude={lat}&longitude={lon}')
        m_data = json.loads(m_res.read().decode())
        s_res = urllib.request.urlopen(f'http://localhost:8000/api/safety?latitude={lat}&longitude={lon}')
        s_data = json.loads(s_res.read().decode())
        
        wc = w_data.get('current', {})
        mc = m_data.get('current', {})
        print(f'{name} ({lat:.4f}°N, {lon:.4f}°E):')
        print(f'  Wind:   {wc.get("wind_speed")} kts {wc.get("wind_direction_compass")} (Gusts: {wc.get("wind_gusts")} kts)')
        print(f'  Waves:  {mc.get("wave_height")} m (Period: {mc.get("wave_period")} s, Swell: {mc.get("swell_wave_height")} m)')
        print(f'  SST:    {mc.get("sea_surface_temperature")} °C')
        print(f'  Precip: {wc.get("precipitation")} mm, Temp: {wc.get("temperature")} °C, Humidity: {wc.get("humidity")}%')
        print(f'  Safety: {s_data.get("risk_level")} - {s_data.get("status")} - Score: {s_data.get("risk_score")}/100')
    except Exception as e:
        print(f'Error for {name}: {e}')
    print()
