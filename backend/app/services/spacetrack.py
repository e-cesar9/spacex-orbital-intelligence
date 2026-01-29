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
class SatelliteCatalogEntry:
    """Enriched satellite information from catalog."""
    norad_id: str
    name: str
    object_type: str
    country: str
    launch_date: Optional[str] = None
    decay_date: Optional[str] = None
    owner: Optional[str] = None
    purpose: Optional[str] = None
    perigee_km: Optional[float] = None
    apogee_km: Optional[float] = None
    inclination_deg: Optional[float] = None


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
    
    # Enriched catalog data (optional)
    sat1_catalog: Optional[SatelliteCatalogEntry] = None
    sat2_catalog: Optional[SatelliteCatalogEntry] = None
    
    def to_dict(self) -> dict:
        result = {
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
        
        # Add enriched catalog data if available
        if self.sat1_catalog:
            result["satellite_1"]["catalog"] = {
                "country": self.sat1_catalog.country,
                "owner": self.sat1_catalog.owner,
                "purpose": self.sat1_catalog.purpose,
                "launch_date": self.sat1_catalog.launch_date,
                "orbit": {
                    "perigee_km": self.sat1_catalog.perigee_km,
                    "apogee_km": self.sat1_catalog.apogee_km,
                    "inclination_deg": self.sat1_catalog.inclination_deg
                }
            }
        
        if self.sat2_catalog:
            result["satellite_2"]["catalog"] = {
                "country": self.sat2_catalog.country,
                "owner": self.sat2_catalog.owner,
                "purpose": self.sat2_catalog.purpose,
                "launch_date": self.sat2_catalog.launch_date,
                "orbit": {
                    "perigee_km": self.sat2_catalog.perigee_km,
                    "apogee_km": self.sat2_catalog.apogee_km,
                    "inclination_deg": self.sat2_catalog.inclination_deg
                }
            }
        
        return result
    
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
        
        # Get credentials from settings (loads from .env)
        self.username = self.settings.spacetrack_username
        self.password = self.settings.spacetrack_password
    
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
    
    async def get_satellite_catalog(self, norad_ids: list[str]) -> dict[str, SatelliteCatalogEntry]:
        """
        Fetch satellite catalog entries for given NORAD IDs.
        
        Returns a dict mapping NORAD ID to catalog entry.
        """
        if not await self._authenticate() or not norad_ids:
            return {}
        
        client = await self._get_client()
        result = {}
        
        try:
            # Query satcat for multiple IDs at once
            ids_str = ",".join(norad_ids[:50])  # Limit to 50 at a time
            
            query = (
                f"/basicspacedata/query/class/satcat"
                f"/NORAD_CAT_ID/{ids_str}"
                f"/format/json"
            )
            
            response = await client.get(query, cookies=self._cookies)
            
            if response.status_code == 200:
                data = response.json()
                
                for item in data:
                    norad = item.get("NORAD_CAT_ID", "")
                    if norad:
                        result[norad] = SatelliteCatalogEntry(
                            norad_id=norad,
                            name=item.get("SATNAME", "Unknown"),
                            object_type=item.get("OBJECT_TYPE", "UNKNOWN"),
                            country=item.get("COUNTRY", "UNKNOWN"),
                            launch_date=item.get("LAUNCH", None),
                            decay_date=item.get("DECAY", None),
                            owner=item.get("OWNER", None),
                            purpose=self._get_purpose(item.get("SATNAME", "")),
                            perigee_km=float(item.get("PERIGEE", 0) or 0),
                            apogee_km=float(item.get("APOGEE", 0) or 0),
                            inclination_deg=float(item.get("INCLINATION", 0) or 0)
                        )
        
        except Exception as e:
            print(f"Catalog fetch error: {e}")
        
        return result
    
    def _get_purpose(self, name: str) -> str:
        """Infer satellite purpose from name."""
        name_upper = name.upper()
        if "STARLINK" in name_upper:
            return "Internet/Communications"
        elif "COSMOS" in name_upper or "KOSMOS" in name_upper:
            return "Military/Government"
        elif "ISS" in name_upper:
            return "Space Station"
        elif "GPS" in name_upper or "NAVSTAR" in name_upper:
            return "Navigation"
        elif "WEATHER" in name_upper or "NOAA" in name_upper or "METEO" in name_upper:
            return "Weather"
        elif any(x in name_upper for x in ["DEB", "R/B", "DEBRIS"]):
            return "Debris"
        else:
            return "Unknown"
    
    async def get_cdm_enriched(
        self,
        hours_ahead: int = 72,
        limit: int = 50
    ) -> list[CDMAlert]:
        """
        Get CDM alerts enriched with satellite catalog data.
        
        This cross-references CDM data with the satellite catalog
        to provide additional context about involved objects.
        """
        # First get basic CDM alerts
        alerts = await self.get_all_cdm(hours_ahead=hours_ahead, limit=limit)
        
        if not alerts:
            return alerts
        
        # Collect all unique NORAD IDs
        norad_ids = set()
        for alert in alerts:
            if alert.sat1_norad:
                norad_ids.add(alert.sat1_norad)
            if alert.sat2_norad:
                norad_ids.add(alert.sat2_norad)
        
        # Fetch catalog data
        catalog = await self.get_satellite_catalog(list(norad_ids))
        
        # Enrich alerts
        for alert in alerts:
            if alert.sat1_norad in catalog:
                alert.sat1_catalog = catalog[alert.sat1_norad]
            if alert.sat2_norad in catalog:
                alert.sat2_catalog = catalog[alert.sat2_norad]
        
        return alerts
    
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
