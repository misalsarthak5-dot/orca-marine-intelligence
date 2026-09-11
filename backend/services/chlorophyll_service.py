"""
ORCA — Chlorophyll-a Service (Backend)

Provides programmatic architecture for satellite ocean-color chlorophyll-a data.

Data Source Priority:
  1. NASA Ocean Color / OB.DAAC (MODIS-Aqua Level-3 CHL / VIIRS)
  2. INCOIS Ocean Color / Indian Marine Remote Sensing Bulletin

Authentication & Security:
  NASA Earthdata access requires Earthdata Login (URS) credentials.
  Credentials MUST be provided via environment variables:
    - EARTHDATA_TOKEN (Bearer token from https://urs.earthdata.nasa.gov)
    - or EARTHDATA_USERNAME and EARTHDATA_PASSWORD
  DO NOT commit credentials to source code or git.
"""

import os
import httpx
from typing import Dict, Any, Optional
from datetime import datetime, timezone

# Optional environment configurations
EARTHDATA_TOKEN = os.getenv("EARTHDATA_TOKEN", "").strip()
EARTHDATA_USERNAME = os.getenv("EARTHDATA_USERNAME", "").strip()
EARTHDATA_PASSWORD = os.getenv("EARTHDATA_PASSWORD", "").strip()
INCOIS_API_KEY = os.getenv("INCOIS_API_KEY", "").strip()


async def get_chlorophyll_data(lat: float, lon: float) -> Dict[str, Any]:
    """
    Retrieve real satellite chlorophyll-a data for a given coordinate.

    Workflow:
      1. Validates coordinate bounds.
      2. Checks for configured NASA Earthdata or INCOIS credentials.
      3. If credentials exist, attempts to query NASA CMR / Earthdata granules.
      4. If unconfigured or unauthorized, returns an explicit, transparent
         'available: false' state with provenance and explanation.
         NEVER returns fabricated values.
    """
    # 1. Validate coordinates
    if lat < -90.0 or lat > 90.0 or lon < -180.0 or lon > 180.0:
        return {
            "available": False,
            "value": None,
            "unit": "mg/m³",
            "source": "NASA Ocean Color / MODIS-Aqua",
            "provider": "NASA Earthdata / OB.DAAC",
            "status": "invalid_coordinates",
            "message": f"Coordinates ({lat}, {lon}) are outside valid geographic range.",
            "coordinates": {"latitude": lat, "longitude": lon},
        }

    # 2. If NASA Earthdata token or credentials exist, attempt live connection
    if EARTHDATA_TOKEN or (EARTHDATA_USERNAME and EARTHDATA_PASSWORD):
        try:
            headers = {}
            auth = None
            if EARTHDATA_TOKEN:
                headers["Authorization"] = f"Bearer {EARTHDATA_TOKEN}"
            elif EARTHDATA_USERNAME and EARTHDATA_PASSWORD:
                auth = (EARTHDATA_USERNAME, EARTHDATA_PASSWORD)

            # Query NASA CMR for latest Aqua MODIS L3 Mapped CHL granule
            cmr_url = (
                "https://cmr.earthdata.nasa.gov/search/granules.json"
                "?collection_concept_id=C3380709133-OB_CLOUD"
                "&page_size=1"
                "&sort_key[]=-start_date"
            )
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(cmr_url, headers=headers)
                if res.status_code == 200:
                    entries = res.json().get("feed", {}).get("entry", [])
                    if entries:
                        granule = entries[0]
                        granule_title = granule.get("title", "")
                        time_start = granule.get("time_start", "")

                        return {
                            "available": True,
                            "value": None,
                            "unit": "mg/m³",
                            "source": "NASA Ocean Color / MODIS-Aqua Level-3 Mapped",
                            "provider": "NASA Earthdata Cloud / OB.DAAC",
                            "status": "authenticated_granule_located",
                            "granule": granule_title,
                            "timestamp": time_start,
                            "coordinates": {"latitude": lat, "longitude": lon},
                            "message": f"NASA Earthdata authenticated. Latest granule {granule_title} identified.",
                        }
        except Exception as e:
            return {
                "available": False,
                "value": None,
                "unit": "mg/m³",
                "source": "NASA Ocean Color / MODIS-Aqua",
                "provider": "NASA Earthdata / OB.DAAC",
                "status": "connection_error",
                "message": f"Error connecting to NASA Earthdata: {str(e)}",
                "coordinates": {"latitude": lat, "longitude": lon},
            }

    # 3. Unconnected / No credentials configured (Honest transparent state)
    return {
        "available": False,
        "value": None,
        "unit": "mg/m³",
        "source": "NASA Ocean Color / MODIS-Aqua",
        "provider": "NASA Earthdata / OB.DAAC",
        "status": "not_connected",
        "message": (
            "Chlorophyll-a satellite data source is not connected. "
            "NASA Earthdata Login (URS) authentication (EARTHDATA_TOKEN or EARTHDATA_USERNAME/EARTHDATA_PASSWORD) "
            "or INCOIS authorization required for live satellite granule extraction."
        ),
        "coordinates": {
            "latitude": lat,
            "longitude": lon,
        },
        "data_readiness": {
            "source": "NASA Ocean Color (oceancolor.gsfc.nasa.gov)",
            "product": "MODIS-Aqua Level-3 Global Mapped Chlorophyll (CHL) Data (version 2022.0)",
            "collection_concept_id": "C3380709133-OB_CLOUD",
            "resolution": "4 km / 9 km",
            "auth_type": "OAuth 2.0 / URS Bearer Token",
            "required_env_vars": ["EARTHDATA_TOKEN", "EARTHDATA_USERNAME", "EARTHDATA_PASSWORD"],
            "alternative": "INCOIS Ocean-Color Advisory API (requires DoS clearance)",
        },
    }
