"""
Monitoring API endpoints.

Provides endpoints for collision monitoring status and control.
Protected endpoints require X-API-Key header.
"""
from fastapi import APIRouter, Query, Depends
from datetime import datetime, timezone

from app.services.monitoring import collision_monitor
from app.core.security import verify_api_key, limiter

router = APIRouter(prefix="/monitoring", tags=["Collision Monitoring"])


@router.get("/status")
async def get_monitoring_status():
    """Get current monitoring service status."""
    return await collision_monitor.get_monitoring_status()


@router.post("/check")
async def trigger_manual_check(
    probability_threshold: float = Query(1e-5, description="Minimum probability to report"),
    hours_ahead: int = Query(72, ge=1, le=168)
):
    """
    Trigger a manual check for CDM alerts.
    
    This can be called by a cron job for scheduled monitoring.
    """
    return await collision_monitor.check_for_alerts(
        probability_threshold=probability_threshold,
        hours_ahead=hours_ahead
    )


@router.post("/start")
async def start_background_monitoring(
    interval_minutes: int = Query(15, ge=5, le=60),
    probability_threshold: float = Query(1e-5),
    _auth: bool = Depends(verify_api_key)
):
    """
    Start continuous background monitoring.
    
    Requires X-API-Key header.
    Checks for CDM alerts at the specified interval and logs critical events.
    """
    return await collision_monitor.start_background_monitoring(
        interval_minutes=interval_minutes,
        probability_threshold=probability_threshold
    )


@router.post("/stop")
async def stop_background_monitoring(_auth: bool = Depends(verify_api_key)):
    """Stop background monitoring. Requires X-API-Key header."""
    return collision_monitor.stop_background_monitoring()


@router.get("/alerts/critical")
async def get_critical_alerts():
    """
    Get current critical alerts that require attention.
    
    Critical = Emergency level (Pc > 1e-4 or miss < 1km)
    """
    from app.services.spacetrack import spacetrack_client
    
    if not spacetrack_client.is_configured:
        return {"error": "Space-Track not configured"}
    
    try:
        alerts = await spacetrack_client.get_cdm_enriched(
            hours_ahead=168,
            limit=100
        )
        
        critical = [a for a in alerts if a.emergency]
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "critical_count": len(critical),
            "action_required": len(critical) > 0,
            "alerts": [a.to_dict() for a in critical]
        }
        
    except Exception as e:
        return {"error": str(e)}


@router.get("/summary")
async def get_monitoring_summary():
    """
    Get a summary suitable for dashboards and status pages.
    """
    from app.services.spacetrack import spacetrack_client
    
    status = await collision_monitor.get_monitoring_status()
    
    if not spacetrack_client.is_configured:
        return {
            "status": "UNCONFIGURED",
            "message": "Space-Track credentials not set",
            "monitoring": status
        }
    
    try:
        # Quick check
        result = await collision_monitor.check_for_alerts(hours_ahead=72)
        
        # Determine overall status
        if result.get("new_critical", 0) > 0:
            overall_status = "CRITICAL"
        elif result.get("new_high", 0) > 0:
            overall_status = "WARNING"
        elif result.get("status") == "OK":
            overall_status = "NOMINAL"
        else:
            overall_status = "ERROR"
        
        return {
            "status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_conjunctions": result.get("total_alerts", 0),
            "critical_events": result.get("new_critical", 0),
            "high_risk_events": result.get("new_high", 0),
            "monitoring": status,
            "action_required": overall_status in ["CRITICAL", "WARNING"]
        }
        
    except Exception as e:
        return {
            "status": "ERROR",
            "error": str(e),
            "monitoring": status
        }
