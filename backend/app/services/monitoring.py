"""
Collision Monitoring Service.

Provides periodic monitoring of CDM alerts and can send notifications
for critical conjunction events.
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional, Callable, Any
import json
import os

from app.services.spacetrack import spacetrack_client, CDMAlert
from app.services.cache import cache


class CollisionMonitor:
    """
    Monitors CDM alerts and triggers notifications for critical events.
    
    Can be run as a background task or scheduled via cron.
    """
    
    def __init__(self):
        self.last_check: Optional[datetime] = None
        self.known_alerts: set[str] = set()  # CDM IDs we've already seen
        self.notification_callbacks: list[Callable] = []
        self._running = False
    
    def add_notification_callback(self, callback: Callable[[CDMAlert], Any]):
        """Add a callback to be called when critical alerts are detected."""
        self.notification_callbacks.append(callback)
    
    async def check_for_alerts(
        self,
        probability_threshold: float = 1e-5,
        hours_ahead: int = 72
    ) -> dict:
        """
        Check for new CDM alerts that exceed the probability threshold.
        
        Returns a summary of the check including any new critical alerts.
        """
        if not spacetrack_client.is_configured:
            return {
                "status": "ERROR",
                "error": "Space-Track not configured",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        try:
            # Fetch current alerts
            alerts = await spacetrack_client.get_cdm_enriched(
                hours_ahead=hours_ahead,
                limit=100
            )
            
            # Filter by threshold
            significant = [
                a for a in alerts 
                if a.probability >= probability_threshold
            ]
            
            # Find new alerts we haven't seen
            new_alerts = [
                a for a in significant 
                if a.cdm_id not in self.known_alerts
            ]
            
            # Update known alerts
            for alert in significant:
                self.known_alerts.add(alert.cdm_id)
            
            # Clean old alerts (keep last 1000)
            if len(self.known_alerts) > 1000:
                self.known_alerts = set(list(self.known_alerts)[-500:])
            
            # Categorize new alerts
            critical_new = [a for a in new_alerts if a.emergency]
            high_new = [a for a in new_alerts if not a.emergency and a.probability > 1e-4]
            
            # Trigger notifications for critical alerts
            for alert in critical_new:
                for callback in self.notification_callbacks:
                    try:
                        await callback(alert) if asyncio.iscoroutinefunction(callback) else callback(alert)
                    except Exception as e:
                        print(f"Notification callback error: {e}")
            
            self.last_check = datetime.now(timezone.utc)
            
            result = {
                "status": "OK",
                "timestamp": self.last_check.isoformat(),
                "hours_ahead": hours_ahead,
                "probability_threshold": probability_threshold,
                "total_alerts": len(alerts),
                "significant_alerts": len(significant),
                "new_alerts": len(new_alerts),
                "new_critical": len(critical_new),
                "new_high": len(high_new),
                "alerts": {
                    "critical": [a.to_dict() for a in critical_new[:10]],
                    "high": [a.to_dict() for a in high_new[:10]]
                }
            }
            
            # Cache the result
            await cache.set("monitoring:last_check", result, ttl=3600)
            
            return result
            
        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def get_monitoring_status(self) -> dict:
        """Get current monitoring status."""
        cached = await cache.get("monitoring:last_check")
        
        return {
            "monitoring_active": self._running,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "known_alerts_count": len(self.known_alerts),
            "last_result": cached
        }
    
    async def start_background_monitoring(
        self,
        interval_minutes: int = 15,
        probability_threshold: float = 1e-5
    ):
        """Start continuous background monitoring."""
        if self._running:
            return {"status": "already_running"}
        
        self._running = True
        
        async def monitor_loop():
            while self._running:
                try:
                    await self.check_for_alerts(probability_threshold=probability_threshold)
                except Exception as e:
                    print(f"Monitoring error: {e}")
                
                await asyncio.sleep(interval_minutes * 60)
        
        asyncio.create_task(monitor_loop())
        
        return {
            "status": "started",
            "interval_minutes": interval_minutes,
            "threshold": probability_threshold
        }
    
    def stop_background_monitoring(self):
        """Stop background monitoring."""
        self._running = False
        return {"status": "stopped"}


# Global monitor instance
collision_monitor = CollisionMonitor()


# Example notification callbacks
async def log_notification(alert: CDMAlert):
    """Log critical alerts to console/file."""
    print(f"[ALERT] Critical conjunction: {alert.sat1_name} vs {alert.sat2_name}")
    print(f"        TCA: {alert.tca}, Miss: {alert.miss_distance_km:.3f}km, Pc: {alert.probability:.2e}")


async def webhook_notification(alert: CDMAlert):
    """Send critical alerts to a webhook (if configured)."""
    webhook_url = os.environ.get("ALERT_WEBHOOK_URL")
    if not webhook_url:
        return
    
    import httpx
    
    payload = {
        "type": "collision_alert",
        "severity": "CRITICAL" if alert.emergency else "HIGH",
        "data": alert.to_dict()
    }
    
    try:
        async with httpx.AsyncClient() as client:
            await client.post(webhook_url, json=payload, timeout=10)
    except Exception as e:
        print(f"Webhook notification failed: {e}")


# Register default callbacks
collision_monitor.add_notification_callback(log_notification)
