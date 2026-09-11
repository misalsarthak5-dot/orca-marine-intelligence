from typing import Dict, Any, List
from .weather_service import get_weather_data
from .marine_service import get_marine_data

def evaluate_risk(
    wind_speed: float,
    wave_height: float,
    precipitation: float,
    wind_gusts: float
) -> Dict[str, Any]:
    """
    Transparent rule-based marine safety evaluation for ORCA.
    Evaluates wind, waves, gusts, and rain against coastal navigation thresholds.
    """
    factors: List[Dict[str, Any]] = []

    # 1. Wave Height Factor
    if wave_height > 2.5:
        wave_risk = "HIGH"
        wave_status = "Rough seas (>2.5m)"
    elif wave_height > 1.8:
        wave_risk = "CAUTION"
        wave_status = "Moderate swell (1.8m-2.5m)"
    else:
        wave_risk = "LOW"
        wave_status = "Safe (<1.8m)"

    factors.append({
        "factor": "wave_height",
        "label": "Significant Wave Height",
        "value": f"{wave_height:.1f} m",
        "risk": wave_risk,
        "status": wave_status,
        "threshold": "Safe: <1.8m | Caution: 1.8-2.5m | High: >2.5m",
    })

    # 2. Wind Speed Factor
    if wind_speed > 22.0:
        wind_risk = "HIGH"
        wind_status = "High wind advisory (>22 kts)"
    elif wind_speed > 15.0:
        wind_risk = "CAUTION"
        wind_status = "Fresh breeze (15-22 kts)"
    else:
        wind_risk = "LOW"
        wind_status = "Gentle/Moderate breeze (<15 kts)"

    factors.append({
        "factor": "wind_speed",
        "label": "Sustained Wind Speed",
        "value": f"{wind_speed:.1f} kts",
        "risk": wind_risk,
        "status": wind_status,
        "threshold": "Safe: <15 kts | Caution: 15-22 kts | High: >22 kts",
    })

    # 3. Wind Gusts Factor
    if wind_gusts > 28.0:
        gust_risk = "HIGH"
        gust_status = "Severe squall gusts (>28 kts)"
    elif wind_gusts > 20.0:
        gust_risk = "CAUTION"
        gust_status = "Moderate gusts (20-28 kts)"
    else:
        gust_risk = "LOW"
        gust_status = "Light gusts (<20 kts)"

    factors.append({
        "factor": "wind_gusts",
        "label": "Peak Wind Gusts",
        "value": f"{wind_gusts:.1f} kts",
        "risk": gust_risk,
        "status": gust_status,
        "threshold": "Safe: <20 kts | Caution: 20-28 kts | High: >28 kts",
    })

    # 4. Precipitation Factor
    if precipitation > 5.0:
        rain_risk = "HIGH"
        rain_status = "Heavy precipitation (>5mm/hr)"
    elif precipitation > 1.0:
        rain_risk = "CAUTION"
        rain_status = "Light to moderate rain (1-5mm/hr)"
    else:
        rain_risk = "LOW"
        rain_status = "Clear / Dry (<1mm/hr)"

    factors.append({
        "factor": "precipitation",
        "label": "Precipitation & Visibility",
        "value": f"{precipitation:.1f} mm",
        "risk": rain_risk,
        "status": rain_status,
        "threshold": "Safe: <1mm | Caution: 1-5mm | High: >5mm",
    })

    # Determine overall risk state
    all_risks = [f["risk"] for f in factors]
    if "HIGH" in all_risks:
        overall_risk = "HIGH"
        status = "HAZARDOUS CONDITIONS — DEPARTURE NOT RECOMMENDED"
        recommendation = (
            "Hazardous sea conditions detected exceeding operational safety thresholds. "
            "Small and motorized vessels are advised to postpone departure or seek safe anchorage. "
            "Verify official marine advisories before departure."
        )
    elif "CAUTION" in all_risks:
        overall_risk = "CAUTION"
        status = "CAUTION ADVISED — CONDITIONS MARGINAL"
        recommendation = (
            "Conditions show elevated wave swell or wind gusts in coastal sectors. "
            "Experienced motorized craft (>9m) may operate with heightened vigilance. "
            "Verify official marine advisories before departure."
        )
    else:
        overall_risk = "LOW"
        status = "CONDITIONS APPEAR SUITABLE"
        recommendation = (
            "Conditions appear favourable based on available environmental data. "
            "Mechanized and motorized fishing craft may proceed with standard vigilance. "
            "Verify official marine advisories before departure."
        )

    return {
        "risk_level": overall_risk,
        "status": status,
        "recommendation": recommendation,
        "factors": factors,
    }

async def calculate_safety_assessment(
    lat: float,
    lon: float,
    time_window: str = "now"
) -> Dict[str, Any]:
    """
    Combine Open-Meteo weather and marine datasets to compute transparent safety assessment.
    Supports both real-time telemetry ('now') and forecast-aware windows ('tomorrow_morning', 'tomorrow').
    Requires explicit latitude and longitude coordinates.
    """
    weather = await get_weather_data(lat, lon)
    marine = await get_marine_data(lat, lon)

    w_curr = weather.get("current", {})
    m_curr = marine.get("current", {})
    w_hourly = weather.get("hourly", {})
    m_hourly = marine.get("hourly", {})

    if time_window in ["tomorrow_morning", "tomorrow"]:
        times = w_hourly.get("time", [])
        # Determine unique dates in hourly series (times are in Asia/Kolkata timezone)
        unique_dates = []
        for t in times:
            d = t.split("T")[0] if "T" in t else ""
            if d and d not in unique_dates:
                unique_dates.append(d)

        if len(unique_dates) < 2:
            return {
                "source": "Open-Meteo & ORCA Rule-Based Engine",
                "coordinates": {"latitude": lat, "longitude": lon},
                "time_window": time_window,
                "forecast_period": "Tomorrow Forecast Unavailable",
                "risk_level": "UNKNOWN",
                "status": "FORECAST DATA UNAVAILABLE",
                "recommendation": "Hourly forecast data for tomorrow is currently unavailable from meteorological servers. Please check back shortly.",
                "factors": [],
                "metrics_snapshot": {},
                "is_forecast": True,
            }

        tomorrow_date = unique_dates[1]

        # Define hour filter for window
        if time_window == "tomorrow_morning":
            # 05:00 to 11:00 IST inclusive
            hour_start, hour_end = 5, 11
            period_label = "Tomorrow Morning (05:00–11:00 IST)"
        else:
            # Full day / daytime tomorrow: 05:00 to 19:00 IST
            hour_start, hour_end = 5, 19
            period_label = "Tomorrow (05:00–19:00 IST)"

        idx_list = []
        for i, t in enumerate(times):
            if t.startswith(tomorrow_date):
                try:
                    hour = int(t.split("T")[1].split(":")[0])
                    if hour_start <= hour <= hour_end:
                        idx_list.append(i)
                except (ValueError, IndexError):
                    pass

        if not idx_list:
            return {
                "source": "Open-Meteo & ORCA Rule-Based Engine",
                "coordinates": {"latitude": lat, "longitude": lon},
                "time_window": time_window,
                "forecast_period": period_label,
                "risk_level": "UNKNOWN",
                "status": "FORECAST WINDOW UNAVAILABLE",
                "recommendation": f"Forecast data for {period_label} is unavailable. Verify official marine advisories before departure.",
                "factors": [],
                "metrics_snapshot": {},
                "is_forecast": True,
            }

        # Extract values for the window
        wave_heights = [m_hourly.get("wave_height", [])[i] for i in idx_list if i < len(m_hourly.get("wave_height", [])) and m_hourly.get("wave_height", [])[i] is not None]
        wind_speeds = [w_hourly.get("wind_speed", [])[i] for i in idx_list if i < len(w_hourly.get("wind_speed", [])) and w_hourly.get("wind_speed", [])[i] is not None]
        wind_gusts_list = [w_hourly.get("wind_gusts", [])[i] for i in idx_list if i < len(w_hourly.get("wind_gusts", [])) and w_hourly.get("wind_gusts", [])[i] is not None]
        precips = [w_hourly.get("precipitation", [])[i] for i in idx_list if i < len(w_hourly.get("precipitation", [])) and w_hourly.get("precipitation", [])[i] is not None]
        ssts = [m_hourly.get("sea_surface_temperature", [])[i] for i in idx_list if i < len(m_hourly.get("sea_surface_temperature", [])) and m_hourly.get("sea_surface_temperature", [])[i] is not None]
        wave_periods = [m_hourly.get("wave_period", [])[i] for i in idx_list if i < len(m_hourly.get("wave_period", [])) and m_hourly.get("wave_period", [])[i] is not None]

        # Calculate representative / worst-case peak values across the window
        wave_height = max(wave_heights) if wave_heights else float(m_curr.get("wave_height") or 1.0)
        wind_speed = max(wind_speeds) if wind_speeds else float(w_curr.get("wind_speed") or 10.0)
        if wind_gusts_list:
            wind_gusts = max(wind_gusts_list)
        else:
            wind_gusts = max([w * 1.3 for w in wind_speeds]) if wind_speeds else wind_speed * 1.3
        precip = max(precips) if precips else 0.0
        sst = round(sum(ssts) / len(ssts), 1) if ssts else m_curr.get("sea_surface_temperature", 28.5)
        wave_period = round(sum(wave_periods) / len(wave_periods), 1) if wave_periods else m_curr.get("wave_period", 7.0)

        evaluation = evaluate_risk(wind_speed, wave_height, precip, wind_gusts)

        return {
            "source": "Open-Meteo Hourly Forecast & ORCA Safety Engine",
            "coordinates": {"latitude": lat, "longitude": lon},
            "time_window": time_window,
            "forecast_period": period_label,
            "forecast_date": tomorrow_date,
            "forecast_timestamps": [times[i] for i in idx_list],
            "is_forecast": True,
            "risk_level": evaluation["risk_level"],
            "status": evaluation["status"],
            "recommendation": evaluation["recommendation"],
            "factors": evaluation["factors"],
            "metrics_snapshot": {
                "wind_speed_knots": round(wind_speed, 1),
                "wind_direction": w_curr.get("wind_direction_compass", "NW"),
                "wind_gusts_knots": round(wind_gusts, 1),
                "wave_height_meters": round(wave_height, 2),
                "wave_period_seconds": wave_period,
                "sea_surface_temperature_c": sst,
                "precipitation_mm": round(precip, 1),
            },
        }

    # Default / Current Telemetry
    wind_speed = float(w_curr.get("wind_speed") or 10.0)
    wind_gusts = float(w_curr.get("wind_gusts") or wind_speed * 1.3)
    precip = float(w_curr.get("precipitation") or 0.0)
    wave_height = float(m_curr.get("wave_height") or 1.0)
    sst = m_curr.get("sea_surface_temperature")

    evaluation = evaluate_risk(wind_speed, wave_height, precip, wind_gusts)

    return {
        "source": "Open-Meteo Current & ORCA Rule-Based Engine",
        "coordinates": {"latitude": lat, "longitude": lon},
        "time_window": "now",
        "forecast_period": "Current Telemetry",
        "is_forecast": False,
        "risk_level": evaluation["risk_level"],
        "status": evaluation["status"],
        "recommendation": evaluation["recommendation"],
        "factors": evaluation["factors"],
        "metrics_snapshot": {
            "wind_speed_knots": round(wind_speed, 1),
            "wind_direction": w_curr.get("wind_direction_compass"),
            "wind_gusts_knots": round(wind_gusts, 1),
            "wave_height_meters": round(wave_height, 2),
            "wave_period_seconds": m_curr.get("wave_period"),
            "sea_surface_temperature_c": sst,
            "precipitation_mm": round(precip, 1),
        },
    }
