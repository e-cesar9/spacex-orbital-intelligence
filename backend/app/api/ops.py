"""Operational decision support endpoints for SpaceX-level utility."""
from fastapi import APIRouter, Query
from datetime import datetime, timedelta
from typing import Optional

from app.services.orbital_engine import orbital_engine
from app.services.tle_service import tle_service
from app.services.cache import cache

router = APIRouter(prefix="/ops", tags=["Operations"])


@router.get("/fleet/health")
async def get_fleet_health_kpis():
    """
    Fleet Health Dashboard - Key Performance Indicators
    
    Provides actionable metrics for constellation management:
    - Operational vs raising vs decaying satellites
    - Altitude anomalies requiring attention
    - TLE data freshness
    - Constellation coverage score
    """
    cache_key = "ops:fleet:health"
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    await tle_service.ensure_data_loaded()
    positions = orbital_engine.get_all_positions()
    
    if not positions:
        return {"error": "No satellite data available"}
    
    # Categorize satellites by operational status
    operational = []  # Normal altitude (520-570 km)
    raising = []      # Being raised (400-520 km)
    parking = []      # Parking orbit (>570 km)
    decaying = []     # Decaying (<400 km) - URGENT
    anomalous = []    # Unusual altitude
    
    for p in positions:
        name = tle_service.get_satellite_name(p.satellite_id) or ""
        sat_info = {
            "id": p.satellite_id,
            "name": name,
            "altitude_km": round(p.altitude, 2),
            "velocity_kms": round(p.velocity, 3)
        }
        
        if p.altitude < 350:
            sat_info["status"] = "CRITICAL"
            sat_info["action"] = "DEORBIT_IMMINENT"
            decaying.append(sat_info)
        elif p.altitude < 400:
            sat_info["status"] = "WARNING"
            sat_info["action"] = "MONITOR_DECAY"
            decaying.append(sat_info)
        elif p.altitude < 520:
            sat_info["status"] = "RAISING"
            sat_info["action"] = "CONTINUE_RAISING"
            raising.append(sat_info)
        elif p.altitude <= 570:
            sat_info["status"] = "OPERATIONAL"
            operational.append(sat_info)
        elif p.altitude <= 600:
            sat_info["status"] = "PARKING"
            parking.append(sat_info)
        else:
            sat_info["status"] = "ANOMALOUS"
            sat_info["action"] = "INVESTIGATE"
            anomalous.append(sat_info)
    
    total = len(positions)
    
    # Calculate health score (0-100)
    health_score = (len(operational) / total * 100) if total > 0 else 0
    
    # Data freshness
    tle_age_seconds = (datetime.utcnow() - tle_service.last_update).total_seconds() if tle_service.last_update else 9999
    data_fresh = tle_age_seconds < 3600
    
    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "fleet_health_score": round(health_score, 1),
        "data_freshness": {
            "tle_age_seconds": int(tle_age_seconds),
            "tle_age_human": f"{int(tle_age_seconds // 60)} minutes ago",
            "status": "FRESH" if tle_age_seconds < 1800 else "STALE" if tle_age_seconds < 7200 else "OUTDATED"
        },
        "summary": {
            "total_tracked": total,
            "operational": len(operational),
            "raising": len(raising),
            "parking": len(parking),
            "decaying": len(decaying),
            "anomalous": len(anomalous)
        },
        "percentages": {
            "operational_pct": round(len(operational) / total * 100, 1) if total else 0,
            "raising_pct": round(len(raising) / total * 100, 1) if total else 0,
            "decaying_pct": round(len(decaying) / total * 100, 1) if total else 0,
        },
        "alerts": {
            "critical_count": len([s for s in decaying if s.get("status") == "CRITICAL"]),
            "warning_count": len([s for s in decaying if s.get("status") == "WARNING"]),
            "investigate_count": len(anomalous)
        },
        "action_required": {
            "decaying_satellites": decaying[:20],  # Top 20 most urgent
            "anomalous_satellites": anomalous[:10]
        }
    }
    
    await cache.set(cache_key, result, ttl=120)
    return result


@router.get("/conjunctions/workflow")
async def get_conjunction_workflow():
    """
    Conjunction Assessment Workflow
    
    Provides decision support for conjunction events:
    - SCREEN: Low probability, monitor only
    - ASSESS: Medium probability, evaluate maneuver options
    - MITIGATE: High probability, execute avoidance maneuver
    """
    cache_key = "ops:conjunctions:workflow"
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    await tle_service.ensure_data_loaded()
    
    from app.services.conjunction_service import conjunction_service
    
    # Get CDM data
    try:
        cdm_alerts = await conjunction_service.get_cdm_alerts(
            satellite_filter="STARLINK",
            hours_ahead=168,  # 7 days
            limit=100
        )
    except:
        cdm_alerts = []
    
    # Categorize by action required
    screen = []   # Pc < 1e-5, just monitor
    assess = []   # 1e-5 <= Pc < 1e-4, evaluate options
    mitigate = [] # Pc >= 1e-4, action required
    
    for alert in cdm_alerts:
        pc = alert.get("probability", 0)
        min_range = alert.get("min_range_km", 9999)
        
        workflow_item = {
            "cdm_id": alert.get("cdm_id"),
            "tca": alert.get("tca"),
            "satellite_1": alert.get("satellite_1"),
            "satellite_2": alert.get("satellite_2"),
            "probability": pc,
            "min_range_km": min_range,
            "emergency": alert.get("emergency", False)
        }
        
        if alert.get("emergency"):
            workflow_item["action"] = "MITIGATE"
            workflow_item["recommendation"] = "Execute collision avoidance maneuver"
            workflow_item["priority"] = "CRITICAL"
            mitigate.append(workflow_item)
        elif pc >= 1e-4:
            workflow_item["action"] = "MITIGATE"
            workflow_item["recommendation"] = "Plan avoidance maneuver, notify ops"
            workflow_item["priority"] = "HIGH"
            mitigate.append(workflow_item)
        elif pc >= 1e-5:
            workflow_item["action"] = "ASSESS"
            workflow_item["recommendation"] = "Evaluate maneuver options, continue monitoring"
            workflow_item["priority"] = "MEDIUM"
            assess.append(workflow_item)
        else:
            workflow_item["action"] = "SCREEN"
            workflow_item["recommendation"] = "Continue monitoring, no action required"
            workflow_item["priority"] = "LOW"
            screen.append(workflow_item)
    
    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "lookahead_hours": 168,
        "summary": {
            "total_conjunctions": len(cdm_alerts),
            "mitigate": len(mitigate),
            "assess": len(assess),
            "screen": len(screen)
        },
        "action_required": {
            "mitigate": mitigate,
            "assess": assess[:10]  # Top 10
        },
        "monitoring": {
            "screen_count": len(screen),
            "screen_sample": screen[:5]
        },
        "workflow_status": "GREEN" if len(mitigate) == 0 else "YELLOW" if len(mitigate) < 3 else "RED"
    }
    
    await cache.set(cache_key, result, ttl=300)
    return result


@router.get("/decision/maneuver/{satellite_id}")
async def get_maneuver_recommendation(
    satellite_id: str,
    target_altitude_km: float = Query(550, ge=300, le=600)
):
    """
    Maneuver Decision Support
    
    Provides delta-V estimation and maneuver windows for altitude adjustment.
    """
    await tle_service.ensure_data_loaded()
    
    pos = orbital_engine.propagate(satellite_id)
    if not pos:
        return {"error": "Satellite not found"}
    
    import math
    
    current_alt = pos.altitude
    delta_alt = target_altitude_km - current_alt
    
    # Orbital mechanics calculations
    MU = 398600.4418  # km³/s² (Earth's gravitational parameter)
    R_EARTH = 6371
    
    r_current = R_EARTH + current_alt
    r_target = R_EARTH + target_altitude_km
    
    # Vis-viva equation for delta-V (Hohmann transfer approximation)
    v_current = math.sqrt(MU / r_current)
    v_target = math.sqrt(MU / r_target)
    
    # Hohmann transfer orbit
    a_transfer = (r_current + r_target) / 2
    v_transfer_perigee = math.sqrt(MU * (2/r_current - 1/a_transfer))
    v_transfer_apogee = math.sqrt(MU * (2/r_target - 1/a_transfer))
    
    delta_v_1 = abs(v_transfer_perigee - v_current)
    delta_v_2 = abs(v_target - v_transfer_apogee)
    total_delta_v = delta_v_1 + delta_v_2
    
    # Transfer time (half orbital period of transfer orbit)
    transfer_time_seconds = math.pi * math.sqrt(a_transfer**3 / MU)
    transfer_time_hours = transfer_time_seconds / 3600
    
    # Fuel estimation (assuming Starlink ion thruster: Isp ~1500s)
    ISP = 1500  # seconds
    G0 = 9.80665  # m/s²
    STARLINK_MASS = 260  # kg (approximate)
    
    # Tsiolkovsky rocket equation: delta_v = Isp * g0 * ln(m0/m1)
    mass_ratio = math.exp((total_delta_v * 1000) / (ISP * G0))
    fuel_required = STARLINK_MASS * (1 - 1/mass_ratio)
    
    # Maneuver windows (simplified: every orbit at optimal point)
    orbital_period_min = 2 * math.pi * math.sqrt(r_current**3 / MU) / 60
    
    windows = []
    for i in range(5):
        window_time = datetime.utcnow() + timedelta(minutes=i * orbital_period_min)
        windows.append({
            "window_start": window_time.isoformat(),
            "optimal_for": "RAISE" if delta_alt > 0 else "LOWER"
        })
    
    return {
        "satellite_id": satellite_id,
        "name": tle_service.get_satellite_name(satellite_id),
        "current_state": {
            "altitude_km": round(current_alt, 2),
            "velocity_kms": round(pos.velocity, 3),
            "orbital_period_min": round(orbital_period_min, 2)
        },
        "target": {
            "altitude_km": target_altitude_km,
            "delta_altitude_km": round(delta_alt, 2)
        },
        "maneuver_plan": {
            "maneuver_type": "HOHMANN_TRANSFER",
            "total_delta_v_ms": round(total_delta_v * 1000, 2),
            "burn_1_delta_v_ms": round(delta_v_1 * 1000, 2),
            "burn_2_delta_v_ms": round(delta_v_2 * 1000, 2),
            "transfer_time_hours": round(transfer_time_hours, 2),
            "estimated_fuel_kg": round(fuel_required, 3)
        },
        "recommendation": {
            "action": "RAISE" if delta_alt > 0 else "LOWER" if delta_alt < 0 else "MAINTAIN",
            "urgency": "HIGH" if current_alt < 400 else "NORMAL",
            "feasibility": "FEASIBLE" if fuel_required < 5 else "MARGINAL" if fuel_required < 10 else "REVIEW_REQUIRED"
        },
        "next_windows": windows
    }


@router.get("/coverage/analysis")
async def get_coverage_analysis():
    """
    Global Coverage Analysis
    
    Analyzes constellation coverage gaps and recommendations.
    """
    cache_key = "ops:coverage:analysis"
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    await tle_service.ensure_data_loaded()
    positions = orbital_engine.get_all_positions()
    
    # Divide globe into latitude bands
    bands = {
        "polar_north": {"range": (60, 90), "satellites": 0, "target": 500},
        "mid_north": {"range": (30, 60), "satellites": 0, "target": 1500},
        "tropical_north": {"range": (0, 30), "satellites": 0, "target": 1500},
        "tropical_south": {"range": (-30, 0), "satellites": 0, "target": 1500},
        "mid_south": {"range": (-60, -30), "satellites": 0, "target": 1000},
        "polar_south": {"range": (-90, -60), "satellites": 0, "target": 300}
    }
    
    for p in positions:
        for band_name, band_data in bands.items():
            if band_data["range"][0] <= p.latitude < band_data["range"][1]:
                band_data["satellites"] += 1
                break
    
    # Calculate coverage scores
    coverage_analysis = []
    total_score = 0
    
    for band_name, band_data in bands.items():
        score = min(100, (band_data["satellites"] / band_data["target"]) * 100)
        total_score += score
        
        coverage_analysis.append({
            "region": band_name.replace("_", " ").title(),
            "latitude_range": band_data["range"],
            "satellite_count": band_data["satellites"],
            "target_count": band_data["target"],
            "coverage_score": round(score, 1),
            "status": "OPTIMAL" if score >= 90 else "ADEQUATE" if score >= 70 else "NEEDS_ATTENTION"
        })
    
    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "global_coverage_score": round(total_score / len(bands), 1),
        "total_satellites": len(positions),
        "coverage_by_region": coverage_analysis,
        "recommendations": [
            r for r in coverage_analysis if r["status"] == "NEEDS_ATTENTION"
        ]
    }
    
    await cache.set(cache_key, result, ttl=300)
    return result
