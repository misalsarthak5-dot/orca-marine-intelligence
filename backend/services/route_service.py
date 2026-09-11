import math
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from .weather_service import get_weather_data
from .marine_service import get_marine_data
from .geofence_service import evaluate_route_geofences

# Fixed speed assumption for decision support MVP
VESSEL_SPEED_KNOTS = 8.0
VESSEL_SPEED_KMH = VESSEL_SPEED_KNOTS * 1.852  # ~14.816 km/h

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points on Earth in kilometers."""
    R = 6371.0  # Earth's radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def calculate_total_path_distance(coords: List[Tuple[float, float]]) -> float:
    """Compute cumulative distance along a list of (lat, lon) coordinates in km."""
    total = 0.0
    for i in range(len(coords) - 1):
        total += haversine_distance(coords[i][0], coords[i][1], coords[i + 1][0], coords[i + 1][1])
    return round(total, 2)

def generate_corridor_coordinates(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    num_points: int = 7,
    offset_ratio: float = 0.0,
) -> List[List[float]]:
    """
    Geospatially interpolate intermediate route coordinates between origin and destination.
    When offset_ratio != 0, applies a smooth parabolic perpendicular offset:
    offset = offset_ratio * distance * 4 * t * (1 - t)
    """
    total_dist = haversine_distance(origin_lat, origin_lon, dest_lat, dest_lon)
    d_lat = dest_lat - origin_lat
    d_lon = dest_lon - origin_lon

    # Compute perpendicular unit vector in latitude/longitude space
    norm = math.sqrt(d_lat * d_lat + d_lon * d_lon)
    if norm == 0:
        perp_lat = 0.0
        perp_lon = 0.0
    else:
        perp_lat = -d_lon / norm
        perp_lon = d_lat / norm

    # Maximum lateral offset in approximate geographic degrees (~111 km per deg)
    max_offset_deg = (total_dist * offset_ratio) / 111.0

    path = []
    for i in range(num_points):
        t = i / float(num_points - 1)
        # Linear interpolation
        base_lat = origin_lat + t * d_lat
        base_lon = origin_lon + t * d_lon

        # Parabolic bell curve factor (0 at t=0 and t=1, 1 at t=0.5)
        curve_factor = 4.0 * t * (1.0 - t)
        offset_lat = perp_lat * max_offset_deg * curve_factor
        offset_lon = perp_lon * max_offset_deg * curve_factor

        final_lat = round(base_lat + offset_lat, 5)
        final_lon = round(base_lon + offset_lon, 5)
        path.append([final_lat, final_lon])

    return path

_point_telemetry_cache: Dict[Tuple[float, float, str], Dict[str, Any]] = {}

async def sample_point_telemetry(lat: float, lon: float, time_window: str = "tomorrow_morning") -> Dict[str, Any]:
    """
    Sample marine wave, swell, and atmospheric weather conditions for a single coordinate point.
    Extracts telemetry aligned with the requested time_window (current / tomorrow_morning / tomorrow).
    """
    cache_key = (round(lat, 3), round(lon, 3), time_window)
    if cache_key in _point_telemetry_cache:
        return _point_telemetry_cache[cache_key]

    try:
        async def fetch_both():
            weather_task = get_weather_data(lat, lon)
            marine_task = get_marine_data(lat, lon)
            return await asyncio.gather(weather_task, marine_task, return_exceptions=True)

        weather_res, marine_res = await asyncio.wait_for(fetch_both(), timeout=6.0)

        weather = weather_res if isinstance(weather_res, dict) else {}
        marine = marine_res if isinstance(marine_res, dict) else {}

        w_curr = weather.get("current", {})
        m_curr = marine.get("current", {})
        w_hourly = weather.get("hourly", {})
        m_hourly = marine.get("hourly", {})

        wave_h = 0.9
        swell_h = 0.6
        wind_spd = 10.0
        wind_gust = 13.0
        precip = 0.0
        sst = 28.5

        if time_window in ["tomorrow_morning", "tomorrow"] and w_hourly.get("time") and m_hourly.get("time"):
            times = w_hourly.get("time", [])
            unique_dates = []
            for t in times:
                d = t.split("T")[0] if "T" in t else ""
                if d and d not in unique_dates:
                    unique_dates.append(d)

            if len(unique_dates) >= 2:
                target_date = unique_dates[1]
                hour_start, hour_end = (5, 11) if time_window == "tomorrow_morning" else (5, 19)

                idx_list = []
                for i, t in enumerate(times):
                    if t.startswith(target_date):
                        try:
                            hour = int(t.split("T")[1].split(":")[0])
                            if hour_start <= hour <= hour_end:
                                idx_list.append(i)
                        except (ValueError, IndexError):
                            pass

                if idx_list:
                    # Sample peak values in the window
                    m_waves = [m_hourly.get("wave_height", [])[i] for i in idx_list if i < len(m_hourly.get("wave_height", [])) and m_hourly.get("wave_height", [])[i] is not None]
                    m_swells = [m_hourly.get("swell_wave_height", [])[i] for i in idx_list if i < len(m_hourly.get("swell_wave_height", [])) and m_hourly.get("swell_wave_height", [])[i] is not None]
                    w_winds = [w_hourly.get("wind_speed_10m", [])[i] for i in idx_list if i < len(w_hourly.get("wind_speed_10m", [])) and w_hourly.get("wind_speed_10m", [])[i] is not None]
                    w_gusts = [w_hourly.get("wind_gusts_10m", [])[i] for i in idx_list if i < len(w_hourly.get("wind_gusts_10m", [])) and w_hourly.get("wind_gusts_10m", [])[i] is not None]
                    w_precips = [w_hourly.get("precipitation", [])[i] for i in idx_list if i < len(w_hourly.get("precipitation", [])) and w_hourly.get("precipitation", [])[i] is not None]
                    m_ssts = [m_hourly.get("sea_surface_temperature", [])[i] for i in idx_list if i < len(m_hourly.get("sea_surface_temperature", [])) and m_hourly.get("sea_surface_temperature", [])[i] is not None]

                    if m_waves:
                        wave_h = float(max(m_waves))
                    if m_swells:
                        swell_h = float(max(m_swells))
                    if w_winds:
                        wind_spd = float(max(w_winds))
                    if w_gusts:
                        wind_gust = float(max(w_gusts))
                    if w_precips:
                        precip = float(max(w_precips))
                    if m_ssts:
                        sst = float(sum(m_ssts) / len(m_ssts))
                else:
                    # Fallback to current
                    if m_curr.get("wave_height") is not None:
                        wave_h = float(m_curr["wave_height"])
                    if m_curr.get("swell_wave_height") is not None:
                        swell_h = float(m_curr["swell_wave_height"])
                    if w_curr.get("wind_speed") is not None:
                        wind_spd = float(w_curr["wind_speed"])
                    if w_curr.get("wind_gusts") is not None:
                        wind_gust = float(w_curr["wind_gusts"])
                    if w_curr.get("precipitation") is not None:
                        precip = float(w_curr["precipitation"])
                    if m_curr.get("sea_surface_temperature") is not None:
                        sst = float(m_curr["sea_surface_temperature"])
            else:
                if m_curr.get("wave_height") is not None:
                    wave_h = float(m_curr["wave_height"])
                if m_curr.get("swell_wave_height") is not None:
                    swell_h = float(m_curr["swell_wave_height"])
                if w_curr.get("wind_speed") is not None:
                    wind_spd = float(w_curr["wind_speed"])
                if w_curr.get("wind_gusts") is not None:
                    wind_gust = float(w_curr["wind_gusts"])
                if w_curr.get("precipitation") is not None:
                    precip = float(w_curr["precipitation"])
                if m_curr.get("sea_surface_temperature") is not None:
                    sst = float(m_curr["sea_surface_temperature"])
        else:
            # Current values
            if m_curr.get("wave_height") is not None:
                wave_h = float(m_curr["wave_height"])
            if m_curr.get("swell_wave_height") is not None:
                swell_h = float(m_curr["swell_wave_height"])
            if w_curr.get("wind_speed") is not None:
                wind_spd = float(w_curr["wind_speed"])
            if w_curr.get("wind_gusts") is not None:
                wind_gust = float(w_curr["wind_gusts"])
            if w_curr.get("precipitation") is not None:
                precip = float(w_curr["precipitation"])
            if m_curr.get("sea_surface_temperature") is not None:
                sst = float(m_curr["sea_surface_temperature"])

        result = {
            "lat": lat,
            "lon": lon,
            "wave_height_m": round(wave_h, 2),
            "swell_height_m": round(swell_h, 2),
            "wind_speed_kts": round(wind_spd, 1),
            "wind_gusts_kts": round(wind_gust, 1),
            "precipitation_mm": round(precip, 1),
            "sst_c": round(sst, 1),
            "is_live": True,
        }
        _point_telemetry_cache[cache_key] = result
        return result
    except Exception as e:
        fallback_res = {
            "lat": lat,
            "lon": lon,
            "wave_height_m": 0.9,
            "swell_height_m": 0.6,
            "wind_speed_kts": 10.0,
            "wind_gusts_kts": 13.0,
            "precipitation_mm": 0.0,
            "sst_c": 28.5,
            "is_live": False,
            "error": str(e),
        }
        _point_telemetry_cache[cache_key] = fallback_res
        return fallback_res

async def analyze_routes_service(
    origin_lat: float,
    origin_lon: float,
    destination_lat: float,
    destination_lon: float,
    destination_name: str = "Designated Target",
    time_window: str = "tomorrow_morning",
    override_zones: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Main Route Intelligence Service:
    Generates 3 candidate corridors (Direct, Northern, Southern), checks geofence/avoidance-zone intersections,
    samples live Open-Meteo telemetry at intermediate waypoints along each route, computes transparent risk scores,
    and recommends the optimal lower-risk viable option.
    """
    total_linear_dist = haversine_distance(origin_lat, origin_lon, destination_lat, destination_lon)
    if total_linear_dist < 0.1:
        total_linear_dist = 1.0

    num_samples = 7
    coords_direct = generate_corridor_coordinates(origin_lat, origin_lon, destination_lat, destination_lon, num_points=num_samples, offset_ratio=0.0)
    coords_north = generate_corridor_coordinates(origin_lat, origin_lon, destination_lat, destination_lon, num_points=num_samples, offset_ratio=0.12)
    coords_south = generate_corridor_coordinates(origin_lat, origin_lon, destination_lat, destination_lon, num_points=num_samples, offset_ratio=-0.12)

    # ── Gather all unique points to sample concurrently ──
    all_points = {}
    for path in [coords_direct, coords_north, coords_south]:
        for pt in path:
            key = (pt[0], pt[1])
            if key not in all_points:
                all_points[key] = sample_point_telemetry(pt[0], pt[1], time_window)

    # Concurrently execute telemetry sampling
    results = await asyncio.gather(*all_points.values())
    point_results_map = {k: v for k, v in zip(all_points.keys(), results)}

    corridors_config = [
        {
            "id": "route_1",
            "name": "Route 1 - Direct Corridor",
            "description": "Shortest direct geodesic route from departure origin to target destination.",
            "coords": coords_direct,
        },
        {
            "id": "route_2",
            "name": "Route 2 - Northern Corridor",
            "description": "Upper coastal corridor providing an offset buffer from standard direct shipping tracks.",
            "coords": coords_north,
        },
        {
            "id": "route_3",
            "name": "Route 3 - Southern Corridor",
            "description": "Lower coastal corridor navigating along offshore thermal contours.",
            "coords": coords_south,
        },
    ]

    routes = []
    for cfg in corridors_config:
        coords = cfg["coords"]
        samples = [point_results_map[(pt[0], pt[1])] for pt in coords]
        dist_km = calculate_total_path_distance([(c[0], c[1]) for c in coords])
        est_hours = round(dist_km / VESSEL_SPEED_KMH, 1)

        peak_wave = max((s.get("wave_height_m", 0.0) for s in samples), default=0.8)
        peak_swell = max((s.get("swell_height_m", 0.0) for s in samples), default=0.6)
        peak_wind = max((s.get("wind_speed_kts", 0.0) for s in samples), default=10.0)
        peak_gust = max((s.get("wind_gusts_kts", 0.0) for s in samples), default=12.0)
        peak_precip = max((s.get("precipitation_mm", 0.0) for s in samples), default=0.0)
        avg_sst = round(sum((s.get("sst_c", 28.5) for s in samples)) / max(len(samples), 1), 1)

        # ── Transparent Risk Scoring Formula (0 to 100) ──────────────
        # Base weights: Wave 35%, Swell 15%, Wind 25%, Gusts 15%, Rain 10%
        wave_score = min(100.0, (peak_wave / 2.5) * 100.0)
        swell_score = min(100.0, (peak_swell / 2.0) * 100.0)
        wind_score = min(100.0, (peak_wind / 25.0) * 100.0)
        gust_score = min(100.0, (peak_gust / 35.0) * 100.0)
        precip_score = min(100.0, (peak_precip / 15.0) * 100.0)

        calculated_risk = round(
            0.35 * wave_score + 0.15 * swell_score + 0.25 * wind_score + 0.15 * gust_score + 0.10 * precip_score
        )
        risk_score = max(8, min(95, calculated_risk))
        risk_level = "LOW" if risk_score <= 35 else "CAUTION" if risk_score <= 65 else "HIGH"

        # Highlight primary risk factors along this corridor
        risk_factors = []
        if peak_wave >= 1.8:
            risk_factors.append(f"Elevated wave swell (peak {peak_wave:.1f} m)")
        elif peak_wave >= 1.2:
            risk_factors.append(f"Moderate wave action ({peak_wave:.1f} m)")

        if peak_gust >= 20.0:
            risk_factors.append(f"Gusty conditions (peak {peak_gust:.0f} kts)")
        elif peak_wind >= 14.0:
            risk_factors.append(f"Breezy winds ({peak_wind:.0f} kts)")

        if peak_precip >= 2.0:
            risk_factors.append(f"Precipitation expected ({peak_precip:.1f} mm)")

        if not risk_factors:
            risk_factors.append("Favourable sea state and wind conditions")

        # ── Geofence Restriction Viability Evaluation ──────────────
        geofence_eval = evaluate_route_geofences(coords, override_zones=override_zones)
        restriction_status = geofence_eval["restriction_status"]
        overall_status = geofence_eval["overall_status"]
        intersecting_zones = geofence_eval["intersecting_zones"]
        geofence_note = geofence_eval["detail_message"]

        routes.append({
            "id": cfg["id"],
            "name": cfg["name"],
            "description": cfg["description"],
            "coordinates": coords,
            "sample_points": coords,
            "distance_km": dist_km,
            "estimated_time_hours": est_hours,
            "speed_assumption": f"Estimated at {VESSEL_SPEED_KNOTS} knots",
            "risk_score": risk_score,
            "risk_level": risk_level,
            "restriction_status": restriction_status,
            "overall_status": overall_status,
            "intersecting_zones": intersecting_zones,
            "geofence_note": geofence_note,
            "conditions": {
                "peak_wave_m": round(peak_wave, 2),
                "peak_swell_m": round(peak_swell, 2),
                "peak_wind_kt": round(peak_wind, 1),
                "peak_gust_kt": round(peak_gust, 1),
                "peak_precipitation_mm": round(peak_precip, 1),
                "avg_sst_c": avg_sst,
            },
            "risk_factors": risk_factors,
        })

    # ── Recommendation Decision Logic with Geofence Viability ─────
    direct_route = routes[0]
    viable_routes = [r for r in routes if r["overall_status"] != "NOT_VIABLE"]

    # If some routes are viable, select exclusively from viable routes
    candidate_pool = viable_routes if viable_routes else routes

    sorted_by_risk = sorted(candidate_pool, key=lambda r: (r["risk_score"], r["distance_km"]))
    best_candidate = sorted_by_risk[0]

    # Check if Direct Route is viable
    direct_is_viable = direct_route["overall_status"] != "NOT_VIABLE"

    if not direct_is_viable and viable_routes:
        # Direct route blocked by restriction zone, recommending lowest-risk viable detour
        recommended_route_id = best_candidate["id"]
        recommendation_reason = (
            f"{best_candidate['name']} is recommended because Direct Corridor intersects a restricted maritime zone "
            f"({', '.join(direct_route['intersecting_zones'])}). {best_candidate['name']} provides a clear alternative with "
            f"a risk score of {best_candidate['risk_score']}/100."
        )
    elif not viable_routes:
        # All routes intersect restrictions
        recommended_route_id = best_candidate["id"]
        recommendation_reason = (
            f"CAUTION: All candidate corridors intersect verified restricted zones ({', '.join(direct_route['intersecting_zones'])}). "
            f"{best_candidate['name']} has the lowest environmental risk ({best_candidate['risk_score']}/100)."
        )
    else:
        # Direct route is viable (either CLEAR or UNAVAILABLE)
        risk_diff = direct_route["risk_score"] - best_candidate["risk_score"]
        dist_diff = best_candidate["distance_km"] - direct_route["distance_km"]
        dist_pct_increase = (dist_diff / direct_route["distance_km"]) * 100 if direct_route["distance_km"] > 0 else 0

        # Unavailability disclaimer suffix if restriction data is unavailable
        geofence_suffix = (
            " Note: Restriction-zone clearance could not be verified because authoritative government restriction geometry is currently unavailable."
            if direct_route["restriction_status"] == "UNAVAILABLE"
            else " Route is verified clear of restricted maritime zones."
        )

        if best_candidate["id"] != direct_route["id"] and risk_diff >= 4 and (dist_pct_increase <= 25.0 or dist_diff <= 15.0):
            recommended_route_id = best_candidate["id"]
            recommendation_reason = (
                f"{best_candidate['name']} is recommended due to lower wave/wind exposure (risk score {best_candidate['risk_score']} vs "
                f"{direct_route['risk_score']} on Direct) while adding only {dist_diff:.1f} km transit distance.{geofence_suffix}"
            )
        else:
            recommended_route_id = direct_route["id"]
            recommendation_reason = (
                f"{direct_route['name']} is recommended as the shortest viable path ({direct_route['distance_km']} km) "
                f"with a favourable environmental risk score ({direct_route['risk_score']}/100) and peak waves under "
                f"{direct_route['conditions']['peak_wave_m']} m.{geofence_suffix}"
            )

    return {
        "available": True,
        "origin": {
            "latitude": origin_lat,
            "longitude": origin_lon,
        },
        "destination": {
            "name": destination_name,
            "latitude": destination_lat,
            "longitude": destination_lon,
            "linear_distance_km": round(total_linear_dist, 1),
        },
        "time_window": time_window,
        "routes": routes,
        "recommended_route_id": recommended_route_id,
        "recommendation_reason": recommendation_reason,
        "data_sources": [
            "Open-Meteo Marine API (Wave & Swell)",
            "Open-Meteo Forecast API (Wind & Precipitation)",
            "INCOIS GeoServer WFS (Target Landing Centres & PFZ)",
            "ORCA Geofencing & Restricted Zone Engine",
            "ORCA Decision Support Engine",
        ],
        "disclaimer": (
            "ORCA provides decision-support recommendations based on available marine and weather data. "
            "Route suggestions are not authoritative navigation instructions and do not guarantee safety. "
            "Follow official maritime advisories and local authority guidance."
        ),
    }
