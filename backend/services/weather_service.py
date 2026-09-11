import httpx
from typing import Dict, Any

OPEN_METEO_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

def degrees_to_compass(deg: float) -> str:
    """Convert degrees to 8-point compass bearing."""
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = round(((deg % 360) + 360) % 360 / 45) % 8
    return directions[idx]

async def get_weather_data(lat: float, lon: float) -> Dict[str, Any]:
    """
    Retrieve real atmospheric weather data from Open-Meteo Forecast API.
    Requires explicit latitude and longitude coordinates.
    No API key required.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
        ],
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
        ],
        "wind_speed_unit": "kn",
        "timezone": "Asia/Kolkata",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(OPEN_METEO_WEATHER_URL, params=params)
        response.raise_for_status()
        raw = response.json()

    current = raw.get("current", {})
    hourly = raw.get("hourly", {})
    wind_dir = current.get("wind_direction_10m", 0.0)

    return {
        "source": "Open-Meteo",
        "coordinates": {"latitude": lat, "longitude": lon},
        "current": {
            "temperature": current.get("temperature_2m"),
            "temperature_unit": "°C",
            "humidity": current.get("relative_humidity_2m"),
            "humidity_unit": "%",
            "precipitation": current.get("precipitation"),
            "precipitation_unit": "mm",
            "wind_speed": current.get("wind_speed_10m"),
            "wind_speed_unit": "kn",
            "wind_direction": wind_dir,
            "wind_direction_compass": degrees_to_compass(wind_dir),
            "wind_gusts": current.get("wind_gusts_10m"),
            "wind_gusts_unit": "kn",
            "time": current.get("time"),
        },
        "hourly": {
            "time": hourly.get("time", [])[:48],
            "temperature": hourly.get("temperature_2m", [])[:48],
            "precipitation": hourly.get("precipitation", [])[:48],
            "wind_speed": hourly.get("wind_speed_10m", [])[:48],
            "wind_direction": hourly.get("wind_direction_10m", [])[:48],
            "wind_gusts": hourly.get("wind_gusts_10m", [])[:48],
            "humidity": hourly.get("relative_humidity_2m", [])[:48],
        },
    }
