"""TLE data fetching and management service."""
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import structlog

from app.core.config import get_settings
from app.services.orbital_engine import orbital_engine

logger = structlog.get_logger()


class TLEService:
    """Service for fetching and managing TLE data from Space-Track.org."""
    
    SPACETRACK_LOGIN = "https://www.space-track.org/ajaxauth/login"
    SPACETRACK_BASE = "https://www.space-track.org/basicspacedata/query"
    
    def __init__(self):
        self.settings = get_settings()
        self._last_update: Optional[datetime] = None
        self._tle_cache: dict[str, tuple[str, str, str]] = {}  # norad_id -> (name, line1, line2)
        self._update_lock = asyncio.Lock()
        self._session_cookie = None
    
    async def _authenticate(self, client: httpx.AsyncClient) -> bool:
        """Authenticate with Space-Track.org."""
        if not self.settings.spacetrack_username or not self.settings.spacetrack_password:
            logger.error("Space-Track credentials not configured")
            return False
        
        response = await client.post(
            self.SPACETRACK_LOGIN,
            data={
                "identity": self.settings.spacetrack_username,
                "password": self.settings.spacetrack_password,
            }
        )
        
        if response.status_code == 200 and "error" not in response.text.lower():
            logger.info("Space-Track authentication successful")
            return True
        
        logger.error("Space-Track authentication failed", response=response.text[:200])
        return False
    
    async def fetch_tle_data(self, source: str = "starlink") -> dict[str, tuple[str, str, str]]:
        """Fetch TLE data from Space-Track.org."""
        
        # Build query based on source
        if source == "starlink":
            query = f"{self.SPACETRACK_BASE}/class/gp/OBJECT_NAME/~~STARLINK/orderby/NORAD_CAT_ID/format/tle"
        elif source == "stations":
            query = f"{self.SPACETRACK_BASE}/class/gp/OBJECT_TYPE/PAYLOAD/PERIOD/90--95/ECCENTRICITY/<0.01/orderby/NORAD_CAT_ID/limit/100/format/tle"
        else:
            query = f"{self.SPACETRACK_BASE}/class/gp/OBJECT_TYPE/PAYLOAD/DECAY/null-val/orderby/NORAD_CAT_ID/limit/1000/format/tle"
        
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            # Authenticate first
            if not await self._authenticate(client):
                raise Exception("Failed to authenticate with Space-Track")
            
            # Fetch TLE data
            logger.info("Fetching TLE data from Space-Track", source=source)
            response = await client.get(query)
            response.raise_for_status()
            
            tle_text = response.text
            return self._parse_tle(tle_text)
    
    def _parse_tle(self, tle_text: str) -> dict[str, tuple[str, str, str]]:
        """Parse TLE format text into structured data."""
        lines = [l.strip() for l in tle_text.strip().split('\n') if l.strip()]
        result = {}
        
        i = 0
        while i < len(lines) - 2:
            # TLE format: Name, Line 1, Line 2
            name = lines[i]
            line1 = lines[i + 1]
            line2 = lines[i + 2]
            
            # Validate TLE lines
            if line1.startswith('1 ') and line2.startswith('2 '):
                # Extract NORAD catalog ID from line 1
                try:
                    norad_id = line1[2:7].strip()
                    result[norad_id] = (name, line1, line2)
                except:
                    pass
                i += 3
            else:
                i += 1
        
        return result
    
    async def update_orbital_engine(self, source: str = "starlink") -> int:
        """Update the orbital engine with fresh TLE data."""
        async with self._update_lock:
            logger.info("Fetching TLE data", source=source)
            
            try:
                tle_data = await self.fetch_tle_data(source)
                
                loaded = 0
                for norad_id, (name, line1, line2) in tle_data.items():
                    # Use NORAD ID as satellite ID
                    if orbital_engine.load_tle(norad_id, line1, line2):
                        self._tle_cache[norad_id] = (name, line1, line2)
                        loaded += 1
                
                self._last_update = datetime.utcnow()
                logger.info("TLE update complete", loaded=loaded, total=len(tle_data))
                
                return loaded
                
            except Exception as e:
                logger.error("TLE update failed", error=str(e))
                raise
    
    async def ensure_data_loaded(self) -> bool:
        """Ensure TLE data is loaded, fetching if necessary."""
        if self._last_update is None:
            await self.update_orbital_engine()
            return True
        
        # Check if refresh needed
        age = datetime.utcnow() - self._last_update
        if age > timedelta(seconds=self.settings.tle_refresh_interval):
            await self.update_orbital_engine()
            return True
        
        return False
    
    def get_satellite_name(self, norad_id: str) -> Optional[str]:
        """Get satellite name from cache."""
        if norad_id in self._tle_cache:
            return self._tle_cache[norad_id][0]
        return None
    
    def get_tle(self, norad_id: str) -> Optional[tuple[str, str]]:
        """Get TLE lines for a satellite."""
        if norad_id in self._tle_cache:
            _, line1, line2 = self._tle_cache[norad_id]
            return (line1, line2)
        return None
    
    @property
    def satellite_count(self) -> int:
        """Number of satellites with TLE data."""
        return len(self._tle_cache)
    
    @property
    def last_update(self) -> Optional[datetime]:
        """Time of last TLE update."""
        return self._last_update
    
    def get_status(self) -> dict:
        """Get TLE service status."""
        return {
            "satellite_count": self.satellite_count,
            "last_update": self._last_update.isoformat() if self._last_update else None,
            "orbital_engine_loaded": orbital_engine.satellite_count
        }


# Global service instance
tle_service = TLEService()
