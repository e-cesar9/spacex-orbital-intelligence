"""Risk analysis and orbital intelligence endpoints."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.services.orbital_engine import orbital_engine
from app.services.tle_service import tle_service
from app.services.cache import cache
from app.services.conjunction_service import (
    conjunction_service, 
    get_visible_stations, 
    get_next_passes,
    GROUND_STATIONS
)

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.get("/risk/{satellite_id}")
async def get_satellite_risk(
    satellite_id: str,
    hours_ahead: int = Query(24, ge=1, le=72)
):
    """Calculate collision risk for a specific satellite against nearby objects."""
    await tle_service.ensure_data_loaded()
    
    # Get target satellite position
    target_pos = orbital_engine.propagate(satellite_id)
    if not target_pos:
        raise HTTPException(status_code=404, detail="Satellite not found")
    
    # Find nearby satellites (within 500km altitude band)
    target_alt = target_pos.altitude
    all_ids = orbital_engine.satellite_ids
    
    nearby = []
    for other_id in all_ids:
        if other_id == satellite_id:
            continue
        
        other_pos = orbital_engine.propagate(other_id)
        if other_pos and abs(other_pos.altitude - target_alt) < 500:
            nearby.append(other_id)
    
    # Calculate risk for nearby satellites (limit to 20 for performance)
    risks = []
    for other_id in nearby[:20]:
        risk = orbital_engine.calculate_risk_score(
            satellite_id, 
            other_id, 
            hours_ahead=min(hours_ahead, 24)  # Limit for performance
        )
        if risk and risk.risk_score > 0.1:
            risks.append({
                **risk.to_dict(),
                "other_name": tle_service.get_satellite_name(other_id)
            })
    
    # Sort by risk score
    risks.sort(key=lambda x: x["risk_score"], reverse=True)
    
    return {
        "satellite_id": satellite_id,
        "name": tle_service.get_satellite_name(satellite_id),
        "altitude_km": target_alt,
        "nearby_count": len(nearby),
        "analyzed_count": min(len(nearby), 20),
        "hours_ahead": hours_ahead,
        "risks": risks[:10]  # Top 10 risks
    }


@router.get("/density")
async def get_orbital_density(
    altitude_km: float = Query(550, ge=200, le=2000),
    tolerance_km: float = Query(50, ge=10, le=200)
):
    """Analyze satellite density at a specific altitude."""
    cache_key = f"analysis:density:{altitude_km}:{tolerance_km}"
    
    # Try cache
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    await tle_service.ensure_data_loaded()
    
    result = orbital_engine.analyze_density(altitude_km, tolerance_km)
    
    # Add names to satellites
    for sat in result.get("satellites", []):
        sat["name"] = tle_service.get_satellite_name(sat["id"])
    
    # Cache for 5 minutes
    await cache.set(cache_key, result, ttl=300)
    
    return result


@router.get("/density/distribution")
async def get_altitude_distribution():
    """Get satellite distribution across altitude bands."""
    cache_key = "analysis:density:distribution"
    
    # Try cache
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    await tle_service.ensure_data_loaded()
    
    # Altitude bands (km)
    bands = [
        (200, 400, "LEO-Low"),
        (400, 600, "LEO-Mid (Starlink)"),
        (600, 800, "LEO-High"),
        (800, 1200, "LEO-Upper"),
        (1200, 2000, "MEO-Low")
    ]
    
    positions = orbital_engine.get_all_positions()
    
    distribution = []
    for low, high, name in bands:
        count = sum(1 for p in positions if low <= p.altitude < high)
        distribution.append({
            "band": name,
            "altitude_min": low,
            "altitude_max": high,
            "count": count,
            "percentage": round(count / len(positions) * 100, 2) if positions else 0
        })
    
    result = {
        "total_satellites": len(positions),
        "distribution": distribution
    }
    
    # Cache for 10 minutes
    await cache.set(cache_key, result, ttl=600)
    
    return result


@router.get("/hotspots")
async def get_collision_hotspots():
    """Identify orbital regions with high satellite density (collision hotspots)."""
    cache_key = "analysis:hotspots"
    
    # Try cache
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    await tle_service.ensure_data_loaded()
    
    positions = orbital_engine.get_all_positions()
    
    # Grid-based density analysis
    # Divide into altitude bands and latitude zones
    grid = {}
    
    for pos in positions:
        # Round to 5-degree lat zones and 50km altitude bands
        lat_zone = round(pos.latitude / 5) * 5
        alt_band = round(pos.altitude / 50) * 50
        
        key = f"{lat_zone},{alt_band}"
        if key not in grid:
            grid[key] = {
                "latitude_zone": lat_zone,
                "altitude_band": alt_band,
                "count": 0,
                "satellites": []
            }
        
        grid[key]["count"] += 1
        if len(grid[key]["satellites"]) < 5:
            grid[key]["satellites"].append(pos.satellite_id)
    
    # Find hotspots (high density cells)
    hotspots = sorted(
        [v for v in grid.values() if v["count"] >= 10],
        key=lambda x: x["count"],
        reverse=True
    )[:20]
    
    result = {
        "total_satellites": len(positions),
        "grid_cells": len(grid),
        "hotspots": hotspots
    }
    
    # Cache for 10 minutes
    await cache.set(cache_key, result, ttl=600)
    
    return result


@router.get("/constellation/health")
async def get_constellation_health():
    """Get Starlink constellation health overview by orbital shell."""
    cache_key = "analysis:constellation:health"
    
    # Try cache
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    await tle_service.ensure_data_loaded()
    
    positions = orbital_engine.get_all_positions()
    
    # Starlink orbital shells (approximate)
    shells = [
        {"name": "Shell 1 (V1.0)", "altitude": 550, "inclination": 53.0, "tolerance": 30},
        {"name": "Shell 2 (V1.5)", "altitude": 540, "inclination": 53.2, "tolerance": 20},
        {"name": "Shell 3 (Polar)", "altitude": 560, "inclination": 97.6, "tolerance": 20},
        {"name": "Shell 4 (V2 Mini)", "altitude": 525, "inclination": 43.0, "tolerance": 25},
        {"name": "Shell 5 (V2 Mini)", "altitude": 530, "inclination": 33.0, "tolerance": 25},
    ]
    
    # Count satellites per shell
    shell_stats = []
    total_operational = 0
    
    for shell in shells:
        # Filter satellites in this shell's altitude range
        in_shell = [
            p for p in positions 
            if abs(p.altitude - shell["altitude"]) <= shell["tolerance"]
        ]
        
        count = len(in_shell)
        total_operational += count
        
        # Calculate health metrics
        avg_altitude = sum(p.altitude for p in in_shell) / count if count > 0 else 0
        altitude_variance = (
            sum((p.altitude - avg_altitude) ** 2 for p in in_shell) / count 
            if count > 0 else 0
        ) ** 0.5
        
        shell_stats.append({
            "shell": shell["name"],
            "target_altitude_km": shell["altitude"],
            "target_inclination": shell["inclination"],
            "satellite_count": count,
            "avg_altitude_km": round(avg_altitude, 2),
            "altitude_std_km": round(altitude_variance, 2),
            "health_score": min(100, max(0, 100 - altitude_variance * 2))  # Simplified health
        })
    
    # Anomaly detection: satellites outside normal altitude range
    anomalies = []
    for p in positions:
        if p.altitude < 300:  # Too low, likely decaying
            anomalies.append({
                "satellite_id": p.satellite_id,
                "name": tle_service.get_satellite_name(p.satellite_id),
                "altitude_km": round(p.altitude, 2),
                "status": "DECAYING",
                "urgency": "HIGH"
            })
        elif p.altitude > 700:  # Parking/raising orbit
            anomalies.append({
                "satellite_id": p.satellite_id,
                "name": tle_service.get_satellite_name(p.satellite_id),
                "altitude_km": round(p.altitude, 2),
                "status": "RAISING",
                "urgency": "LOW"
            })
    
    result = {
        "timestamp": orbital_engine._last_propagation.isoformat() if hasattr(orbital_engine, '_last_propagation') else None,
        "total_tracked": len(positions),
        "total_operational": total_operational,
        "operational_percentage": round(total_operational / len(positions) * 100, 1) if positions else 0,
        "shells": shell_stats,
        "anomalies": anomalies[:20],  # Limit to 20
        "anomaly_count": len(anomalies)
    }
    
    # Cache for 5 minutes
    await cache.set(cache_key, result, ttl=300)
    
    return result


@router.get("/conjunctions/cdm")
async def get_cdm_conjunctions(
    satellite_filter: str = Query("STARLINK", description="Satellite name pattern"),
    hours_ahead: int = Query(72, ge=1, le=168),
    limit: int = Query(50, ge=1, le=200)
):
    """
    Get real Conjunction Data Messages (CDM) from Space-Track.
    
    CDM is the official format used by 18th Space Control Squadron
    for conjunction assessments.
    """
    cache_key = f"cdm:conjunctions:{satellite_filter}:{hours_ahead}:{limit}"
    
    # Try cache
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    try:
        alerts = await conjunction_service.get_cdm_alerts(
            satellite_filter=satellite_filter,
            hours_ahead=hours_ahead,
            limit=limit
        )
        
        result = {
            "source": "space-track.org/cdm_public",
            "satellite_filter": satellite_filter,
            "hours_ahead": hours_ahead,
            "alert_count": len(alerts),
            "alerts": alerts
        }
        
        # Cache for 10 minutes
        await cache.set(cache_key, result, ttl=600)
        
        return result
        
    except Exception as e:
        return {
            "source": "space-track.org/cdm_public",
            "error": str(e),
            "alert_count": 0,
            "alerts": []
        }


@router.get("/conjunctions/calculate")
async def calculate_conjunction(
    sat1_id: str = Query(..., description="First satellite NORAD ID"),
    sat2_id: str = Query(..., description="Second satellite NORAD ID"),
    hours_ahead: int = Query(24, ge=1, le=72)
):
    """
    Calculate Time of Closest Approach (TCA) between two satellites using SGP4.
    
    This uses orbital propagation to find when two objects will be closest.
    """
    await tle_service.ensure_data_loaded()
    
    result = conjunction_service.calculate_tca_sgp4(
        sat1_id, sat2_id, hours_ahead
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Could not calculate conjunction - satellites not found")
    
    return result


@router.get("/ground-stations")
async def list_ground_stations():
    """List all tracked ground stations."""
    return {
        "count": len(GROUND_STATIONS),
        "stations": [
            {
                "name": gs["name"],
                "latitude": gs["lat"],
                "longitude": gs["lon"],
                "min_elevation_deg": gs["min_elevation"]
            }
            for gs in GROUND_STATIONS
        ]
    }


@router.get("/ground-stations/visibility/{satellite_id}")
async def get_ground_station_visibility(satellite_id: str):
    """Get which ground stations can currently see a satellite."""
    await tle_service.ensure_data_loaded()
    
    pos = orbital_engine.propagate(satellite_id)
    if not pos:
        raise HTTPException(status_code=404, detail="Satellite not found")
    
    visible = get_visible_stations(pos.latitude, pos.longitude, pos.altitude)
    
    return {
        "satellite_id": satellite_id,
        "name": tle_service.get_satellite_name(satellite_id),
        "position": {
            "latitude": pos.latitude,
            "longitude": pos.longitude,
            "altitude_km": pos.altitude
        },
        "visible_stations": visible,
        "visible_count": len(visible)
    }


@router.get("/ground-stations/passes/{satellite_id}")
async def get_satellite_passes(
    satellite_id: str,
    station: str = Query(..., description="Ground station name"),
    hours_ahead: int = Query(24, ge=1, le=72)
):
    """Calculate upcoming passes of a satellite over a ground station."""
    await tle_service.ensure_data_loaded()
    
    passes = get_next_passes(satellite_id, station, hours_ahead)
    
    return {
        "satellite_id": satellite_id,
        "name": tle_service.get_satellite_name(satellite_id),
        "station": station,
        "hours_ahead": hours_ahead,
        "pass_count": len(passes),
        "passes": passes
    }


@router.get("/eclipse/{satellite_id}")
async def predict_eclipse(
    satellite_id: str,
    hours_ahead: int = Query(24, ge=1, le=72)
):
    """
    Predict eclipse periods for a satellite (when it's in Earth's shadow).
    
    Important for:
    - Solar panel operations
    - Thermal management
    - Battery planning
    """
    await tle_service.ensure_data_loaded()
    
    pos = orbital_engine.propagate(satellite_id)
    if not pos:
        raise HTTPException(status_code=404, detail="Satellite not found")
    
    import math
    from datetime import datetime, timedelta
    
    # Sun position (simplified - assumes sun at fixed position for demo)
    # In production, use proper ephemeris (e.g., JPL DE430)
    
    EARTH_RADIUS = 6371  # km
    
    eclipses = []
    in_eclipse = False
    eclipse_start = None
    
    steps = hours_ahead * 12  # 5-minute steps
    
    for i in range(steps):
        dt = datetime.utcnow() + timedelta(minutes=i * 5)
        sat_pos = orbital_engine.propagate(satellite_id, dt)
        
        if not sat_pos:
            continue
        
        # Simplified eclipse calculation
        # Check if satellite is behind Earth relative to Sun
        # Sun direction (simplified: assume sun at +X in ECI, varies with time of year)
        
        # Day of year affects sun position
        day_of_year = dt.timetuple().tm_yday
        sun_angle = (day_of_year / 365.25) * 2 * math.pi
        
        # Sun unit vector (simplified)
        sun_x = math.cos(sun_angle)
        sun_y = 0
        sun_z = math.sin(sun_angle) * 0.4  # Account for ecliptic tilt
        
        # Satellite position
        sat_x, sat_y, sat_z = sat_pos.x, sat_pos.y, sat_pos.z
        sat_r = math.sqrt(sat_x**2 + sat_y**2 + sat_z**2)
        
        # Dot product to check if satellite is behind Earth
        dot = (sat_x * sun_x + sat_y * sun_y + sat_z * sun_z) / sat_r
        
        # Check shadow cone
        shadow_angle = math.asin(EARTH_RADIUS / sat_r)
        is_eclipsed = dot < -math.cos(shadow_angle)
        
        if is_eclipsed and not in_eclipse:
            in_eclipse = True
            eclipse_start = dt
        elif not is_eclipsed and in_eclipse:
            in_eclipse = False
            if eclipse_start:
                duration = (dt - eclipse_start).seconds / 60
                eclipses.append({
                    "start": eclipse_start.isoformat(),
                    "end": dt.isoformat(),
                    "duration_minutes": round(duration, 1)
                })
    
    # Calculate orbital period for context
    altitude = pos.altitude
    orbital_period = 2 * math.pi * math.sqrt((EARTH_RADIUS + altitude)**3 / 398600.4) / 60  # minutes
    
    return {
        "satellite_id": satellite_id,
        "name": tle_service.get_satellite_name(satellite_id),
        "altitude_km": pos.altitude,
        "orbital_period_minutes": round(orbital_period, 2),
        "hours_ahead": hours_ahead,
        "eclipse_count": len(eclipses),
        "eclipses": eclipses,
        "note": "Simplified model - production should use JPL ephemeris"
    }


@router.get("/link-budget/{satellite_id}")
async def calculate_link_budget(
    satellite_id: str,
    ground_station: str = Query(..., description="Ground station name"),
    frequency_ghz: float = Query(12.0, ge=1, le=30, description="Downlink frequency in GHz")
):
    """
    Calculate link budget for satellite-to-ground communication.
    
    Provides:
    - Free space path loss
    - Elevation angle
    - Estimated signal strength
    """
    await tle_service.ensure_data_loaded()
    
    pos = orbital_engine.propagate(satellite_id)
    if not pos:
        raise HTTPException(status_code=404, detail="Satellite not found")
    
    # Find ground station
    station = next((gs for gs in GROUND_STATIONS if gs["name"] == ground_station), None)
    if not station:
        raise HTTPException(status_code=404, detail="Ground station not found")
    
    import math
    
    # Calculate slant range
    EARTH_RADIUS = 6371
    
    # Elevation calculation
    gs_lat = math.radians(station["lat"])
    gs_lon = math.radians(station["lon"])
    sat_lat = math.radians(pos.latitude)
    sat_lon = math.radians(pos.longitude)
    
    # Ground distance
    dlat = sat_lat - gs_lat
    dlon = sat_lon - gs_lon
    a = math.sin(dlat/2)**2 + math.cos(gs_lat) * math.cos(sat_lat) * math.sin(dlon/2)**2
    central_angle = 2 * math.asin(min(1.0, math.sqrt(a)))
    
    # Slant range (km)
    sat_r = EARTH_RADIUS + pos.altitude
    slant_range = math.sqrt(EARTH_RADIUS**2 + sat_r**2 - 2*EARTH_RADIUS*sat_r*math.cos(central_angle))
    
    # Free Space Path Loss (dB)
    # FSPL = 20*log10(d) + 20*log10(f) + 92.45 (d in km, f in GHz)
    fspl = 20 * math.log10(slant_range) + 20 * math.log10(frequency_ghz) + 92.45
    
    # Elevation angle
    elevation = math.degrees(math.asin((sat_r * math.cos(central_angle) - EARTH_RADIUS) / slant_range))
    
    # Atmospheric loss estimate (simplified)
    if elevation > 10:
        atm_loss = 0.5  # dB, minimal at high elevation
    elif elevation > 5:
        atm_loss = 1.5  # dB
    else:
        atm_loss = 3.0  # dB, significant at low elevation
    
    # Rain fade estimate (Ku-band)
    rain_fade = 2.0 if frequency_ghz > 10 else 0.5  # dB, varies with weather
    
    # Typical Starlink parameters (estimated)
    satellite_eirp = 40  # dBW
    ground_antenna_gain = 35  # dBi
    system_noise_temp = 25  # dB-K
    
    # Received power estimate
    received_power = satellite_eirp + ground_antenna_gain - fspl - atm_loss - rain_fade
    
    # Link margin (simplified)
    required_cnr = 10  # dB for typical modulation
    link_margin = received_power - system_noise_temp - required_cnr
    
    return {
        "satellite_id": satellite_id,
        "name": tle_service.get_satellite_name(satellite_id),
        "ground_station": ground_station,
        "frequency_ghz": frequency_ghz,
        "geometry": {
            "slant_range_km": round(slant_range, 2),
            "elevation_deg": round(elevation, 2),
            "satellite_altitude_km": round(pos.altitude, 2)
        },
        "losses": {
            "free_space_path_loss_db": round(fspl, 2),
            "atmospheric_loss_db": atm_loss,
            "rain_fade_db": rain_fade,
            "total_loss_db": round(fspl + atm_loss + rain_fade, 2)
        },
        "link_performance": {
            "received_power_dbw": round(received_power, 2),
            "link_margin_db": round(link_margin, 2),
            "link_status": "GOOD" if link_margin > 3 else "MARGINAL" if link_margin > 0 else "POOR"
        },
        "note": "Simplified model - actual values depend on weather, antenna, and satellite state"
    }


@router.get("/alerts")
async def get_collision_alerts(
    min_risk: float = Query(0.3, ge=0, le=1.0),
    limit: int = Query(20, ge=1, le=100)
):
    """Get active collision alerts for the constellation."""
    cache_key = f"analysis:alerts:{min_risk}:{limit}"
    
    # Try cache (short TTL for alerts)
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    await tle_service.ensure_data_loaded()
    
    positions = orbital_engine.get_all_positions()
    
    # Simplified proximity-based alerts
    # In production, this would use conjunction assessments from 18th Space Control Squadron
    alerts = []
    
    # Sample satellites for proximity check (performance)
    sample_ids = [p.satellite_id for p in positions[:500]]
    
    for i, sat_id in enumerate(sample_ids[:100]):  # Check first 100
        pos = orbital_engine.propagate(sat_id)
        if not pos:
            continue
        
        # Find close approaches
        for other_id in sample_ids[i+1:i+50]:  # Check nearby 50
            other_pos = orbital_engine.propagate(other_id)
            if not other_pos:
                continue
            
            # Simple 3D distance check
            dist = (
                (pos.position['x'] - other_pos.position['x']) ** 2 +
                (pos.position['y'] - other_pos.position['y']) ** 2 +
                (pos.position['z'] - other_pos.position['z']) ** 2
            ) ** 0.5
            
            # Alert if within 50km
            if dist < 50:
                risk_score = max(0, min(1, 1 - dist / 50))
                if risk_score >= min_risk:
                    alerts.append({
                        "satellite_1": {
                            "id": sat_id,
                            "name": tle_service.get_satellite_name(sat_id)
                        },
                        "satellite_2": {
                            "id": other_id,
                            "name": tle_service.get_satellite_name(other_id)
                        },
                        "distance_km": round(dist, 2),
                        "risk_score": round(risk_score, 3),
                        "severity": "HIGH" if risk_score > 0.7 else "MEDIUM" if risk_score > 0.4 else "LOW"
                    })
        
        if len(alerts) >= limit:
            break
    
    # Sort by risk
    alerts.sort(key=lambda x: x["risk_score"], reverse=True)
    
    result = {
        "timestamp": orbital_engine._last_propagation.isoformat() if hasattr(orbital_engine, '_last_propagation') else None,
        "alert_count": len(alerts),
        "min_risk_threshold": min_risk,
        "alerts": alerts[:limit]
    }
    
    # Cache for 2 minutes
    await cache.set(cache_key, result, ttl=120)
    
    return result


@router.post("/simulate/deorbit")
async def simulate_deorbit(
    satellite_id: str,
    delta_v: float = Query(0.1, ge=0.01, le=1.0, description="Deorbit burn delta-v in km/s")
):
    """Simulate deorbit trajectory for a satellite."""
    await tle_service.ensure_data_loaded()
    
    # Get current position
    current = orbital_engine.propagate(satellite_id)
    if not current:
        raise HTTPException(status_code=404, detail="Satellite not found")
    
    # Simplified deorbit simulation
    # In reality, this would use proper orbital mechanics
    # For now, we simulate altitude decay
    
    trajectory = []
    altitude = current.altitude
    hours = 0
    
    while altitude > 100 and hours < 720:  # 30 days max
        # Simplified decay rate based on delta-v
        decay_rate = delta_v * 10  # km per hour (simplified)
        altitude -= decay_rate
        hours += 1
        
        trajectory.append({
            "hours": hours,
            "altitude_km": max(0, altitude),
            "status": "reentering" if altitude < 120 else "deorbiting"
        })
        
        if altitude <= 0:
            break
    
    return {
        "satellite_id": satellite_id,
        "name": tle_service.get_satellite_name(satellite_id),
        "initial_altitude_km": current.altitude,
        "delta_v_kms": delta_v,
        "estimated_reentry_hours": hours,
        "trajectory_sample": trajectory[::max(1, len(trajectory)//50)]  # Sample 50 points
    }
