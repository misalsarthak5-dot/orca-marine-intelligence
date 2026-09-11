import httpx
from typing import Dict, Any

OPEN_METEO_MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"

def degrees_to_compass(deg: float) -> str:
    """Convert degrees to 8-point compass bearing."""
    if deg is None:
        return "N/A"
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = round(((deg % 360) + 360) % 360 / 45) % 8
    return directions[idx]

async def get_marine_data(lat: float, lon: float) -> Dict[str, Any]:
    """
    Retrieve real marine wave and sea surface temperature data from Open-Meteo Marine API.
    Requires explicit latitude and longitude coordinates.
    Uses cell_selection=sea for marine grid matching.
    No API key required.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "cell_selection": "sea",
        "current": [
            "wave_height",
            "wave_direction",
            "wave_period",
            "swell_wave_height",
            "swell_wave_period",
            "sea_surface_temperature",
        ],
        "hourly": [
            "wave_height",
            "wave_direction",
            "wave_period",
            "swell_wave_height",
            "swell_wave_period",
            "sea_surface_temperature",
        ],
        "timezone": "Asia/Kolkata",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(OPEN_METEO_MARINE_URL, params=params)
        response.raise_for_status()
        raw = response.json()

    current = raw.get("current", {})
    hourly = raw.get("hourly", {})
    wave_dir = current.get("wave_direction")

    return {
        "source": "Open-Meteo",
        "coordinates": {"latitude": lat, "longitude": lon},
        "current": {
            "wave_height": current.get("wave_height"),
            "wave_height_unit": "m",
            "wave_direction": wave_dir,
            "wave_direction_compass": degrees_to_compass(wave_dir) if wave_dir is not None else "W",
            "wave_period": current.get("wave_period"),
            "wave_period_unit": "s",
            "swell_wave_height": current.get("swell_wave_height"),
            "swell_wave_height_unit": "m",
            "swell_wave_period": current.get("swell_wave_period"),
            "swell_wave_period_unit": "s",
            "sea_surface_temperature": current.get("sea_surface_temperature"),
            "sea_surface_temperature_unit": "°C",
            "time": current.get("time"),
        },
        "hourly": {
            "time": hourly.get("time", [])[:48],
            "wave_height": hourly.get("wave_height", [])[:48],
            "wave_direction": hourly.get("wave_direction", [])[:48],
            "wave_period": hourly.get("wave_period", [])[:48],
            "swell_wave_height": hourly.get("swell_wave_height", [])[:48],
            "sea_surface_temperature": hourly.get("sea_surface_temperature", [])[:48],
        },
    }
