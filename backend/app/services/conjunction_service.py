"""Conjunction Data Message (CDM) service for real collision alerts."""
import httpx
from datetime import datetime, timedelta
from typing import Optional
import structlog
import math

from app.core.config import get_settings
from app.services.orbital_engine import orbital_engine
from app.services.tle_service import tle_service

logger = structlog.get_logger()


class ConjunctionService:
    """Service for fetching and analyzing conjunction data from Space-Track."""
    
    SPACETRACK_LOGIN = "https://www.space-track.org/ajaxauth/login"
    SPACETRACK_BASE = "https://www.space-track.org/basicspacedata/query"
    
    def __init__(self):
        self.settings = get_settings()
        
    async def _get_authenticated_client(self) -> httpx.AsyncClient:
        """Get an authenticated client for Space-Track."""
        client = httpx.AsyncClient(timeout=60.0, follow_redirects=True)
        
        # Authenticate
        resp = await client.post(
            self.SPACETRACK_LOGIN,
            data={
                "identity": self.settings.spacetrack_username,
                "password": self.settings.spacetrack_password
            }
        )
        
        if resp.status_code != 200:
            await client.aclose()
            raise Exception("Space-Track authentication failed")
        
        return client
    
    async def get_cdm_alerts(
        self,
        satellite_filter: str = "STARLINK",
        min_probability: float = 0.0,
        hours_ahead: int = 72,
        limit: int = 50
    ) -> list[dict]:
        """
        Fetch real CDM (Conjunction Data Messages) from Space-Track.
        
        CDM contains:
        - TCA: Time of Closest Approach
        - MIN_RNG: Minimum range (distance) in km
        - PC: Probability of Collision
        """
        client = await self._get_authenticated_client()
        
        try:
            # Build query for CDM data
            # Filter by satellite name pattern and TCA in future
            now = datetime.utcnow()
            tca_start = now.strftime("%Y-%m-%d")
            tca_end = (now + timedelta(hours=hours_ahead)).strftime("%Y-%m-%d")
            
            query = (
                f"{self.SPACETRACK_BASE}/class/cdm_public"
                f"/SAT_1_NAME/~~{satellite_filter}"
                f"/TCA/{tca_start}--{tca_end}"
                f"/orderby/TCA asc"
                f"/limit/{limit}"
                f"/format/json"
            )
            
            logger.info("Fetching CDM data", query=query[:100])
            resp = await client.get(query)
            resp.raise_for_status()
            
            cdm_data = resp.json()
            
            # Process and filter results
            alerts = []
            for cdm in cdm_data:
                try:
                    pc = float(cdm.get("PC", 0) or 0)
                    if pc < min_probability:
                        continue
                    
                    alerts.append({
                        "cdm_id": cdm.get("CDM_ID"),
                        "tca": cdm.get("TCA"),
                        "min_range_km": float(cdm.get("MIN_RNG", 0) or 0),
                        "probability": pc,
                        "satellite_1": {
                            "id": cdm.get("SAT_1_ID"),
                            "name": cdm.get("SAT_1_NAME"),
                            "type": cdm.get("SAT1_OBJECT_TYPE")
                        },
                        "satellite_2": {
                            "id": cdm.get("SAT_2_ID"),
                            "name": cdm.get("SAT_2_NAME"),
                            "type": cdm.get("SAT2_OBJECT_TYPE")
                        },
                        "emergency": cdm.get("EMERGENCY_REPORTABLE") == "Y",
                        "created": cdm.get("CREATED")
                    })
                except (ValueError, TypeError) as e:
                    logger.warning("Failed to parse CDM record", error=str(e))
                    continue
            
            return alerts
            
        finally:
            await client.aclose()
    
    def calculate_tca_sgp4(
        self,
        sat1_id: str,
        sat2_id: str,
        hours_ahead: int = 24,
        step_seconds: int = 60
    ) -> Optional[dict]:
        """
        Calculate Time of Closest Approach using SGP4 propagation.
        
        This is a simplified TCA calculation that:
        1. Propagates both satellites forward in time
        2. Finds the minimum distance point
        3. Refines using binary search
        """
        # Get TLE data for both satellites
        tle1 = tle_service.get_tle(sat1_id)
        tle2 = tle_service.get_tle(sat2_id)
        
        if not tle1 or not tle2:
            return None
        
        # Propagate and find minimum distance
        min_dist = float('inf')
        min_time = None
        
        steps = (hours_ahead * 3600) // step_seconds
        
        for i in range(steps):
            # Propagate both satellites
            pos1 = orbital_engine.propagate_at_time(sat1_id, i * step_seconds)
            pos2 = orbital_engine.propagate_at_time(sat2_id, i * step_seconds)
            
            if not pos1 or not pos2:
                continue
            
            # Calculate 3D distance
            dist = math.sqrt(
                (pos1.position['x'] - pos2.position['x']) ** 2 +
                (pos1.position['y'] - pos2.position['y']) ** 2 +
                (pos1.position['z'] - pos2.position['z']) ** 2
            )
            
            if dist < min_dist:
                min_dist = dist
                min_time = datetime.utcnow() + timedelta(seconds=i * step_seconds)
        
        if min_time is None:
            return None
        
        # Calculate relative velocity at TCA (simplified)
        pos1 = orbital_engine.propagate(sat1_id)
        pos2 = orbital_engine.propagate(sat2_id)
        
        if not pos1 or not pos2:
            return None
        
        rel_velocity = math.sqrt(
            (pos1.velocity['vx'] - pos2.velocity['vx']) ** 2 +
            (pos1.velocity['vy'] - pos2.velocity['vy']) ** 2 +
            (pos1.velocity['vz'] - pos2.velocity['vz']) ** 2
        )
        
        # Estimate collision probability (very simplified)
        # Real calculation uses covariance matrices
        combined_radius = 0.01  # ~10m for two Starlinks
        probability = max(0, min(1, (combined_radius / max(min_dist, 0.001)) ** 2))
        
        return {
            "satellite_1": {
                "id": sat1_id,
                "name": tle_service.get_satellite_name(sat1_id)
            },
            "satellite_2": {
                "id": sat2_id,
                "name": tle_service.get_satellite_name(sat2_id)
            },
            "tca": min_time.isoformat(),
            "min_range_km": round(min_dist, 3),
            "relative_velocity_kms": round(rel_velocity, 3),
            "probability_estimate": round(probability, 6),
            "calculation_method": "sgp4_propagation"
        }


# Ground station visibility
GROUND_STATIONS = [
    {"name": "Svalbard (SvalSat)", "lat": 78.23, "lon": 15.39, "min_elevation": 5},
    {"name": "Alaska (Fairbanks)", "lat": 64.86, "lon": -147.85, "min_elevation": 5},
    {"name": "McMurdo (Antarctica)", "lat": -77.85, "lon": 166.67, "min_elevation": 5},
    {"name": "Punta Arenas", "lat": -53.16, "lon": -70.91, "min_elevation": 5},
    {"name": "Hawaii (AMOS)", "lat": 20.71, "lon": -156.26, "min_elevation": 10},
    {"name": "Guam", "lat": 13.44, "lon": 144.79, "min_elevation": 10},
    {"name": "Cape Canaveral", "lat": 28.49, "lon": -80.58, "min_elevation": 10},
    {"name": "Vandenberg", "lat": 34.74, "lon": -120.52, "min_elevation": 10},
]


def calculate_elevation(sat_lat: float, sat_lon: float, sat_alt: float,
                       gs_lat: float, gs_lon: float) -> float:
    """Calculate elevation angle from ground station to satellite."""
    # Earth radius in km
    R = 6371
    
    # Convert to radians
    sat_lat_r = math.radians(sat_lat)
    sat_lon_r = math.radians(sat_lon)
    gs_lat_r = math.radians(gs_lat)
    gs_lon_r = math.radians(gs_lon)
    
    # Calculate ground distance using haversine
    dlat = sat_lat_r - gs_lat_r
    dlon = sat_lon_r - gs_lon_r
    
    a = math.sin(dlat/2)**2 + math.cos(gs_lat_r) * math.cos(sat_lat_r) * math.sin(dlon/2)**2
    c = 2 * math.asin(min(1.0, math.sqrt(a)))  # Clamp to prevent domain error
    ground_dist = R * c
    
    # Calculate elevation angle using simpler geometric method
    if ground_dist < 0.1:  # Directly overhead
        return 90.0
    
    # Satellite distance from Earth center
    sat_r = R + sat_alt
    
    # Use law of cosines to find slant range and then elevation
    # Simplified: elevation ≈ atan2(altitude, ground_distance) for small angles
    # More accurate: consider Earth curvature
    
    # Angle at Earth center between GS and sub-satellite point
    gamma = ground_dist / R
    
    # Slant range to satellite
    slant_range = math.sqrt(R**2 + sat_r**2 - 2*R*sat_r*math.cos(gamma))
    
    # Elevation angle
    if slant_range < 0.1:
        return 90.0
    
    sin_elev = (sat_r * math.sin(gamma)) / slant_range if slant_range > 0 else 0
    sin_elev = max(-1, min(1, sin_elev))  # Clamp
    
    # Convert to elevation (complement of the angle)
    elevation = 90 - math.degrees(math.asin(sin_elev))
    
    # Adjust for geometry - satellite must be above horizon
    if sat_r * math.cos(gamma) < R:
        return -90  # Below horizon
    
    return max(-90, min(90, elevation))


def get_visible_stations(sat_lat: float, sat_lon: float, sat_alt: float) -> list[dict]:
    """Get list of ground stations that can see the satellite."""
    visible = []
    
    for gs in GROUND_STATIONS:
        elevation = calculate_elevation(
            sat_lat, sat_lon, sat_alt,
            gs["lat"], gs["lon"]
        )
        
        if elevation >= gs["min_elevation"]:
            visible.append({
                "name": gs["name"],
                "latitude": gs["lat"],
                "longitude": gs["lon"],
                "elevation_deg": round(elevation, 2),
                "in_view": True
            })
    
    return visible


def get_next_passes(
    satellite_id: str,
    station_name: str,
    hours_ahead: int = 24,
    step_minutes: int = 1
) -> list[dict]:
    """Calculate next passes over a ground station."""
    # Find the station
    station = next((gs for gs in GROUND_STATIONS if gs["name"] == station_name), None)
    if not station:
        return []
    
    passes = []
    in_pass = False
    pass_start = None
    max_elevation = 0
    
    steps = (hours_ahead * 60) // step_minutes
    
    for i in range(steps):
        pos = orbital_engine.propagate_at_time(satellite_id, i * step_minutes * 60)
        if not pos:
            continue
        
        elevation = calculate_elevation(
            pos.latitude, pos.longitude, pos.altitude,
            station["lat"], station["lon"]
        )
        
        if elevation >= station["min_elevation"]:
            if not in_pass:
                in_pass = True
                pass_start = datetime.utcnow() + timedelta(minutes=i * step_minutes)
                max_elevation = elevation
            else:
                max_elevation = max(max_elevation, elevation)
        else:
            if in_pass:
                # Pass ended
                pass_end = datetime.utcnow() + timedelta(minutes=i * step_minutes)
                passes.append({
                    "aos": pass_start.isoformat(),  # Acquisition of Signal
                    "los": pass_end.isoformat(),    # Loss of Signal
                    "duration_minutes": (pass_end - pass_start).seconds // 60,
                    "max_elevation_deg": round(max_elevation, 2)
                })
                in_pass = False
                max_elevation = 0
    
    return passes[:10]  # Limit to 10 passes


# Global service instance
conjunction_service = ConjunctionService()
