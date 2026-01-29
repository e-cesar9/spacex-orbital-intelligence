"""SpaceX launches and fleet API endpoints."""
from fastapi import APIRouter, Query

from app.services.spacex_api import spacex_client
from app.services.cache import cache

router = APIRouter(prefix="/launches", tags=["Launches & Fleet"])


@router.get("")
async def list_launches(
    limit: int = Query(20, ge=1, le=100),
    upcoming: bool = Query(False)
):
    """List SpaceX launches (past or upcoming)."""
    cache_key = f"launches:list:{limit}:{upcoming}"
    
    # Try cache
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    launches = await spacex_client.get_launches(limit, upcoming)
    
    result = {
        "type": "upcoming" if upcoming else "past",
        "count": len(launches),
        "launches": [l.to_dict() for l in launches]
    }
    
    # Cache for 10 minutes
    await cache.set(cache_key, result, ttl=600)
    
    return result


@router.get("/cores")
async def list_cores(limit: int = Query(20, ge=1, le=100)):
    """List SpaceX booster cores with reuse statistics."""
    cache_key = f"cores:list:{limit}"
    
    # Try cache
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    cores = await spacex_client.get_cores(limit)
    
    # Calculate statistics
    total_reuses = sum(c.reuse_count for c in cores)
    active_cores = sum(1 for c in cores if c.status == "active")
    
    result = {
        "count": len(cores),
        "total_reuses": total_reuses,
        "active_cores": active_cores,
        "cores": [c.to_dict() for c in cores]
    }
    
    # Cache for 10 minutes
    await cache.set(cache_key, result, ttl=600)
    
    return result


@router.get("/statistics")
async def get_fleet_statistics():
    """Get overall SpaceX fleet statistics."""
    cache_key = "fleet:statistics"
    
    # Try cache
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    stats = await spacex_client.get_statistics()
    
    # Get additional stats
    launches = await spacex_client.get_launches(limit=100, upcoming=False)
    
    # Calculate success rate
    completed = [l for l in launches if l.success is not None]
    successful = [l for l in completed if l.success]
    success_rate = len(successful) / len(completed) * 100 if completed else 0
    
    # Recent launches (last 30 days)
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(days=30)
    recent = [l for l in launches if l.date_utc > cutoff]
    
    result = {
        **stats,
        "success_rate": round(success_rate, 2),
        "launches_last_30_days": len(recent),
        "recent_launches": [
            {"name": l.name, "date": l.date_utc.isoformat(), "success": l.success}
            for l in recent[:5]
        ]
    }
    
    # Cache for 30 minutes
    await cache.set(cache_key, result, ttl=1800)
    
    return result


@router.get("/timeline")
async def get_launch_timeline(
    months: int = Query(12, ge=1, le=60)
):
    """Get launch timeline for visualization."""
    cache_key = f"launches:timeline:{months}"
    
    # Try cache
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    # Get more launches for timeline
    launches = await spacex_client.get_launches(limit=100, upcoming=False)
    upcoming = await spacex_client.get_launches(limit=20, upcoming=True)
    
    # Filter by time range
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(days=months * 30)
    
    past_in_range = [
        {
            "date": l.date_utc.isoformat(),
            "name": l.name,
            "success": l.success,
            "type": "past"
        }
        for l in launches if l.date_utc > cutoff
    ]
    
    future = [
        {
            "date": l.date_utc.isoformat(),
            "name": l.name,
            "success": None,
            "type": "upcoming"
        }
        for l in upcoming
    ]
    
    # Combine and sort
    timeline = sorted(past_in_range + future, key=lambda x: x["date"])
    
    result = {
        "months": months,
        "past_count": len(past_in_range),
        "upcoming_count": len(future),
        "timeline": timeline
    }
    
    # Cache for 30 minutes
    await cache.set(cache_key, result, ttl=1800)
    
    return result
