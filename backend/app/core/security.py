"""
Security middleware and utilities.

- API key authentication for sensitive endpoints
- Rate limiting
- CORS configuration
"""
import os
import secrets
from functools import wraps
from typing import Optional

from fastapi import Request, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# API Key header
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Generate default API key if not set
def get_api_key() -> str:
    """Get API key from environment or generate one."""
    key = os.environ.get("SPACEX_API_KEY")
    if not key:
        # Generate and log a key for first run
        key = secrets.token_urlsafe(32)
        print(f"[SECURITY] No SPACEX_API_KEY set. Generated: {key}")
        print(f"[SECURITY] Set SPACEX_API_KEY={key} in .env for persistence")
    return key

# Cached API key
_api_key: Optional[str] = None

def get_valid_api_key() -> str:
    """Get the valid API key (cached)."""
    global _api_key
    if _api_key is None:
        _api_key = get_api_key()
    return _api_key


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> bool:
    """Verify the API key for protected endpoints."""
    if api_key is None:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include X-API-Key header."
        )
    
    if api_key != get_valid_api_key():
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    
    return True


def require_api_key(func):
    """Decorator to require API key for an endpoint."""
    @wraps(func)
    async def wrapper(*args, api_key: bool = Depends(verify_api_key), **kwargs):
        return await func(*args, **kwargs)
    return wrapper


# Allowed origins for CORS (production)
def get_allowed_origins() -> list[str]:
    """Get allowed CORS origins from environment."""
    origins_str = os.environ.get("CORS_ORIGINS", "")
    if origins_str:
        return [o.strip() for o in origins_str.split(",")]
    
    # Default: allow common local dev + the production domain
    return [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "https://spacex.ericcesar.com",
    ]


# IP-based rate limit check
def is_rate_limited(request: Request, limit: int = 100, window: int = 60) -> bool:
    """Simple rate limit check (use slowapi decorator for actual limiting)."""
    # This is handled by slowapi limiter decorator
    return False
