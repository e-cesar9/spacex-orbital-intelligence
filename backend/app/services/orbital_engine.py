"""Orbital mechanics engine using SGP4."""
import math
from datetime import datetime, timedelta
from typing import Optional
import numpy as np
from sgp4.api import Satrec, jday
from sgp4.api import WGS84
from dataclasses import dataclass


@dataclass
class SatellitePosition:
    """Satellite position in various coordinate systems."""
    satellite_id: str
    timestamp: datetime
    # ECI coordinates (km)
    x: float
    y: float
    z: float
    # Velocity (km/s)
    vx: float
    vy: float
    vz: float
    # Geographic coordinates
    latitude: float
    longitude: float
    altitude: float  # km
    # Orbital elements
    velocity: float  # km/s
    
    def to_dict(self) -> dict:
        return {
            "satellite_id": self.satellite_id,
            "timestamp": self.timestamp.isoformat(),
            "position": {"x": self.x, "y": self.y, "z": self.z},
            "velocity": {"vx": self.vx, "vy": self.vy, "vz": self.vz},
            "geographic": {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "altitude": self.altitude
            },
            "speed": self.velocity
        }


@dataclass
class CollisionRisk:
    """Collision risk assessment."""
    satellite_id_1: str
    satellite_id_2: str
    min_distance: float  # km
    time_of_closest_approach: datetime
    risk_score: float  # 0-1
    
    def to_dict(self) -> dict:
        return {
            "satellite_1": self.satellite_id_1,
            "satellite_2": self.satellite_id_2,
            "min_distance_km": self.min_distance,
            "tca": self.time_of_closest_approach.isoformat(),
            "risk_score": self.risk_score
        }


class OrbitalEngine:
    """SGP4-based orbital propagation engine."""
    
    # Earth radius in km
    EARTH_RADIUS = 6371.0
    
    # Risk thresholds (km)
    COLLISION_THRESHOLD = 10.0  # High risk
    WARNING_THRESHOLD = 50.0    # Medium risk
    MONITOR_THRESHOLD = 100.0   # Low risk
    
    def __init__(self):
        self._satellites: dict[str, Satrec] = {}
        self._tle_data: dict[str, tuple[str, str]] = {}
    
    def load_tle(self, satellite_id: str, tle_line1: str, tle_line2: str) -> bool:
        """Load TLE data for a satellite."""
        try:
            satellite = Satrec.twoline2rv(tle_line1, tle_line2)
            self._satellites[satellite_id] = satellite
            self._tle_data[satellite_id] = (tle_line1, tle_line2)
            return True
        except Exception as e:
            print(f"Error loading TLE for {satellite_id}: {e}")
            return False
    
    def propagate(
        self, 
        satellite_id: str, 
        dt: Optional[datetime] = None
    ) -> Optional[SatellitePosition]:
        """Propagate satellite position to given time."""
        if satellite_id not in self._satellites:
            return None
        
        satellite = self._satellites[satellite_id]
        
        if dt is None:
            dt = datetime.utcnow()
        
        # Convert to Julian date
        jd, fr = jday(dt.year, dt.month, dt.day, 
                      dt.hour, dt.minute, dt.second + dt.microsecond / 1e6)
        
        # Propagate
        error, position, velocity = satellite.sgp4(jd, fr)
        
        if error != 0:
            return None
        
        x, y, z = position
        vx, vy, vz = velocity
        
        # Calculate geographic coordinates
        lat, lon, alt = self._eci_to_geodetic(x, y, z, dt)
        
        # Calculate velocity magnitude
        vel_mag = math.sqrt(vx**2 + vy**2 + vz**2)
        
        return SatellitePosition(
            satellite_id=satellite_id,
            timestamp=dt,
            x=x, y=y, z=z,
            vx=vx, vy=vy, vz=vz,
            latitude=lat,
            longitude=lon,
            altitude=alt,
            velocity=vel_mag
        )
    
    def propagate_at_time(
        self,
        satellite_id: str,
        seconds_offset: int
    ) -> Optional[SatellitePosition]:
        """Propagate satellite position to a time offset from now."""
        dt = datetime.utcnow() + timedelta(seconds=seconds_offset)
        return self.propagate(satellite_id, dt)
    
    def propagate_orbit(
        self,
        satellite_id: str,
        hours: int = 24,
        step_minutes: int = 5
    ) -> list[SatellitePosition]:
        """Generate orbital path for visualization."""
        positions = []
        now = datetime.utcnow()
        
        steps = (hours * 60) // step_minutes
        
        for i in range(steps):
            dt = now + timedelta(minutes=i * step_minutes)
            pos = self.propagate(satellite_id, dt)
            if pos:
                positions.append(pos)
        
        return positions
    
    def calculate_risk_score(
        self,
        sat_id_1: str,
        sat_id_2: str,
        hours_ahead: int = 24
    ) -> Optional[CollisionRisk]:
        """Calculate collision risk between two satellites."""
        if sat_id_1 not in self._satellites or sat_id_2 not in self._satellites:
            return None
        
        min_distance = float('inf')
        tca = datetime.utcnow()
        now = datetime.utcnow()
        
        # Check positions at 1-minute intervals
        for minutes in range(hours_ahead * 60):
            dt = now + timedelta(minutes=minutes)
            
            pos1 = self.propagate(sat_id_1, dt)
            pos2 = self.propagate(sat_id_2, dt)
            
            if not pos1 or not pos2:
                continue
            
            distance = math.sqrt(
                (pos1.x - pos2.x)**2 + 
                (pos1.y - pos2.y)**2 + 
                (pos1.z - pos2.z)**2
            )
            
            if distance < min_distance:
                min_distance = distance
                tca = dt
        
        # Calculate risk score (0-1)
        if min_distance <= self.COLLISION_THRESHOLD:
            risk_score = 1.0
        elif min_distance <= self.WARNING_THRESHOLD:
            risk_score = 0.7 + 0.3 * (1 - (min_distance - self.COLLISION_THRESHOLD) / 
                                       (self.WARNING_THRESHOLD - self.COLLISION_THRESHOLD))
        elif min_distance <= self.MONITOR_THRESHOLD:
            risk_score = 0.3 + 0.4 * (1 - (min_distance - self.WARNING_THRESHOLD) / 
                                       (self.MONITOR_THRESHOLD - self.WARNING_THRESHOLD))
        else:
            risk_score = max(0, 0.3 * (1 - (min_distance - self.MONITOR_THRESHOLD) / 500))
        
        return CollisionRisk(
            satellite_id_1=sat_id_1,
            satellite_id_2=sat_id_2,
            min_distance=min_distance,
            time_of_closest_approach=tca,
            risk_score=risk_score
        )
    
    def analyze_density(
        self,
        altitude_km: float,
        tolerance_km: float = 50
    ) -> dict:
        """Analyze satellite density at a given altitude."""
        now = datetime.utcnow()
        satellites_at_altitude = []
        
        for sat_id in self._satellites:
            pos = self.propagate(sat_id, now)
            if pos and abs(pos.altitude - altitude_km) <= tolerance_km:
                satellites_at_altitude.append({
                    "id": sat_id,
                    "altitude": pos.altitude,
                    "latitude": pos.latitude,
                    "longitude": pos.longitude
                })
        
        return {
            "target_altitude": altitude_km,
            "tolerance": tolerance_km,
            "count": len(satellites_at_altitude),
            "density_per_1000km": len(satellites_at_altitude) / (4 * math.pi * (self.EARTH_RADIUS + altitude_km)**2 / 1e6),
            "satellites": satellites_at_altitude[:100]  # Limit response
        }
    
    def _eci_to_geodetic(
        self,
        x: float,
        y: float,
        z: float,
        dt: datetime
    ) -> tuple[float, float, float]:
        """Convert ECI coordinates to geodetic (lat, lon, alt)."""
        # Calculate GMST for ECI to ECEF conversion
        jd, fr = jday(dt.year, dt.month, dt.day,
                      dt.hour, dt.minute, dt.second + dt.microsecond / 1e6)
        
        # Simplified GMST calculation
        d = jd - 2451545.0 + fr
        gmst = 280.46061837 + 360.98564736629 * d
        gmst = gmst % 360
        gmst_rad = math.radians(gmst)
        
        # Rotate to ECEF
        x_ecef = x * math.cos(gmst_rad) + y * math.sin(gmst_rad)
        y_ecef = -x * math.sin(gmst_rad) + y * math.cos(gmst_rad)
        z_ecef = z
        
        # Calculate geodetic coordinates
        r = math.sqrt(x_ecef**2 + y_ecef**2 + z_ecef**2)
        lon = math.degrees(math.atan2(y_ecef, x_ecef))
        lat = math.degrees(math.asin(z_ecef / r))
        alt = r - self.EARTH_RADIUS
        
        return lat, lon, alt
    
    def get_all_positions(self) -> list[SatellitePosition]:
        """Get current positions of all loaded satellites."""
        now = datetime.utcnow()
        positions = []
        
        for sat_id in self._satellites:
            pos = self.propagate(sat_id, now)
            if pos:
                positions.append(pos)
        
        return positions
    
    @property
    def satellite_count(self) -> int:
        """Number of loaded satellites."""
        return len(self._satellites)
    
    @property
    def satellite_ids(self) -> list[str]:
        """List of loaded satellite IDs."""
        return list(self._satellites.keys())


# Global engine instance
orbital_engine = OrbitalEngine()
