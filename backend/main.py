import os
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from services.weather_service import get_weather_data
from services.marine_service import get_marine_data
from services.safety_service import calculate_safety_assessment
from services.hazard_service import evaluate_hazards
from services.chlorophyll_service import get_chlorophyll_data
from services.pfz_service import get_pfz_assessment

# Load environment configuration
load_dotenv()

app = FastAPI(
    title="ORCA Marine Intelligence API",
    description="Agentic AI-Powered Marine Intelligence & Conversational Decision Support Platform (ISRO SIH 26176)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration
allowed_origins_env = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
# Ensure localhost development ports are included
for dev_origin in ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"]:
    if dev_origin not in origins:
        origins.append(dev_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from typing import Optional
from pydantic import BaseModel
from services.orca_service import process_orca_query

def parse_and_validate_coords(
    lat: Optional[float] = None,
    latitude: Optional[float] = None,
    lon: Optional[float] = None,
    longitude: Optional[float] = None,
) -> tuple[float, float]:
    """
    Validate and extract geographic coordinates from either lat/lon or latitude/longitude parameters.
    Ensures coordinates are provided and -90 <= latitude <= 90 and -180 <= longitude <= 180.
    Does NOT silently fall back to Mumbai when parameters are missing.
    """
    actual_lat = latitude if latitude is not None else lat
    actual_lon = longitude if longitude is not None else lon

    if actual_lat is None or actual_lon is None:
        raise HTTPException(
            status_code=400,
            detail="Both latitude and longitude parameters are required for live marine telemetry. Please specify coordinates."
        )

    if actual_lat < -90.0 or actual_lat > 90.0:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid latitude value: {actual_lat}. Latitude must be between -90.0 and 90.0 degrees.",
        )
    if actual_lon < -180.0 or actual_lon > 180.0:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid longitude value: {actual_lon}. Longitude must be between -180.0 and 180.0 degrees.",
        )

    return float(actual_lat), float(actual_lon)

@app.get("/api/health", tags=["System"])
async def health_check():
    """
    Health check endpoint for ORCA FastAPI backend.
    """
    return {
        "status": "ok",
        "service": "ORCA FastAPI Backend",
        "version": "1.0.0",
    }

@app.get("/api/weather", tags=["Atmospheric Weather"])
async def get_weather(
    lat: Optional[float] = Query(None, description="Latitude (alias: latitude)"),
    latitude: Optional[float] = Query(None, description="Latitude"),
    lon: Optional[float] = Query(None, description="Longitude (alias: longitude)"),
    longitude: Optional[float] = Query(None, description="Longitude"),
):
    """
    Retrieve real atmospheric weather data from Open-Meteo Forecast API.
    Accepts latitude and longitude coordinates.
    Returns current conditions (temp, humidity, wind, gusts, precipitation) and hourly forecast.
    """
    val_lat, val_lon = parse_and_validate_coords(lat, latitude, lon, longitude)
    try:
        data = await get_weather_data(lat=val_lat, lon=val_lon)
        return data
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error fetching Open-Meteo weather data: {str(e)}",
        )

@app.get("/api/marine", tags=["Marine & Oceanography"])
async def get_marine(
    lat: Optional[float] = Query(None, description="Latitude (alias: latitude)"),
    latitude: Optional[float] = Query(None, description="Latitude"),
    lon: Optional[float] = Query(None, description="Longitude (alias: longitude)"),
    longitude: Optional[float] = Query(None, description="Longitude"),
):
    """
    Retrieve real oceanographic wave and sea surface temperature data from Open-Meteo Marine API.
    Accepts latitude and longitude coordinates.
    Returns wave height, direction, period, swell, and SST with hourly forecast.
    """
    val_lat, val_lon = parse_and_validate_coords(lat, latitude, lon, longitude)
    try:
        data = await get_marine_data(lat=val_lat, lon=val_lon)
        return data
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error fetching Open-Meteo marine data: {str(e)}",
        )

@app.get("/api/safety", tags=["Decision Support"])
async def get_safety(
    lat: Optional[float] = Query(None, description="Latitude (alias: latitude)"),
    latitude: Optional[float] = Query(None, description="Latitude"),
    lon: Optional[float] = Query(None, description="Longitude (alias: longitude)"),
    longitude: Optional[float] = Query(None, description="Longitude"),
    time_window: Optional[str] = Query("now", description="Time window ('now', 'tomorrow_morning', 'tomorrow')"),
):
    """
    Compute rule-based marine safety evaluation combining real-time atmospheric and oceanographic feeds.
    Accepts latitude and longitude coordinates and optional time_window.
    Returns risk level (LOW/CAUTION/HIGH), verdict status, recommendation, and factor details.
    """
    val_lat, val_lon = parse_and_validate_coords(lat, latitude, lon, longitude)
    try:
        assessment = await calculate_safety_assessment(lat=val_lat, lon=val_lon, time_window=time_window or "now")
        return assessment
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error computing marine safety assessment: {str(e)}",
        )

@app.get("/api/hazards", tags=["Decision Support"])
async def get_hazards(
    lat: Optional[float] = Query(None, description="Latitude (alias: latitude)"),
    latitude: Optional[float] = Query(None, description="Latitude"),
    lon: Optional[float] = Query(None, description="Longitude (alias: longitude)"),
    longitude: Optional[float] = Query(None, description="Longitude"),
):
    """
    Compute transparent, real-time marine hazard & alerts evaluation for any coastal point (lat, lon).
    Reuses existing Open-Meteo atmospheric and oceanographic feeds without fake data.
    Returns overall state (NO SIGNIFICANT HAZARDS / CAUTION / HIGH ALERT), active alerts, and condition details.
    """
    val_lat, val_lon = parse_and_validate_coords(lat, latitude, lon, longitude)
    try:
        hazards = await evaluate_hazards(lat=val_lat, lon=val_lon)
        return hazards
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error computing marine hazards evaluation: {str(e)}",
        )

@app.get("/api/chlorophyll", tags=["Marine Environmental Intelligence"])
async def get_chlorophyll(
    lat: Optional[float] = Query(None, description="Latitude (alias: latitude)"),
    latitude: Optional[float] = Query(None, description="Latitude"),
    lon: Optional[float] = Query(None, description="Longitude (alias: longitude)"),
    longitude: Optional[float] = Query(None, description="Longitude"),
):
    """
    Returns chlorophyll-a (ocean color) data for a given coordinate.
    CURRENT STATUS: Satellite data source not connected.
    Returns a clearly marked unavailable result — no fabricated values.
    Future: NASA Ocean Color / MODIS-Aqua / INCOIS integration.
    """
    val_lat, val_lon = parse_and_validate_coords(lat, latitude, lon, longitude)
    try:
        data = await get_chlorophyll_data(lat=val_lat, lon=val_lon)
        return data
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error retrieving chlorophyll data: {str(e)}",
        )

@app.get("/api/pfz", tags=["Decision Support"])
async def get_pfz(
    lat: Optional[float] = Query(None, description="Latitude (alias: latitude)"),
    latitude: Optional[float] = Query(None, description="Latitude"),
    lon: Optional[float] = Query(None, description="Longitude (alias: longitude)"),
    longitude: Optional[float] = Query(None, description="Longitude"),
    radius_km: Optional[float] = Query(250.0, description="Search radius in kilometers"),
):
    """
    Retrieve real-time official INCOIS Potential Fishing Zones (PFZ) advisory data.
    Queries official INCOIS GeoServer WFS services (PFZ lines & Landing Centre vectors).
    Returns active PFZ advisories, nearest advisory vector (distance/bearing/depth),
    real MultiLineString PFZ geometries, and official validity dates.
    """
    val_lat, val_lon = parse_and_validate_coords(lat, latitude, lon, longitude)
    try:
        data = await get_pfz_assessment(lat=val_lat, lon=val_lon, max_radius_km=radius_km or 250.0)
        return data
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error retrieving official INCOIS PFZ advisory data: {str(e)}",
        )

@app.get("/api/validate-marine", tags=["Marine & Oceanography"])
async def validate_marine_point(
    lat: Optional[float] = Query(None, description="Latitude (alias: latitude)"),
    latitude: Optional[float] = Query(None, description="Latitude"),
    lon: Optional[float] = Query(None, description="Longitude (alias: longitude)"),
    longitude: Optional[float] = Query(None, description="Longitude"),
):
    """
    Validates whether a coordinate point is in the marine/ocean area.
    Returns is_marine=True if wave data exists, or False if the point is inland.
    """
    val_lat, val_lon = parse_and_validate_coords(lat, latitude, lon, longitude)
    try:
        data = await get_marine_data(lat=val_lat, lon=val_lon)
        wave_height = data.get("current", {}).get("wave_height")
        is_marine = wave_height is not None
        return {
            "is_marine": is_marine,
            "latitude": val_lat,
            "longitude": val_lon,
            "wave_height": wave_height,
        }
    except Exception:
        return {
            "is_marine": False,
            "latitude": val_lat,
            "longitude": val_lon,
            "wave_height": None,
        }

class AskRequest(BaseModel):
    query: str
    language: Optional[str] = "en"
    lat: Optional[float] = None
    latitude: Optional[float] = None
    lon: Optional[float] = None
    longitude: Optional[float] = None
    location_name: Optional[str] = None

@app.post("/api/ask", tags=["Decision Support"])
async def ask_orca(req: AskRequest):
    """
    ORCA Reasoning & Decision Support Pipeline:
    Executes Intent Detection -> Planning -> Telemetry Retrieval -> Reasoning -> Recommendation -> Map Actions.
    """
    try:
        val_lat = req.latitude if req.latitude is not None else req.lat
        val_lon = req.longitude if req.longitude is not None else req.lon
        response = await process_orca_query(
            query=req.query,
            language=req.language or "en",
            lat=val_lat,
            lon=val_lon,
            location_name=req.location_name,
        )
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error executing ORCA reasoning workflow: {str(e)}",
        )

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
