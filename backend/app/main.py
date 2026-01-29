"""SpaceX Orbital Intelligence Platform - FastAPI Application."""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
import time

from app.core.config import get_settings
from app.services.cache import cache
from app.services.tle_service import tle_service
from app.services.spacex_api import spacex_client
from app.api import satellites, analysis, launches, websocket, ops, analytics, launches_live

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("Starting SpaceX Orbital Intelligence Platform")
    
    # Connect to Redis (non-blocking)
    try:
        await asyncio.wait_for(cache.connect(), timeout=5)
    except Exception as e:
        logger.warning("Redis connection failed, running without cache", error=str(e))
    
    # TLE loading in background (don't block startup)
    async def load_tle_background():
        try:
            await asyncio.wait_for(tle_service.update_orbital_engine(), timeout=30)
            logger.info("TLE data loaded", count=tle_service.satellite_count)
        except Exception as e:
            logger.warning("TLE load failed, using mock data", error=str(e))
    
    # Start TLE loading in background
    asyncio.create_task(load_tle_background())
    
    # Start background TLE refresh task
    refresh_task = asyncio.create_task(tle_refresh_loop())
    
    yield
    
    # Cleanup
    refresh_task.cancel()
    try:
        await cache.disconnect()
    except:
        pass
    try:
        await spacex_client.close()
    except:
        pass
    logger.info("Application shutdown complete")


async def tle_refresh_loop():
    """Background task to refresh TLE data periodically."""
    while True:
        try:
            await asyncio.sleep(settings.tle_refresh_interval)
            await tle_service.update_orbital_engine()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("TLE refresh failed", error=str(e))


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Real-time orbital intelligence for SpaceX Starlink constellation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing."""
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    logger.info(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round(duration * 1000, 2)
    )
    
    return response


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Include routers
app.include_router(satellites.router, prefix=settings.api_prefix)
app.include_router(analysis.router, prefix=settings.api_prefix)
app.include_router(launches.router, prefix=settings.api_prefix)
app.include_router(ops.router, prefix=settings.api_prefix)
app.include_router(analytics.router, prefix=settings.api_prefix)
app.include_router(launches_live.router, prefix=settings.api_prefix)
app.include_router(websocket.router)


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "satellites_loaded": tle_service.satellite_count,
        "cache_connected": cache.is_connected,
        "last_tle_update": tle_service.last_update.isoformat() if tle_service.last_update else None
    }


# Root endpoint
@app.get("/")
async def root():
    """API information."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "websocket": "/ws/positions"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
