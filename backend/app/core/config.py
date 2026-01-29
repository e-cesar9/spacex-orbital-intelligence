"""Application configuration."""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # App
    app_name: str = "SpaceX Orbital Intelligence"
    debug: bool = False
    api_prefix: str = "/api/v1"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    
    # Database
    database_url: str = "postgresql+asyncpg://spacex:spacex@localhost:5432/spacex_orbital"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl: int = 300  # 5 minutes
    
    # External APIs
    spacex_api_url: str = "https://api.spacexdata.com/v4"
    celestrak_url: str = "https://celestrak.org/NORAD/elements/gp.php"
    
    # Space-Track API (optional, CelesTrak works without auth)
    spacetrack_username: str = ""
    spacetrack_password: str = ""
    
    # TLE refresh interval (seconds)
    tle_refresh_interval: int = 3600  # 1 hour
    
    # WebSocket
    ws_broadcast_interval: float = 1.0  # seconds
    
    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
