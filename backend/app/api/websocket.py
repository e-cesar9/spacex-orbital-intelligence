"""WebSocket endpoint for real-time satellite positions."""
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set
import structlog

from app.services.orbital_engine import orbital_engine
from app.services.tle_service import tle_service
from app.services.mock_satellites import mock_generator
from app.core.config import get_settings

logger = structlog.get_logger()
router = APIRouter()

# Connected clients
clients: Set[WebSocket] = set()


class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._broadcast_task = None
    
    async def connect(self, websocket: WebSocket):
        """Accept and register new connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("WebSocket connected", total=len(self.active_connections))
        
        # Start broadcast task if not running
        if self._broadcast_task is None or self._broadcast_task.done():
            self._broadcast_task = asyncio.create_task(self._broadcast_loop())
    
    def disconnect(self, websocket: WebSocket):
        """Remove connection."""
        self.active_connections.discard(websocket)
        logger.info("WebSocket disconnected", total=len(self.active_connections))
    
    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        if not self.active_connections:
            return
        
        data = json.dumps(message)
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                await connection.send_text(data)
            except Exception:
                disconnected.add(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.active_connections.discard(conn)
    
    async def _broadcast_loop(self):
        """Continuously broadcast satellite positions."""
        settings = get_settings()
        
        while self.active_connections:
            try:
                # Try TLE data first
                positions = []
                try:
                    await tle_service.ensure_data_loaded()
                    positions = orbital_engine.get_all_positions()
                except Exception:
                    pass
                
                if positions:
                    # Use real TLE data
                    message = {
                        "type": "positions",
                        "count": len(positions),
                        "source": "tle",
                        "data": [
                            {
                                "id": p.satellite_id,
                                "lat": round(p.latitude, 4),
                                "lon": round(p.longitude, 4),
                                "alt": round(p.altitude, 2)
                            }
                            for p in positions
                        ]
                    }
                else:
                    # Fall back to mock data
                    mock_positions = mock_generator.get_all_positions()
                    message = {
                        "type": "positions",
                        "count": len(mock_positions),
                        "source": "simulated",
                        "data": mock_positions
                    }
                
                await self.broadcast(message)
                
            except Exception as e:
                logger.error("Broadcast error", error=str(e))
            
            await asyncio.sleep(settings.ws_broadcast_interval)
        
        logger.info("Broadcast loop stopped - no clients")


manager = ConnectionManager()


@router.websocket("/ws/positions")
async def websocket_positions(websocket: WebSocket):
    """WebSocket endpoint for real-time satellite positions."""
    await manager.connect(websocket)
    
    try:
        while True:
            # Keep connection alive, handle client messages
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                
                # Handle client commands
                try:
                    message = json.loads(data)
                    
                    if message.get("type") == "subscribe":
                        # Client wants specific satellite updates
                        sat_id = message.get("satellite_id")
                        if sat_id:
                            pos = orbital_engine.propagate(sat_id)
                            if pos:
                                await websocket.send_json({
                                    "type": "satellite",
                                    "data": pos.to_dict()
                                })
                    
                    elif message.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                        
                except json.JSONDecodeError:
                    pass
                    
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_json({"type": "ping"})
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
        manager.disconnect(websocket)
