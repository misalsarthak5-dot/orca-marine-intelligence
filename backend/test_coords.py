import asyncio
from services.weather_service import get_weather_data
from services.marine_service import get_marine_data
from services.safety_service import calculate_safety_assessment

coords = [
    ('Mumbai', 19.0760, 72.8777),
    ('Ratnagiri', 16.9902, 73.3120),
    ('Goa', 15.4989, 73.8278),
    ('Mangalore', 12.9141, 74.8560),
    ('Kochi', 9.9312, 76.2673),
    ('Chennai', 13.0827, 80.2707),
    ('Visakhapatnam', 17.6868, 83.2185),
    ('Puri', 19.8135, 85.8312),
    ('Kolkata', 21.6266, 88.0645),
    ('Port Blair', 11.6234, 92.7265),
]

async def test():
    for name, lat, lon in coords:
        try:
            w = await get_weather_data(lat, lon)
            m = await get_marine_data(lat, lon)
            s = await calculate_safety_assessment(lat, lon)
            w_curr = w.get('current', {})
            m_curr = m.get('current', {})
            temp = w_curr.get('temperature')
            wind = w_curr.get('wind_speed')
            wave = m_curr.get('wave_height')
            sst = m_curr.get('sea_surface_temperature')
            risk = s.get('risk_level')
            print(f"{name:15}: Temp={temp}C, Wind={wind}kts, Wave={wave}m, SST={sst}C, Risk={risk}", flush=True)
        except Exception as e:
            print(f"{name:15}: ERROR - {e}", flush=True)

asyncio.run(test())
