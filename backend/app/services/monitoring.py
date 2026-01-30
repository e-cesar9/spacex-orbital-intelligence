"""
Collision Monitoring Service.

Provides periodic monitoring of CDM alerts and can send notifications
for critical conjunction events.

Implements hysteresis to avoid alert storms:
- Alerts only fire after N consecutive checks above threshold
- Alerts only clear after N consecutive checks below threshold
- Tracks probability trends to detect oscillation
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional, Callable, Any
from dataclasses import dataclass, field
import json
import os

from app.services.spacetrack import spacetrack_client, CDMAlert
from app.services.cache import cache


@dataclass
class AlertState:
    """Tracks state for hysteresis logic."""
    cdm_id: str
    first_seen: datetime
    last_seen: datetime
    consecutive_above: int = 0  # Consecutive checks above threshold
    consecutive_below: int = 0  # Consecutive checks below threshold
    alert_fired: bool = False   # Has alert been sent?
    probabilities: list = field(default_factory=list)  # Recent probability values
    
    def add_probability(self, prob: float, max_history: int = 10):
        """Track probability history for trend detection."""
        self.probabilities.append(prob)
        if len(self.probabilities) > max_history:
            self.probabilities.pop(0)
    
    @property
    def trend(self) -> str:
        """Detect probability trend: RISING, FALLING, STABLE, OSCILLATING."""
        if len(self.probabilities) < 3:
            return "UNKNOWN"
        
        diffs = [self.probabilities[i+1] - self.probabilities[i] 
                 for i in range(len(self.probabilities)-1)]
        
        rising = sum(1 for d in diffs if d > 0)
        falling = sum(1 for d in diffs if d < 0)
        
        if rising > len(diffs) * 0.7:
            return "RISING"
        elif falling > len(diffs) * 0.7:
            return "FALLING"
        elif rising > 0 and falling > 0 and abs(rising - falling) <= 1:
            return "OSCILLATING"
        return "STABLE"


class CollisionMonitor:
    """
    Monitors CDM alerts and triggers notifications for critical events.
    
    Implements hysteresis to prevent alert storms:
    - fire_threshold: consecutive checks above prob before alerting
    - clear_threshold: consecutive checks below prob before clearing
    - Detects oscillating probabilities and suppresses flapping
    
    Can be run as a background task or scheduled via cron.
    """
    
    def __init__(
        self,
        fire_threshold: int = 2,   # Alert after 2 consecutive checks
        clear_threshold: int = 3,  # Clear after 3 consecutive checks
    ):
        self.last_check: Optional[datetime] = None
        self.known_alerts: set[str] = set()  # CDM IDs we've already seen
        self.alert_states: dict[str, AlertState] = {}  # Hysteresis state per CDM
        self.fire_threshold = fire_threshold
        self.clear_threshold = clear_threshold
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
        Check for new CDM alerts with hysteresis to prevent alert storms.
        
        Hysteresis logic:
        - Track consecutive checks above/below threshold per CDM
        - Only fire alert after fire_threshold consecutive checks above
        - Only clear after clear_threshold consecutive checks below
        - Suppress oscillating alerts (probability bouncing up/down)
        
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
            
            now = datetime.now(timezone.utc)
            current_cdm_ids = set()
            alerts_to_fire = []
            alerts_to_clear = []
            suppressed_oscillating = []
            
            # Process each alert with hysteresis
            for alert in alerts:
                current_cdm_ids.add(alert.cdm_id)
                above_threshold = alert.probability >= probability_threshold
                
                # Get or create state
                if alert.cdm_id not in self.alert_states:
                    self.alert_states[alert.cdm_id] = AlertState(
                        cdm_id=alert.cdm_id,
                        first_seen=now,
                        last_seen=now
                    )
                
                state = self.alert_states[alert.cdm_id]
                state.last_seen = now
                state.add_probability(alert.probability)
                
                if above_threshold:
                    state.consecutive_above += 1
                    state.consecutive_below = 0
                    
                    # Check if we should fire (hysteresis: need N consecutive)
                    if (state.consecutive_above >= self.fire_threshold and 
                        not state.alert_fired):
                        
                        # Suppress if oscillating
                        if state.trend == "OSCILLATING":
                            suppressed_oscillating.append(alert)
                        else:
                            state.alert_fired = True
                            alerts_to_fire.append(alert)
                            self.known_alerts.add(alert.cdm_id)
                else:
                    state.consecutive_below += 1
                    state.consecutive_above = 0
                    
                    # Check if we should clear (hysteresis: need N consecutive)
                    if (state.consecutive_below >= self.clear_threshold and 
                        state.alert_fired):
                        state.alert_fired = False
                        alerts_to_clear.append(alert.cdm_id)
            
            # Clean up old states (not seen in 24h)
            stale_cutoff = now.timestamp() - 86400
            stale_ids = [
                cdm_id for cdm_id, state in self.alert_states.items()
                if state.last_seen.timestamp() < stale_cutoff
            ]
            for cdm_id in stale_ids:
                del self.alert_states[cdm_id]
                self.known_alerts.discard(cdm_id)
            
            # Categorize alerts to fire
            critical_new = [a for a in alerts_to_fire if a.emergency]
            high_new = [a for a in alerts_to_fire if not a.emergency and a.probability > 1e-4]
            
            # Trigger notifications for critical alerts
            for alert in critical_new:
                for callback in self.notification_callbacks:
                    try:
                        await callback(alert) if asyncio.iscoroutinefunction(callback) else callback(alert)
                    except Exception as e:
                        print(f"Notification callback error: {e}")
            
            self.last_check = datetime.now(timezone.utc)
            
            # Count significant (above threshold)
            significant = [a for a in alerts if a.probability >= probability_threshold]
            
            result = {
                "status": "OK",
                "timestamp": self.last_check.isoformat(),
                "hours_ahead": hours_ahead,
                "probability_threshold": probability_threshold,
                "hysteresis": {
                    "fire_threshold": self.fire_threshold,
                    "clear_threshold": self.clear_threshold,
                    "tracked_states": len(self.alert_states),
                    "active_alerts": len([s for s in self.alert_states.values() if s.alert_fired]),
                    "suppressed_oscillating": len(suppressed_oscillating)
                },
                "total_alerts": len(alerts),
                "significant_alerts": len(significant),
                "new_alerts": len(alerts_to_fire),
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
