"""SpaceX API client service."""
import httpx
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from app.core.config import get_settings


@dataclass
class StarlinkSatellite:
    """Starlink satellite metadata."""
    id: str
    version: str
    launch_date: Optional[datetime]
    longitude: Optional[float]
    latitude: Optional[float]
    height_km: Optional[float]
    velocity_kms: Optional[float]
    spacetrack: dict
    
    @classmethod
    def from_api(cls, data: dict) -> "StarlinkSatellite":
        launch_date = None
        if data.get("spaceTrack", {}).get("LAUNCH_DATE"):
            try:
                launch_date = datetime.fromisoformat(
                    data["spaceTrack"]["LAUNCH_DATE"].replace("Z", "+00:00")
                )
            except:
                pass
        
        return cls(
            id=data.get("id", ""),
            version=data.get("version", "unknown"),
            launch_date=launch_date,
            longitude=data.get("longitude"),
            latitude=data.get("latitude"),
            height_km=data.get("height_km"),
            velocity_kms=data.get("velocity_kms"),
            spacetrack=data.get("spaceTrack", {})
        )
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "version": self.version,
            "launch_date": self.launch_date.isoformat() if self.launch_date else None,
            "position": {
                "longitude": self.longitude,
                "latitude": self.latitude,
                "height_km": self.height_km
            },
            "velocity_kms": self.velocity_kms,
            "norad_id": self.spacetrack.get("NORAD_CAT_ID"),
            "object_name": self.spacetrack.get("OBJECT_NAME"),
            "decay_date": self.spacetrack.get("DECAY_DATE")
        }


@dataclass
class Launch:
    """SpaceX launch data."""
    id: str
    name: str
    date_utc: datetime
    success: Optional[bool]
    rocket_id: str
    launchpad_id: str
    details: Optional[str]
    cores: list[dict]
    payloads: list[str]
    links: dict
    
    @classmethod
    def from_api(cls, data: dict) -> "Launch":
        date_utc = datetime.fromisoformat(
            data.get("date_utc", "").replace("Z", "+00:00")
        )
        
        return cls(
            id=data.get("id", ""),
            name=data.get("name", "Unknown"),
            date_utc=date_utc,
            success=data.get("success"),
            rocket_id=data.get("rocket", ""),
            launchpad_id=data.get("launchpad", ""),
            details=data.get("details"),
            cores=data.get("cores", []),
            payloads=data.get("payloads", []),
            links=data.get("links", {})
        )
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "date_utc": self.date_utc.isoformat(),
            "success": self.success,
            "rocket_id": self.rocket_id,
            "launchpad_id": self.launchpad_id,
            "details": self.details,
            "cores": self.cores,
            "payload_count": len(self.payloads),
            "webcast": self.links.get("webcast"),
            "patch": self.links.get("patch", {}).get("small")
        }


@dataclass
class Core:
    """SpaceX booster core data."""
    id: str
    serial: str
    reuse_count: int
    status: str
    last_update: Optional[str]
    launches: list[str]
    
    @classmethod
    def from_api(cls, data: dict) -> "Core":
        return cls(
            id=data.get("id", ""),
            serial=data.get("serial", "Unknown"),
            reuse_count=data.get("reuse_count", 0),
            status=data.get("status", "unknown"),
            last_update=data.get("last_update"),
            launches=data.get("launches", [])
        )
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "serial": self.serial,
            "reuse_count": self.reuse_count,
            "status": self.status,
            "last_update": self.last_update,
            "launch_count": len(self.launches)
        }


class SpaceXAPIClient:
    """Client for SpaceX public API."""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.spacex_api_url
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0
            )
        return self._client
    
    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def get_starlink_satellites(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> list[StarlinkSatellite]:
        """Fetch Starlink satellite data."""
        client = await self._get_client()
        
        # SpaceX API uses POST with query body
        response = await client.post(
            "/starlink/query",
            json={
                "query": {},
                "options": {
                    "limit": limit,
                    "offset": offset,
                    "sort": {"launch": "desc"}
                }
            }
        )
        response.raise_for_status()
        
        data = response.json()
        satellites = [StarlinkSatellite.from_api(s) for s in data.get("docs", [])]
        
        return satellites
    
    async def get_all_starlink(self) -> list[StarlinkSatellite]:
        """Fetch all Starlink satellites (paginated)."""
        all_satellites = []
        offset = 0
        limit = 500
        
        while True:
            batch = await self.get_starlink_satellites(limit=limit, offset=offset)
            if not batch:
                break
            all_satellites.extend(batch)
            offset += limit
            
            # Safety limit
            if offset > 10000:
                break
        
        return all_satellites
    
    async def get_launches(
        self,
        limit: int = 50,
        upcoming: bool = False
    ) -> list[Launch]:
        """Fetch launch data."""
        client = await self._get_client()
        
        query = {"upcoming": upcoming} if upcoming else {}
        
        response = await client.post(
            "/launches/query",
            json={
                "query": query,
                "options": {
                    "limit": limit,
                    "sort": {"date_utc": "desc" if not upcoming else "asc"}
                }
            }
        )
        response.raise_for_status()
        
        data = response.json()
        return [Launch.from_api(l) for l in data.get("docs", [])]
    
    async def get_cores(self, limit: int = 50) -> list[Core]:
        """Fetch booster core data."""
        client = await self._get_client()
        
        response = await client.post(
            "/cores/query",
            json={
                "query": {},
                "options": {
                    "limit": limit,
                    "sort": {"reuse_count": "desc"}
                }
            }
        )
        response.raise_for_status()
        
        data = response.json()
        return [Core.from_api(c) for c in data.get("docs", [])]
    
    async def get_statistics(self) -> dict:
        """Get fleet statistics."""
        client = await self._get_client()
        
        # Get counts
        starlink_resp = await client.post(
            "/starlink/query",
            json={"query": {}, "options": {"limit": 1}}
        )
        starlink_data = starlink_resp.json()
        
        launches_resp = await client.post(
            "/launches/query",
            json={"query": {}, "options": {"limit": 1}}
        )
        launches_data = launches_resp.json()
        
        cores_resp = await client.post(
            "/cores/query",
            json={"query": {}, "options": {"limit": 1}}
        )
        cores_data = cores_resp.json()
        
        return {
            "total_starlink": starlink_data.get("totalDocs", 0),
            "total_launches": launches_data.get("totalDocs", 0),
            "total_cores": cores_data.get("totalDocs", 0)
        }


# Global client instance
spacex_client = SpaceXAPIClient()
