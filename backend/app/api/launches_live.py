"""Live launch data from Launch Library 2 (up-to-date)."""
from fastapi import APIRouter, Query
from datetime import datetime, timezone

from app.services.launch_library import ll2_client
from app.services.cache import cache

router = APIRouter(prefix="/launches-live", tags=["Launches (Live Data)"])


@router.get("")
async def get_live_launches(
    limit: int = Query(20, ge=1, le=50),
    upcoming: bool = Query(True),
    spacex_only: bool = Query(False)
):
    """
    Get live launch data from Launch Library 2.
    
    This endpoint provides UP-TO-DATE launch information unlike /launches 
    which uses the discontinued SpaceX API (data from 2022).
    """
    cache_key = f"ll2:launches:{limit}:{upcoming}:{spacex_only}"
    
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    try:
        if spacex_only:
            launches = await ll2_client.get_spacex_launches(limit=limit, upcoming=upcoming)
        elif upcoming:
            launches = await ll2_client.get_upcoming_launches(limit=limit)
        else:
            launches = await ll2_client.get_previous_launches(limit=limit)
        
        result = {
            "source": "Launch Library 2 (thespacedevs.com)",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "type": "upcoming" if upcoming else "previous",
            "spacex_only": spacex_only,
            "count": len(launches),
            "launches": [l.to_dict() for l in launches],
            "note": "Live data - updates every 15 minutes"
        }
        
        # Cache for 15 minutes (respect API rate limits)
        await cache.set(cache_key, result, ttl=900)
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "source": "Launch Library 2",
            "note": "API may be rate limited (15 req/hour free tier)"
        }


@router.get("/next")
async def get_next_launch(spacex_only: bool = Query(False)):
    """Get the next upcoming launch."""
    cache_key = f"ll2:next:{spacex_only}"
    
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    try:
        if spacex_only:
            launches = await ll2_client.get_spacex_launches(limit=1, upcoming=True)
        else:
            launches = await ll2_client.get_upcoming_launches(limit=1)
        
        if not launches:
            return {"error": "No upcoming launches found"}
        
        launch = launches[0]
        now = datetime.now(timezone.utc)
        time_until = launch.net - now
        
        result = {
            "source": "Launch Library 2",
            "launch": launch.to_dict(),
            "countdown": {
                "days": time_until.days,
                "hours": time_until.seconds // 3600,
                "minutes": (time_until.seconds % 3600) // 60,
                "total_seconds": int(time_until.total_seconds())
            },
            "is_spacex": "spacex" in launch.agency.lower()
        }
        
        await cache.set(cache_key, result, ttl=300)  # 5 min cache
        return result
        
    except Exception as e:
        return {"error": str(e)}


@router.get("/statistics")
async def get_launch_statistics():
    """Get launch statistics from recent and upcoming launches."""
    cache_key = "ll2:statistics"
    
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    try:
        # Get recent SpaceX launches
        recent_spacex = await ll2_client.get_spacex_launches(limit=30, upcoming=False)
        upcoming_spacex = await ll2_client.get_spacex_launches(limit=10, upcoming=True)
        
        # Get all recent launches for comparison
        recent_all = await ll2_client.get_previous_launches(limit=50)
        
        # Calculate SpaceX market share
        spacex_count = len([l for l in recent_all if "spacex" in l.agency.lower()])
        market_share = (spacex_count / len(recent_all) * 100) if recent_all else 0
        
        # Success rate (from status)
        success_statuses = ["Success", "Partial Failure"]
        spacex_successes = len([l for l in recent_spacex if l.status in success_statuses])
        spacex_success_rate = (spacex_successes / len(recent_spacex) * 100) if recent_spacex else 0
        
        # Mission type breakdown
        mission_types = {}
        for l in recent_spacex:
            mtype = l.mission_type or "Unknown"
            mission_types[mtype] = mission_types.get(mtype, 0) + 1
        
        result = {
            "source": "Launch Library 2",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "spacex": {
                "recent_launches": len(recent_spacex),
                "upcoming_launches": len(upcoming_spacex),
                "success_rate": round(spacex_success_rate, 1),
                "market_share_pct": round(market_share, 1),
                "mission_types": mission_types
            },
            "global": {
                "recent_launches": len(recent_all),
                "agencies": len(set(l.agency for l in recent_all))
            },
            "next_spacex": upcoming_spacex[0].to_dict() if upcoming_spacex else None
        }
        
        await cache.set(cache_key, result, ttl=1800)  # 30 min cache
        return result
        
    except Exception as e:
        return {"error": str(e)}


@router.get("/compare")
async def compare_data_sources():
    """Compare data freshness between sources."""
    from app.services.spacex_api import spacex_client
    
    # Get latest from both sources
    spacex_api_launches = await spacex_client.get_launches(limit=1, upcoming=False)
    ll2_launches = await ll2_client.get_previous_launches(limit=1, agency="SpaceX")
    
    spacex_latest = spacex_api_launches[0].date_utc if spacex_api_launches else None
    ll2_latest = ll2_launches[0].net if ll2_launches else None
    
    return {
        "spacex_api": {
            "latest_launch": spacex_latest.isoformat() if spacex_latest else None,
            "status": "DEPRECATED - No updates since late 2022",
            "note": "SpaceX discontinued their public API"
        },
        "launch_library_2": {
            "latest_launch": ll2_latest.isoformat() if ll2_latest else None,
            "status": "ACTIVE - Updated regularly",
            "note": "Community-maintained, comprehensive space launch database"
        },
        "recommendation": "Use /launches-live for current data, /launches for historical analysis",
        "data_gap_days": (ll2_latest - spacex_latest).days if (spacex_latest and ll2_latest) else None
    }
