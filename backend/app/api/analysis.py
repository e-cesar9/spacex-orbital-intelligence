"""Risk analysis and orbital intelligence endpoints."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.services.orbital_engine import orbital_engine
from app.services.tle_service import tle_service
from app.services.cache import cache

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
