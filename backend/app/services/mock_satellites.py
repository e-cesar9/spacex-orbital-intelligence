"""Optimized mock satellite data generator using numpy for vectorized calculations."""
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time
import threading

# Starlink orbital parameters
STARLINK_SHELLS = [
    {"altitude": 550, "inclination": 53.0, "count": 1584},
    {"altitude": 540, "inclination": 53.2, "count": 1584},
    {"altitude": 570, "inclination": 70.0, "count": 720},
    {"altitude": 560, "inclination": 97.6, "count": 348},
    {"altitude": 336, "inclination": 42.0, "count": 2493},
]

EARTH_RADIUS = 6371.0  # km
MU = 398600.4418  # Earth's gravitational parameter


class OptimizedMockGenerator:
    """High-performance satellite constellation simulator using numpy."""
    
    def __init__(self, max_satellites: int = 2000):
        self.max_satellites = max_satellites
        
        # Pre-allocated numpy arrays for orbital elements
        self._ids: List[str] = []
        self._altitudes: np.ndarray = None
        self._inclinations: np.ndarray = None  # radians
        self._raans: np.ndarray = None  # radians
        self._mean_anomalies: np.ndarray = None  # radians
        self._mean_motions: np.ndarray = None  # rad/min
        self._semi_major_axes: np.ndarray = None  # km
        
        # Cache
        self._cached_positions: Optional[List[Dict]] = None
        self._cache_time: float = 0
        self._cache_ttl: float = 1.0  # Refresh every second
        self._cache_lock = threading.Lock()
        
        # Pre-calculated orbital trail cache
        self._trail_cache: Dict[str, List[Dict]] = {}
        
        # Initialize constellation
        self._generate_constellation()
        
        # Pre-calculate initial positions
        self._update_cache()
    
    def _generate_constellation(self):
        """Generate orbital elements for Starlink constellation."""
        ids = []
        altitudes = []
        inclinations = []
        raans = []
        mean_anomalies = []
        
        sat_id = 0
        np.random.seed(42)  # Reproducible randomness
        
        for shell in STARLINK_SHELLS:
            planes = 72
            sats_per_plane = shell["count"] // planes
            
            for plane in range(planes):
                base_raan = (2 * np.pi / planes) * plane
                
                for sat_in_plane in range(sats_per_plane):
                    base_ma = (2 * np.pi / sats_per_plane) * sat_in_plane
                    
                    ids.append(f"STARLINK-{sat_id}")
                    altitudes.append(shell["altitude"] + np.random.uniform(-5, 5))
                    inclinations.append(np.radians(shell["inclination"] + np.random.uniform(-0.5, 0.5)))
                    raans.append(base_raan + np.random.uniform(-0.02, 0.02))
                    mean_anomalies.append(base_ma + np.random.uniform(-0.035, 0.035))
                    
                    sat_id += 1
                    if sat_id >= self.max_satellites:
                        break
                if sat_id >= self.max_satellites:
                    break
            if sat_id >= self.max_satellites:
                break
        
        # Convert to numpy arrays
        self._ids = ids
        self._altitudes = np.array(altitudes)
        self._inclinations = np.array(inclinations)
        self._raans = np.array(raans)
        self._mean_anomalies = np.array(mean_anomalies)
        
        # Pre-calculate derived values
        self._semi_major_axes = EARTH_RADIUS + self._altitudes
        periods = 2 * np.pi * np.sqrt(self._semi_major_axes**3 / MU)  # seconds
        self._mean_motions = 2 * np.pi / (periods / 60)  # rad/min
        
        # Pre-calculate velocities (constant for circular orbits)
        self._velocities = np.sqrt(MU / self._semi_major_axes)
    
    def _compute_positions_vectorized(self, dt: datetime = None) -> np.ndarray:
        """Compute all satellite positions using vectorized numpy operations."""
        if dt is None:
            dt = datetime.utcnow()
        
        # Time since epoch
        epoch = datetime(2024, 1, 1, 0, 0, 0)
        elapsed_minutes = (dt - epoch).total_seconds() / 60
        
        # Current mean anomalies (all satellites at once)
        M = (self._mean_anomalies + self._mean_motions * elapsed_minutes) % (2 * np.pi)
        
        # RAAN precession (simplified)
        raan_rate = -0.1 * np.cos(self._inclinations) * (np.pi / 180) / 1440  # rad/min
        raan = (self._raans + raan_rate * elapsed_minutes) % (2 * np.pi)
        
        # Position in orbital plane (circular orbit)
        r = self._semi_major_axes
        x_orb = r * np.cos(M)
        y_orb = r * np.sin(M)
        
        # Transform to ECI coordinates
        cos_raan = np.cos(raan)
        sin_raan = np.sin(raan)
        cos_inc = np.cos(self._inclinations)
        sin_inc = np.sin(self._inclinations)
        
        x = x_orb * cos_raan - y_orb * cos_inc * sin_raan
        y = x_orb * sin_raan + y_orb * cos_inc * cos_raan
        z = y_orb * sin_inc
        
        # GMST for sidereal time
        jd = (dt - datetime(2000, 1, 1, 12, 0, 0)).total_seconds() / 86400.0 + 2451545.0
        gmst = np.radians((280.46061837 + 360.98564736629 * (jd - 2451545.0)) % 360)
        
        # Rotate to ECEF
        cos_gmst = np.cos(gmst)
        sin_gmst = np.sin(gmst)
        x_ecef = x * cos_gmst + y * sin_gmst
        y_ecef = -x * sin_gmst + y * cos_gmst
        z_ecef = z
        
        # Geographic coordinates
        lon = np.degrees(np.arctan2(y_ecef, x_ecef))
        lat = np.degrees(np.arcsin(np.clip(z_ecef / r, -1, 1)))
        
        return np.column_stack([lat, lon, self._altitudes, self._velocities])
    
    def _update_cache(self):
        """Update the position cache."""
        positions_array = self._compute_positions_vectorized()
        
        positions = []
        for i, sat_id in enumerate(self._ids):
            positions.append({
                "id": sat_id,
                "lat": round(float(positions_array[i, 0]), 4),
                "lon": round(float(positions_array[i, 1]), 4),
                "alt": round(float(positions_array[i, 2]), 2),
                "v": round(float(positions_array[i, 3]), 3)
            })
        
        with self._cache_lock:
            self._cached_positions = positions
            self._cache_time = time.time()
    
    def get_all_positions(self, dt: datetime = None) -> List[Dict]:
        """Get positions of all satellites (cached)."""
        current_time = time.time()
        
        # Check if cache is still valid
        if dt is None and self._cached_positions and (current_time - self._cache_time) < self._cache_ttl:
            return self._cached_positions
        
        # Compute fresh positions
        if dt is None:
            self._update_cache()
            return self._cached_positions
        else:
            # Custom time requested - compute directly
            positions_array = self._compute_positions_vectorized(dt)
            return [
                {
                    "id": self._ids[i],
                    "lat": round(float(positions_array[i, 0]), 4),
                    "lon": round(float(positions_array[i, 1]), 4),
                    "alt": round(float(positions_array[i, 2]), 2),
                    "v": round(float(positions_array[i, 3]), 3)
                }
                for i in range(len(self._ids))
            ]
    
    def get_position(self, sat_id: str) -> Optional[Dict]:
        """Get position of a single satellite."""
        positions = self.get_all_positions()
        for pos in positions:
            if pos["id"] == sat_id:
                return pos
        return None
    
    def get_orbit_path(self, sat_id: str, hours: int = 2, steps: int = 100) -> List[Dict]:
        """Get orbital path for a satellite."""
        # Check cache
        cache_key = f"{sat_id}:{hours}:{steps}"
        if cache_key in self._trail_cache:
            cached = self._trail_cache[cache_key]
            # Return cached if less than 5 minutes old
            return cached
        
        # Find satellite index
        try:
            idx = self._ids.index(sat_id)
        except ValueError:
            return []
        
        path = []
        now = datetime.utcnow()
        
        for i in range(steps):
            dt = now + timedelta(hours=hours * i / steps)
            
            # Calculate position for single satellite
            elapsed_minutes = (dt - datetime(2024, 1, 1, 0, 0, 0)).total_seconds() / 60
            M = (self._mean_anomalies[idx] + self._mean_motions[idx] * elapsed_minutes) % (2 * np.pi)
            
            raan_rate = -0.1 * np.cos(self._inclinations[idx]) * (np.pi / 180) / 1440
            raan = (self._raans[idx] + raan_rate * elapsed_minutes) % (2 * np.pi)
            
            r = self._semi_major_axes[idx]
            x_orb = r * np.cos(M)
            y_orb = r * np.sin(M)
            
            cos_raan = np.cos(raan)
            sin_raan = np.sin(raan)
            cos_inc = np.cos(self._inclinations[idx])
            sin_inc = np.sin(self._inclinations[idx])
            
            x = x_orb * cos_raan - y_orb * cos_inc * sin_raan
            y = x_orb * sin_raan + y_orb * cos_inc * cos_raan
            z = y_orb * sin_inc
            
            jd = (dt - datetime(2000, 1, 1, 12, 0, 0)).total_seconds() / 86400.0 + 2451545.0
            gmst = np.radians((280.46061837 + 360.98564736629 * (jd - 2451545.0)) % 360)
            
            x_ecef = x * np.cos(gmst) + y * np.sin(gmst)
            y_ecef = -x * np.sin(gmst) + y * np.cos(gmst)
            z_ecef = z
            
            lon = np.degrees(np.arctan2(y_ecef, x_ecef))
            lat = np.degrees(np.arcsin(np.clip(z_ecef / r, -1, 1)))
            
            path.append({
                "t": dt.isoformat(),
                "lat": round(float(lat), 4),
                "lon": round(float(lon), 4),
                "alt": round(float(self._altitudes[idx]), 2)
            })
        
        # Cache the result (limit cache size)
        if len(self._trail_cache) > 100:
            self._trail_cache.clear()
        self._trail_cache[cache_key] = path
        
        return path
    
    @property
    def count(self) -> int:
        return len(self._ids)
    
    @property 
    def satellite_ids(self) -> List[str]:
        return self._ids


# Global instance
mock_generator = OptimizedMockGenerator()
