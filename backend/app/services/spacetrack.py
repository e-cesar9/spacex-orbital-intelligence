"""
Space-Track.org API client for real conjunction data (CDM).

Space-Track is the authoritative source for:
- Conjunction Data Messages (CDM) from 18th Space Defense Squadron
- Official TLE data
- Satellite catalog
- Decay predictions

Register for free at: https://www.space-track.org/auth/createAccount
"""
import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional
from dataclasses import dataclass
import os

from app.core.config import get_settings

BASE_URL = "https://www.space-track.org"


@dataclass
class CDMAlert:
    """Conjunction Data Message from Space-Track."""
    cdm_id: str
    created: datetime
    tca: datetime  # Time of Closest Approach
    miss_distance_km: float
    probability: float
    
    sat1_name: str
    sat1_norad: str
    sat1_type: str  # PAYLOAD, DEBRIS, ROCKET BODY
    
    sat2_name: str
    sat2_norad: str
    sat2_type: str
    
    relative_speed_km_s: float
    
    # Risk classification
    emergency: bool  # Pc > 1e-4 or miss < 1km
    
    def to_dict(self) -> dict:
        return {
            "cdm_id": self.cdm_id,
            "created": self.created.isoformat(),
            "tca": self.tca.isoformat(),
            "miss_distance_km": self.miss_distance_km,
            "probability": self.probability,
            "satellite_1": {
                "name": self.sat1_name,
                "norad_id": self.sat1_norad,
                "type": self.sat1_type
            },
            "satellite_2": {
                "name": self.sat2_name,
                "norad_id": self.sat2_norad,
                "type": self.sat2_type
            },
            "relative_speed_km_s": self.relative_speed_km_s,
            "emergency": self.emergency,
            "risk_level": self._calculate_risk_level()
        }
    
    def _calculate_risk_level(self) -> str:
        if self.emergency or self.probability > 1e-3:
            return "CRITICAL"
        elif self.probability > 1e-4:
            return "HIGH"
        elif self.probability > 1e-5:
            return "MEDIUM"
        return "LOW"


class SpaceTrackClient:
    """
    Client for Space-Track.org API.
    
    Requires credentials set in environment:
    - SPACETRACK_USER
    - SPACETRACK_PASSWORD
    
    Rate limits: 30 requests per minute, 300 per hour
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[httpx.AsyncClient] = None
        self._authenticated = False
        self._cookies = None
        
        # Get credentials from environment or settings
        self.username = os.getenv("SPACETRACK_USER", "")
        self.password = os.getenv("SPACETRACK_PASSWORD", "")
    
    @property
    def is_configured(self) -> bool:
        """Check if credentials are configured."""
        return bool(self.username and self.password)
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=BASE_URL,
                timeout=30.0,
                follow_redirects=True
            )
        return self._client
    
    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
            self._authenticated = False
    
    async def _authenticate(self) -> bool:
        """Authenticate with Space-Track."""
        if not self.is_configured:
            return False
        
        if self._authenticated and self._cookies:
            return True
        
        client = await self._get_client()
        
        try:
            response = await client.post(
                "/ajaxauth/login",
                data={
                    "identity": self.username,
                    "password": self.password
                }
            )
            
            if response.status_code == 200:
                self._cookies = response.cookies
                self._authenticated = True
                return True
            else:
                print(f"Space-Track auth failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Space-Track auth error: {e}")
            return False
    
    async def get_cdm_for_starlink(
        self,
        hours_ahead: int = 72,
        min_probability: float = 1e-7
    ) -> list[CDMAlert]:
        """
        Get Conjunction Data Messages involving Starlink satellites.
        
        Args:
            hours_ahead: Look ahead window in hours
            min_probability: Minimum collision probability
        """
        if not await self._authenticate():
            return []
        
        client = await self._get_client()
        
        # Query CDM data for Starlink
        # CDM class: https://www.space-track.org/basicspacedata/modeldef/class/cdm_public
        
        tca_start = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        tca_end = (datetime.now(timezone.utc) + timedelta(hours=hours_ahead)).strftime("%Y-%m-%d")
        
        try:
            # Query format for Space-Track
            query = (
                f"/basicspacedata/query/class/cdm_public"
                f"/TCA/{tca_start}--{tca_end}"
                f"/SAT1_NAME/~~STARLINK"  # Contains STARLINK
                f"/orderby/TCA asc"
                f"/limit/100"
                f"/format/json"
            )
            
            response = await client.get(query, cookies=self._cookies)
            
            if response.status_code != 200:
                print(f"Space-Track CDM query failed: {response.status_code}")
                return []
            
            data = response.json()
            alerts = []
            
            for item in data:
                try:
                    prob = float(item.get("PC", 0) or 0)
                    if prob < min_probability:
                        continue
                    
                    miss_km = float(item.get("MISS_DISTANCE", 0) or 0) / 1000  # m to km
                    
                    alert = CDMAlert(
                        cdm_id=item.get("CDM_ID", ""),
                        created=self._parse_datetime(item.get("CREATED")),
                        tca=self._parse_datetime(item.get("TCA")),
                        miss_distance_km=miss_km,
                        probability=prob,
                        sat1_name=item.get("SAT1_NAME", "Unknown"),
                        sat1_norad=item.get("SAT1_NORAD_CAT_ID", ""),
                        sat1_type=item.get("SAT1_OBJECT_TYPE", "UNKNOWN"),
                        sat2_name=item.get("SAT2_NAME", "Unknown"),
                        sat2_norad=item.get("SAT2_NORAD_CAT_ID", ""),
                        sat2_type=item.get("SAT2_OBJECT_TYPE", "UNKNOWN"),
                        relative_speed_km_s=float(item.get("RELATIVE_SPEED", 0) or 0) / 1000,
                        emergency=(prob > 1e-4 or miss_km < 1.0)
                    )
                    alerts.append(alert)
                    
                except Exception as e:
                    print(f"Error parsing CDM: {e}")
                    continue
            
            return alerts
            
        except Exception as e:
            print(f"Space-Track CDM error: {e}")
            return []
    
    async def get_all_cdm(
        self,
        hours_ahead: int = 72,
        limit: int = 50
    ) -> list[CDMAlert]:
        """Get all CDM alerts (not just Starlink)."""
        if not await self._authenticate():
            return []
        
        client = await self._get_client()
        
        tca_start = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        tca_end = (datetime.now(timezone.utc) + timedelta(hours=hours_ahead)).strftime("%Y-%m-%d")
        
        try:
            query = (
                f"/basicspacedata/query/class/cdm_public"
                f"/TCA/{tca_start}--{tca_end}"
                f"/orderby/PC desc"  # Highest probability first
                f"/limit/{limit}"
                f"/format/json"
            )
            
            response = await client.get(query, cookies=self._cookies)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            alerts = []
            
            for item in data:
                try:
                    prob = float(item.get("PC", 0) or 0)
                    miss_km = float(item.get("MISS_DISTANCE", 0) or 0) / 1000
                    
                    alert = CDMAlert(
                        cdm_id=item.get("CDM_ID", ""),
                        created=self._parse_datetime(item.get("CREATED")),
                        tca=self._parse_datetime(item.get("TCA")),
                        miss_distance_km=miss_km,
                        probability=prob,
                        sat1_name=item.get("SAT1_NAME", "Unknown"),
                        sat1_norad=item.get("SAT1_NORAD_CAT_ID", ""),
                        sat1_type=item.get("SAT1_OBJECT_TYPE", "UNKNOWN"),
                        sat2_name=item.get("SAT2_NAME", "Unknown"),
                        sat2_norad=item.get("SAT2_NORAD_CAT_ID", ""),
                        sat2_type=item.get("SAT2_OBJECT_TYPE", "UNKNOWN"),
                        relative_speed_km_s=float(item.get("RELATIVE_SPEED", 0) or 0) / 1000,
                        emergency=(prob > 1e-4 or miss_km < 1.0)
                    )
                    alerts.append(alert)
                    
                except Exception:
                    continue
            
            return alerts
            
        except Exception as e:
            print(f"Space-Track error: {e}")
            return []
    
    async def get_tle(self, norad_id: str) -> Optional[dict]:
        """Get latest TLE for a satellite."""
        if not await self._authenticate():
            return None
        
        client = await self._get_client()
        
        try:
            query = (
                f"/basicspacedata/query/class/tle_latest"
                f"/NORAD_CAT_ID/{norad_id}"
                f"/orderby/EPOCH desc"
                f"/limit/1"
                f"/format/json"
            )
            
            response = await client.get(query, cookies=self._cookies)
            
            if response.status_code == 200:
                data = response.json()
                return data[0] if data else None
            
            return None
            
        except Exception:
            return None
    
    def _parse_datetime(self, dt_str: Optional[str]) -> datetime:
        """Parse Space-Track datetime format."""
        if not dt_str:
            return datetime.now(timezone.utc)
        try:
            # Space-Track uses format: 2024-01-15 12:30:45
            return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except:
            try:
                return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            except:
                return datetime.now(timezone.utc)


# Global client instance
spacetrack_client = SpaceTrackClient()
