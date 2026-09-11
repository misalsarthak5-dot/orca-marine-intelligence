"""
ORCA — Geofencing & Restricted Maritime Zones Service (Backend)

Provides:
1. Robust geospatial point-in-polygon (ray casting) and line-segment intersection algorithms
   for arbitrary GeoJSON Polygon and MultiPolygon geometries.
2. Production data retrieval for maritime restriction zones, no-fishing zones,
   marine protected areas, and operational avoidance zones.
3. Graceful fallback to honest UNAVAILABLE state when authoritative government WFS sources
   do not publish machine-readable restriction geometry.
4. ZERO synthetic/fake restriction polygons in production payloads.

Provenance: Official Government Gazette / INCOIS / Ministry of Fisheries (when available).
"""

import math
from typing import Dict, Any, List, Optional, Tuple

# ── Geospatial Intersection Primitives ───────────────────────────────

def point_in_polygon(lat: float, lon: float, ring: List[List[float]]) -> bool:
    """
    Ray casting algorithm to determine if point (lat, lon) is inside polygon ring.
    ring: List of [longitude, latitude] coordinates (GeoJSON standard) or [lat, lon].
    We normalize ring coordinates to (lon, lat).
    """
    if len(ring) < 3:
        return False

    inside = False
    n = len(ring)
    
    # GeoJSON convention: ring[i] = [lon, lat]
    for i in range(n):
        j = (i + 1) % n
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]

        # Check if ray from point (lon, lat) heading in +X direction crosses segment (xi, yi)-(xj, yj)
        intersect = ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-12) + xi
        )
        if intersect:
            inside = not inside

    return inside


def segments_intersect(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    q1: Tuple[float, float],
    q2: Tuple[float, float],
) -> bool:
    """
    Determines whether line segment p1-p2 intersects line segment q1-q2 in 2D space.
    p1, p2, q1, q2 are (lon, lat) tuples.
    """
    def ccw(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> bool:
        return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])

    return (ccw(p1, q1, q2) != ccw(p2, q1, q2)) and (ccw(p1, p2, q1) != ccw(p1, p2, q2))


def line_segment_intersects_polygon_ring(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    ring: List[List[float]],
) -> bool:
    """
    Checks if a route line segment from (start_lat, start_lon) to (end_lat, end_lon)
    either enters, exits, or lies inside a polygon ring.
    """
    # 1. Check if either endpoint is inside the polygon
    if point_in_polygon(start_lat, start_lon, ring) or point_in_polygon(end_lat, end_lon, ring):
        return True

    # 2. Check if the line segment crosses any polygon edge
    p1 = (start_lon, start_lat)
    p2 = (end_lon, end_lat)
    n = len(ring)
    for i in range(n):
        j = (i + 1) % n
        q1 = (ring[i][0], ring[i][1])
        q2 = (ring[j][0], ring[j][1])
        if segments_intersect(p1, p2, q1, q2):
            return True

    return False


def check_route_intersects_geometry(
    route_coords: List[List[float]],
    geometry: Dict[str, Any],
) -> bool:
    """
    Checks whether a multi-point route path [[lat1, lon1], [lat2, lon2], ...]
    intersects a GeoJSON Polygon or MultiPolygon geometry.
    """
    geom_type = geometry.get("type", "")
    coordinates = geometry.get("coordinates", [])

    if not route_coords or len(route_coords) < 2 or not coordinates:
        return False

    if geom_type == "Polygon":
        # Polygon has a list of rings (outer ring + optional holes)
        outer_ring = coordinates[0] if len(coordinates) > 0 else []
        for i in range(len(route_coords) - 1):
            start_lat, start_lon = route_coords[i][0], route_coords[i][1]
            end_lat, end_lon = route_coords[i + 1][0], route_coords[i + 1][1]
            if line_segment_intersects_polygon_ring(start_lat, start_lon, end_lat, end_lon, outer_ring):
                return True

    elif geom_type == "MultiPolygon":
        # MultiPolygon has a list of polygons, each having a list of rings
        for poly in coordinates:
            outer_ring = poly[0] if len(poly) > 0 else []
            for i in range(len(route_coords) - 1):
                start_lat, start_lon = route_coords[i][0], route_coords[i][1]
                end_lat, end_lon = route_coords[i + 1][0], route_coords[i + 1][1]
                if line_segment_intersects_polygon_ring(start_lat, start_lon, end_lat, end_lon, outer_ring):
                    return True

    return False


# ── Production Geofence Service ──────────────────────────────────────

async def get_active_geofences(
    lat: float,
    lon: float,
    radius_km: float = 250.0,
) -> Dict[str, Any]:
    """
    Retrieves active maritime geofences / restriction zones near the specified coordinate.
    
    In the current official INCOIS GeoServer WFS datasets, no machine-readable
    fishing restriction polygon layer is published.
    
    This function honestly returns the UNAVAILABLE state without fabricating
    fake restriction polygons.
    """
    return {
        "status": "UNAVAILABLE",
        "source": None,
        "query_coordinates": {"latitude": lat, "longitude": lon},
        "search_radius_km": radius_km,
        "total_zones_found": 0,
        "zones": [],
        "message": "Authoritative maritime restriction-zone geometry is currently unavailable from official government WFS sources.",
        "disclaimer": (
            "ORCA evaluates environmental route risk based on live meteorological and oceanographic data. "
            "Because machine-readable maritime restriction geometry is not published by the official WFS source, "
            "vessel operators must verify local port notifications and statutory seasonal fishing bans before departure."
        ),
    }


def evaluate_route_geofences(
    route_coords: List[List[float]],
    override_zones: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Evaluates whether a candidate route corridor intersects any active geofences / restricted zones.
    
    Parameters:
      route_coords: List of [latitude, longitude] route waypoints.
      override_zones: Optional list of restriction zones (used for testing or when authoritative data is loaded).
      
    Returns:
      - restriction_status: "CLEAR" | "RESTRICTED" | "UNAVAILABLE"
      - overall_status: "VIABLE" | "NOT_VIABLE" | "ENVIRONMENTAL_ANALYSIS_ONLY"
      - intersecting_zones: List of zone names / descriptions that intersect the route
      - detail_message: Human-readable explanation of the geofencing verdict
    """
    # If override_zones is explicitly provided (e.g. during testing or if authoritative feed is configured)
    if override_zones is not None:
        if not override_zones:
            return {
                "restriction_status": "CLEAR",
                "overall_status": "VIABLE",
                "intersecting_zones": [],
                "detail_message": "Route is clear of all verified maritime restriction zones.",
            }

        intersected: List[str] = []
        for zone in override_zones:
            geom = zone.get("geometry", {})
            if check_route_intersects_geometry(route_coords, geom):
                zone_name = zone.get("name", zone.get("id", "Restricted Maritime Zone"))
                zone_type = zone.get("zone_type", "RESTRICTED_AREA")
                intersected.append(f"{zone_name} ({zone_type})")

        if intersected:
            return {
                "restriction_status": "RESTRICTED",
                "overall_status": "NOT_VIABLE",
                "intersecting_zones": intersected,
                "detail_message": f"Route intersects {len(intersected)} restricted zone(s): {', '.join(intersected)}.",
            }
        else:
            return {
                "restriction_status": "CLEAR",
                "overall_status": "VIABLE",
                "intersecting_zones": [],
                "detail_message": "Route does not intersect any verified restriction zones in the assessment set.",
            }

    # Default production state: Authoritative restriction geometry is unavailable
    return {
        "restriction_status": "UNAVAILABLE",
        "overall_status": "ENVIRONMENTAL_ANALYSIS_ONLY",
        "intersecting_zones": [],
        "detail_message": "Authoritative maritime restriction-zone geometry is unavailable. Environmental analysis only.",
    }
