"""
Real Conjunction Data Messages (CDM) from Space-Track.org.

This endpoint provides ACTUAL collision screening data from the 
18th Space Defense Squadron, not simulations.

Requires Space-Track credentials:
- SPACETRACK_USER
- SPACETRACK_PASSWORD
"""
from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timezone

from app.services.spacetrack import spacetrack_client
from app.services.cache import cache

router = APIRouter(prefix="/cdm", tags=["Conjunction Data (Space-Track)"])


@router.get("/status")
async def get_cdm_status():
    """Check Space-Track integration status."""
    return {
        "service": "Space-Track.org",
        "configured": spacetrack_client.is_configured,
        "description": "18th Space Defense Squadron conjunction screening",
        "data_type": "Conjunction Data Messages (CDM)",
        "note": "Real operational data - NOT simulation" if spacetrack_client.is_configured else "Credentials not configured",
        "setup_instructions": {
            "1": "Register at https://www.space-track.org/auth/createAccount",
            "2": "Set environment variables: SPACETRACK_USER, SPACETRACK_PASSWORD",
            "3": "Restart backend"
        } if not spacetrack_client.is_configured else None
    }


@router.get("/starlink")
async def get_starlink_cdm(
    hours_ahead: int = Query(72, ge=1, le=168, description="Hours to look ahead"),
    min_probability: float = Query(1e-7, description="Minimum collision probability")
):
    """
    Get real CDM alerts for Starlink satellites.
    
    Returns actual conjunction screening data from Space-Track.org.
    This is the same data SpaceX operations uses for collision avoidance.
    """
    if not spacetrack_client.is_configured:
        return {
            "error": "Space-Track credentials not configured",
            "status": "UNAVAILABLE",
            "setup_required": True,
            "instructions": "Set SPACETRACK_USER and SPACETRACK_PASSWORD environment variables"
        }
    
    cache_key = f"cdm:starlink:{hours_ahead}:{min_probability}"
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    try:
        alerts = await spacetrack_client.get_cdm_for_starlink(
            hours_ahead=hours_ahead,
            min_probability=min_probability
        )
        
        # Categorize by risk
        critical = [a for a in alerts if a.emergency]
        high = [a for a in alerts if not a.emergency and a.probability > 1e-4]
        medium = [a for a in alerts if 1e-5 < a.probability <= 1e-4]
        low = [a for a in alerts if a.probability <= 1e-5]
        
        result = {
            "source": "Space-Track.org (18th SDS)",
            "data_type": "CDM (Conjunction Data Message)",
            "query_time": datetime.now(timezone.utc).isoformat(),
            "hours_ahead": hours_ahead,
            "filter": "STARLINK",
            "summary": {
                "total_alerts": len(alerts),
                "critical": len(critical),
                "high": len(high),
                "medium": len(medium),
                "low": len(low)
            },
            "alerts": [a.to_dict() for a in alerts],
            "note": "REAL DATA - This is actual conjunction screening data"
        }
        
        # Cache for 15 minutes
        await cache.set(cache_key, result, ttl=900)
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "source": "Space-Track.org",
            "status": "ERROR"
        }


@router.get("/all")
async def get_all_cdm(
    hours_ahead: int = Query(72, ge=1, le=168),
    limit: int = Query(50, ge=1, le=200),
    enrich: bool = Query(False, description="Include satellite catalog data")
):
    """
    Get all CDM alerts (not just Starlink).
    
    Returns highest probability conjunctions first.
    Set enrich=true to include satellite catalog metadata (country, owner, orbit params).
    """
    if not spacetrack_client.is_configured:
        return {
            "error": "Space-Track credentials not configured",
            "status": "UNAVAILABLE"
        }
    
    cache_key = f"cdm:all:{hours_ahead}:{limit}:{enrich}"
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    try:
        if enrich:
            alerts = await spacetrack_client.get_cdm_enriched(
                hours_ahead=hours_ahead,
                limit=limit
            )
        else:
            alerts = await spacetrack_client.get_all_cdm(
                hours_ahead=hours_ahead,
                limit=limit
            )
        
        # Identify Starlink involvement
        starlink_involved = [a for a in alerts if "STARLINK" in a.sat1_name.upper() or "STARLINK" in a.sat2_name.upper()]
        
        result = {
            "source": "Space-Track.org (18th SDS)",
            "query_time": datetime.now(timezone.utc).isoformat(),
            "hours_ahead": hours_ahead,
            "enriched": enrich,
            "summary": {
                "total_alerts": len(alerts),
                "starlink_involved": len(starlink_involved),
                "emergency_count": len([a for a in alerts if a.emergency])
            },
            "alerts": [a.to_dict() for a in alerts],
            "note": "Sorted by collision probability (highest first)" + (" - includes catalog data" if enrich else "")
        }
        
        await cache.set(cache_key, result, ttl=900)
        
        return result
        
    except Exception as e:
        return {"error": str(e)}


@router.get("/emergency")
async def get_emergency_alerts():
    """
    Get only EMERGENCY level alerts (Pc > 1e-4 or miss < 1km).
    
    These are alerts that typically require immediate maneuver planning.
    """
    if not spacetrack_client.is_configured:
        return {
            "error": "Space-Track credentials not configured",
            "status": "UNAVAILABLE"
        }
    
    cache_key = "cdm:emergency"
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    try:
        # Get all alerts with low threshold
        alerts = await spacetrack_client.get_all_cdm(hours_ahead=168, limit=200)
        
        # Filter to emergency only
        emergency = [a for a in alerts if a.emergency]
        
        result = {
            "source": "Space-Track.org",
            "alert_level": "EMERGENCY",
            "criteria": "Pc > 1e-4 OR miss_distance < 1km",
            "count": len(emergency),
            "alerts": [a.to_dict() for a in emergency],
            "action_required": len(emergency) > 0,
            "note": "These conjunctions typically require collision avoidance maneuvers"
        }
        
        await cache.set(cache_key, result, ttl=300)  # 5 min cache for emergency
        
        return result
        
    except Exception as e:
        return {"error": str(e)}


@router.get("/satellite/{norad_id}")
async def get_satellite_conjunctions(
    norad_id: str,
    hours_ahead: int = Query(72, ge=1, le=168)
):
    """Get CDM alerts for a specific satellite by NORAD ID."""
    if not spacetrack_client.is_configured:
        return {"error": "Space-Track credentials not configured"}
    
    # Get all alerts and filter
    alerts = await spacetrack_client.get_all_cdm(hours_ahead=hours_ahead, limit=200)
    
    # Filter for this satellite
    satellite_alerts = [
        a for a in alerts 
        if a.sat1_norad == norad_id or a.sat2_norad == norad_id
    ]
    
    return {
        "norad_id": norad_id,
        "hours_ahead": hours_ahead,
        "conjunction_count": len(satellite_alerts),
        "alerts": [a.to_dict() for a in satellite_alerts]
    }
