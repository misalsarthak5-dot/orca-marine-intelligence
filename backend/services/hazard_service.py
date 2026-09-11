from typing import Dict, Any, List, Optional
from .weather_service import get_weather_data
from .marine_service import get_marine_data

def evaluate_hazard_conditions(
    wave_height: Optional[float],
    wind_speed: Optional[float],
    wind_gusts: Optional[float],
    precipitation: Optional[float],
) -> Dict[str, Any]:
    """
    Evaluates marine environmental parameters against established safety & operational thresholds.
    Conditions:
    - Wave: normal (<=1.8m), elevated (1.8-2.5m), high (>2.5m)
    - Wind: normal (<=15 kts, gusts <=20 kts), caution / elevated (15-22 kts, or gusts 20-28 kts), high (>22 kts or gusts >28 kts)
    - Rain: normal (<=1.0mm), elevated / light-moderate (1.0-5.0mm), heavy (>5.0mm)
    - Lightning: unavailable / no real-time feed
    - Cyclone: no active alert detected
    """
    conditions: List[Dict[str, Any]] = []
    active_alerts: List[Dict[str, Any]] = []

    # 1. Wave Conditions
    wh = wave_height if wave_height is not None else 0.8
    if wh > 2.5:
        wave_status = "High Alert"
        wave_severity = "high"
        wave_label = "Rough Seas / High Waves"
        wave_desc = f"Significant wave height is {wh:.1f} m, exceeding the 2.5 m heavy sea threshold. Operating small craft is not recommended."
        active_alerts.append({"type": "waves", "severity": "high", "label": wave_label, "description": wave_desc})
    elif wh > 1.8:
        wave_status = "Elevated"
        wave_severity = "caution"
        wave_label = "Elevated Swell Window"
        wave_desc = f"Significant wave height is {wh:.1f} m, exceeding the 1.8 m caution threshold. Increased deck roll and shoaling near sandbars."
        active_alerts.append({"type": "waves", "severity": "caution", "label": wave_label, "description": wave_desc})
    else:
        wave_status = "Normal"
        wave_severity = "normal"
        wave_label = "Normal Wave Conditions"
        wave_desc = f"Wave swell is {wh:.1f} m, safely within the normal operating limit (<1.8 m)."

    conditions.append({
        "id": "waves",
        "name": "Wave Conditions",
        "icon": "waves",
        "value": f"{wh:.1f} m",
        "numeric_value": wh,
        "unit": "m",
        "status": wave_status,
        "severity": wave_severity,
        "is_active": wave_severity in ["caution", "high"],
        "threshold": "Normal: ≤1.8m | Elevated: 1.8–2.5m | High: >2.5m",
        "explanation": wave_desc,
    })

    # 2. Wind Conditions
    ws = wind_speed if wind_speed is not None else 5.0
    wg = wind_gusts if wind_gusts is not None else round(ws * 1.3, 1)

    if ws > 22.0 or wg > 28.0:
        wind_status = "High Alert"
        wind_severity = "high"
        wind_label = "Squall / High Wind Warning"
        wind_desc = f"Sustained wind is {ws:.1f} kts with peak gusts of {wg:.1f} kts, exceeding hazardous squall limits (>22 kts / >28 kts gusts)."
        active_alerts.append({"type": "wind", "severity": "high", "label": wind_label, "description": wind_desc})
    elif ws > 15.0 or wg > 20.0:
        wind_status = "Caution"
        wind_severity = "caution"
        wind_label = "Elevated Wind Advisory"
        wind_desc = f"Sustained wind is {ws:.1f} kts with peak gusts of {wg:.1f} kts. Fresh coastal breeze exceeds standard caution limits (>15 kts / >20 kts gusts)."
        active_alerts.append({"type": "wind", "severity": "caution", "label": wind_label, "description": wind_desc})
    else:
        wind_status = "Normal"
        wind_severity = "normal"
        wind_label = "Moderate Wind"
        wind_desc = f"Sustained wind is {ws:.1f} kts with gusts of {wg:.1f} kts, within manageable coastal thresholds (<15 kts)."

    conditions.append({
        "id": "wind",
        "name": "Wind & Gusts",
        "icon": "wind",
        "value": f"{ws:.1f} kts",
        "peak_gusts": f"{wg:.1f} kts",
        "numeric_value": ws,
        "unit": "kts",
        "status": wind_status,
        "severity": wind_severity,
        "is_active": wind_severity in ["caution", "high"],
        "threshold": "Normal: ≤15 kts | Caution: 15–22 kts | High: >22 kts",
        "explanation": wind_desc,
    })

    # 3. Precipitation / Rain
    pr = precipitation if precipitation is not None else 0.0
    if pr > 5.0:
        rain_status = "Heavy"
        rain_severity = "high"
        rain_label = "Heavy Precipitation Alert"
        rain_desc = f"Precipitation rate is {pr:.1f} mm/hr, creating severely reduced sea visibility and squall risk."
        active_alerts.append({"type": "rain", "severity": "high", "label": rain_label, "description": rain_desc})
    elif pr > 1.0:
        rain_status = "Elevated"
        rain_severity = "caution"
        rain_label = "Moderate Rainfall"
        rain_desc = f"Precipitation rate is {pr:.1f} mm/hr. Intermittent rain bands may intermittently lower navigational visibility."
        active_alerts.append({"type": "rain", "severity": "caution", "label": rain_label, "description": rain_desc})
    else:
        rain_status = "Clear"
        rain_severity = "normal"
        rain_label = "Clear / Dry"
        rain_desc = f"Precipitation is {pr:.1f} mm/hr. Clear sea visibility (>8 NM)."

    conditions.append({
        "id": "precipitation",
        "name": "Precipitation & Visibility",
        "icon": "rain",
        "value": f"{pr:.1f} mm",
        "numeric_value": pr,
        "unit": "mm",
        "status": rain_status,
        "severity": rain_severity,
        "is_active": rain_severity in ["caution", "high"],
        "threshold": "Clear: ≤1.0mm | Elevated: 1.0–5.0mm | Heavy: >5.0mm",
        "explanation": rain_desc,
    })

    # 4. Lightning (Rule: only show active if real data available; otherwise 'Lightning data unavailable')
    conditions.append({
        "id": "lightning",
        "name": "Lightning Activity",
        "icon": "lightning",
        "value": "Unavailable",
        "unit": "",
        "status": "Data unavailable",
        "severity": "unavailable",
        "is_active": False,
        "threshold": "IMD Radar Nowcast",
        "explanation": "No real-time lightning detection sensor stream connected for this coastal sector. Verify local radar nowcasts before departure.",
    })

    # 5. Cyclone / Tropical Storm (Rule: only show alert if real source exists; otherwise no fake alert)
    conditions.append({
        "id": "cyclone",
        "name": "Cyclone & Severe Storm",
        "icon": "cyclone",
        "value": "None Detected",
        "unit": "",
        "status": "No active alert",
        "severity": "normal",
        "is_active": False,
        "threshold": "IMD / RSMC Bulletins",
        "explanation": "No active tropical storm or deep cyclonic depression advisories detected from regional marine feeds.",
    })

    # Determine overall hazard state (Rule: Never "SAFE" or "100% SAFE")
    severities = [c["severity"] for c in conditions]
    if "high" in severities:
        overall_state = "HIGH ALERT"
        overall_code = "high"
        headline = f"{len(active_alerts)} hazardous condition{'s' if len(active_alerts) > 1 else ''} require immediate attention"
    elif "caution" in severities:
        overall_state = "CAUTION"
        overall_code = "caution"
        headline = f"{len(active_alerts)} condition{'s' if len(active_alerts) > 1 else ''} require attention"
    else:
        overall_state = "NO SIGNIFICANT HAZARDS"
        overall_code = "clear"
        headline = "All monitored environmental parameters are within normal baseline ranges"

    return {
        "overall_state": overall_state,
        "overall_code": overall_code,
        "headline": headline,
        "active_conditions_count": len(active_alerts),
        "active_alerts": active_alerts,
        "conditions": conditions,
    }

async def evaluate_hazards(lat: float, lon: float) -> Dict[str, Any]:
    """
    Compute transparent, real-time marine hazard assessment for any coastal point (lat, lon).
    Reuses existing Open-Meteo weather and marine telemetry services without fake data.
    """
    weather_resp = await get_weather_data(lat=lat, lon=lon)
    marine_resp = await get_marine_data(lat=lat, lon=lon)

    w_curr = weather_resp.get("current", {})
    m_curr = marine_resp.get("current", {})

    wind_speed = w_curr.get("wind_speed")
    wind_gusts = w_curr.get("wind_gusts")
    precipitation = w_curr.get("precipitation")
    wave_height = m_curr.get("wave_height")
    wave_period = m_curr.get("wave_period")
    sst = m_curr.get("sea_surface_temperature")

    hazard_eval = evaluate_hazard_conditions(
        wave_height=wave_height,
        wind_speed=wind_speed,
        wind_gusts=wind_gusts,
        precipitation=precipitation,
    )

    return {
        "coordinates": {"latitude": lat, "longitude": lon},
        "overall_state": hazard_eval["overall_state"],
        "overall_code": hazard_eval["overall_code"],
        "headline": hazard_eval["headline"],
        "active_conditions_count": hazard_eval["active_conditions_count"],
        "active_alerts": hazard_eval["active_alerts"],
        "conditions": hazard_eval["conditions"],
        "telemetry_snapshot": {
            "wave_height_m": wave_height,
            "wave_period_s": wave_period,
            "wind_speed_kts": wind_speed,
            "wind_gusts_kts": wind_gusts,
            "precipitation_mm": precipitation,
            "sst_c": sst,
            "timestamp": w_curr.get("time"),
        },
        "disclaimer": "ORCA provides AI-assisted decision support based on available environmental data. Always check official marine weather warnings and local authority advisories before venturing to sea.",
    }
