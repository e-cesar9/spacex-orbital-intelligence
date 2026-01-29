"""Satellite API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.services.orbital_engine import orbital_engine
from app.services.tle_service import tle_service
from app.services.spacex_api import spacex_client
from app.services.cache import cache
from app.services.mock_satellites import mock_generator

router = APIRouter(prefix="/satellites", tags=["Satellites"])


@router.get("")
async def list_satellites(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """List all tracked satellites with current positions."""
    # Ensure TLE data is loaded
    await tle_service.ensure_data_loaded()
    
    # Get all satellite IDs
    all_ids = orbital_engine.satellite_ids
    total = len(all_ids)
    
    # Paginate
    page_ids = all_ids[offset:offset + limit]
    
    # Get current positions
    satellites = []
    for sat_id in page_ids:
        pos = orbital_engine.propagate(sat_id)
        if pos:
            satellites.append({
                **pos.to_dict(),
                "name": tle_service.get_satellite_name(sat_id)
            })
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "satellites": satellites
    }


@router.get("/positions")
async def get_all_positions():
    """Get current positions of all satellites (optimized for 3D visualization)."""
    cache_key = "satellites:positions:all"
    
    # Try cache first
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    # Check if TLE data already loaded (don't wait for fetch)
    positions = []
    if orbital_engine.satellite_count > 0:
        positions = orbital_engine.get_all_positions()
    
    # Use mock data if no TLE data available (fast path)
    if not positions:
        mock_positions = mock_generator.get_all_positions()
        result = {
            "count": len(mock_positions),
            "source": "simulated",
            "positions": mock_positions
        }
    else:
        # Compact format for visualization
        result = {
            "count": len(positions),
            "source": "tle",
            "positions": [
                {
                    "id": p.satellite_id,
                    "lat": round(p.latitude, 4),
                    "lon": round(p.longitude, 4),
                    "alt": round(p.altitude, 2),
                    "v": round(p.velocity, 3)
                }
                for p in positions
            ]
        }
    
    # Cache for 5 seconds
    await cache.set(cache_key, result, ttl=5)
    
    return result


@router.get("/{satellite_id}")
async def get_satellite(satellite_id: str):
    """Get detailed information for a specific satellite."""
    await tle_service.ensure_data_loaded()
    
    pos = orbital_engine.propagate(satellite_id)
    if not pos:
        raise HTTPException(status_code=404, detail="Satellite not found")
    
    tle = tle_service.get_tle(satellite_id)
    
    return {
        **pos.to_dict(),
        "name": tle_service.get_satellite_name(satellite_id),
        "tle": {
            "line1": tle[0] if tle else None,
            "line2": tle[1] if tle else None
        }
    }


@router.get("/{satellite_id}/orbit")
async def get_satellite_orbit(
    satellite_id: str,
    hours: int = Query(24, ge=1, le=168),
    step_minutes: int = Query(5, ge=1, le=60)
):
    """Get orbital path for visualization."""
    cache_key = f"satellites:orbit:{satellite_id}:{hours}:{step_minutes}"
    
    # Try cache
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    # Try TLE data first
    try:
        await tle_service.ensure_data_loaded()
        positions = orbital_engine.propagate_orbit(satellite_id, hours, step_minutes)
    except Exception:
        positions = []
    
    if positions:
        result = {
            "satellite_id": satellite_id,
            "name": tle_service.get_satellite_name(satellite_id),
            "hours": hours,
            "step_minutes": step_minutes,
            "points": len(positions),
            "source": "tle",
            "orbit": [
                {
                    "t": p.timestamp.isoformat(),
                    "lat": round(p.latitude, 4),
                    "lon": round(p.longitude, 4),
                    "alt": round(p.altitude, 2)
                }
                for p in positions
            ]
        }
    else:
        # Fall back to mock data
        steps = (hours * 60) // step_minutes
        path = mock_generator.get_orbit_path(satellite_id, hours, steps)
        if not path:
            raise HTTPException(status_code=404, detail="Satellite not found")
        
        result = {
            "satellite_id": satellite_id,
            "name": satellite_id,
            "hours": hours,
            "step_minutes": step_minutes,
            "points": len(path),
            "source": "simulated",
            "orbit": path
        }
    
    # Cache for 5 minutes
    await cache.set(cache_key, result, ttl=300)
    
    return result


@router.get("/starlink/metadata")
async def get_starlink_metadata(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """Get Starlink satellite metadata from SpaceX API."""
    cache_key = f"starlink:metadata:{limit}:{offset}"
    
    # Try cache
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    satellites = await spacex_client.get_starlink_satellites(limit, offset)
    
    result = {
        "count": len(satellites),
        "limit": limit,
        "offset": offset,
        "satellites": [s.to_dict() for s in satellites]
    }
    
    # Cache for 10 minutes
    await cache.set(cache_key, result, ttl=600)
    
    return result
