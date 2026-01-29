"""
CSV/JSON Export endpoints for all dashboard data.
"""
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone
import csv
import io
import json

from app.services.tle_service import tle_service
from app.services.spacetrack import spacetrack_client

router = APIRouter(prefix="/export", tags=["Data Export"])


@router.get("/satellites/csv")
async def export_satellites_csv():
    """Export all satellite positions as CSV."""
    
    positions = tle_service.get_all_positions()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "norad_id", "name", "latitude", "longitude", "altitude_km", 
        "velocity_km_s", "timestamp"
    ])
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    for pos in positions:
        writer.writerow([
            pos.get("norad_id", ""),
            pos.get("name", "Unknown"),
            round(pos.get("lat", 0), 6),
            round(pos.get("lon", 0), 6),
            round(pos.get("alt", 0), 2),
            round(pos.get("velocity", 0), 3),
            timestamp
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=satellites_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )


@router.get("/satellites/json")
async def export_satellites_json():
    """Export all satellite positions as JSON."""
    
    positions = tle_service.get_all_positions()
    
    data = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "count": len(positions),
        "satellites": positions
    }
    
    output = json.dumps(data, indent=2)
    
    return StreamingResponse(
        iter([output]),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=satellites_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        }
    )


@router.get("/cdm/csv")
async def export_cdm_csv(
    hours_ahead: int = Query(72, ge=1, le=168)
):
    """Export Conjunction Data Messages as CSV."""
    
    if not spacetrack_client.is_configured:
        return {"error": "Space-Track not configured"}
    
    try:
        alerts = await spacetrack_client.get_all_cdm(
            hours_ahead=hours_ahead,
            limit=200
        )
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "cdm_id", "tca", "miss_distance_km", "probability", "risk_level",
            "sat1_name", "sat1_norad", "sat1_type",
            "sat2_name", "sat2_norad", "sat2_type",
            "relative_speed_km_s", "emergency", "created"
        ])
        
        for alert in alerts:
            writer.writerow([
                alert.cdm_id,
                alert.tca.isoformat(),
                round(alert.miss_distance_km, 3),
                f"{alert.probability:.2e}",
                alert._calculate_risk_level(),
                alert.sat1_name,
                alert.sat1_norad,
                alert.sat1_type,
                alert.sat2_name,
                alert.sat2_norad,
                alert.sat2_type,
                round(alert.relative_speed_km_s, 3),
                alert.emergency,
                alert.created.isoformat()
            ])
        
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=cdm_alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )
        
    except Exception as e:
        return {"error": str(e)}


@router.get("/cdm/json")
async def export_cdm_json(
    hours_ahead: int = Query(72, ge=1, le=168)
):
    """Export Conjunction Data Messages as JSON."""
    
    if not spacetrack_client.is_configured:
        return {"error": "Space-Track not configured"}
    
    try:
        alerts = await spacetrack_client.get_all_cdm(
            hours_ahead=hours_ahead,
            limit=200
        )
        
        data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "source": "Space-Track.org (18th SDS)",
            "hours_ahead": hours_ahead,
            "count": len(alerts),
            "alerts": [a.to_dict() for a in alerts]
        }
        
        output = json.dumps(data, indent=2)
        
        return StreamingResponse(
            iter([output]),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=cdm_alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            }
        )
        
    except Exception as e:
        return {"error": str(e)}


@router.get("/analytics/csv")
async def export_analytics_csv():
    """Export analytics data as CSV."""
    from app.api.analytics import get_collision_trends, get_orbital_density_map
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Analytics summary
    writer.writerow(["SpaceX Orbital Analytics Export"])
    writer.writerow([f"Generated: {datetime.now(timezone.utc).isoformat()}"])
    writer.writerow([])
    
    # Satellite count
    positions = tle_service.get_all_positions()
    writer.writerow(["Total Satellites Tracked", len(positions)])
    
    if positions:
        avg_alt = sum(p.get("alt", 0) for p in positions) / len(positions)
        writer.writerow(["Average Altitude (km)", round(avg_alt, 2)])
    
    writer.writerow([])
    writer.writerow(["Altitude Distribution"])
    writer.writerow(["Range", "Count"])
    
    # Altitude buckets
    buckets = {
        "<400km": 0,
        "400-500km": 0,
        "500-600km": 0,
        ">600km": 0
    }
    
    for pos in positions:
        alt = pos.get("alt", 0)
        if alt < 400:
            buckets["<400km"] += 1
        elif alt < 500:
            buckets["400-500km"] += 1
        elif alt < 600:
            buckets["500-600km"] += 1
        else:
            buckets[">600km"] += 1
    
    for range_name, count in buckets.items():
        writer.writerow([range_name, count])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )
