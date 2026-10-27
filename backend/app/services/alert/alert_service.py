"""SentinelAPI Alert & Incident Management Service.

Coordinates incident lifecycle, alert triage, manual mitigation, and false-positive tracking.
"""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional
from backend.app.schemas.alert import AlertMitigateRequest, AlertRecord, AlertStatus, AlertUpdate
from backend.app.schemas.anomaly import AnomalyRecord, SeverityLevel
from backend.app.schemas.policy import PolicyAction
from backend.app.services.detection.engine import anomaly_engine
from backend.app.services.policy.actions.ban_manager import ip_ban_manager
from backend.app.services.policy.actions.quarantine_manager import quarantine_manager

logger = logging.getLogger("sentinelapi.alerts")


class AlertService:
    """Manages security alerts and analyst workflows."""

    def __init__(self):
        self._alerts: Dict[str, AlertRecord] = {}  # alert_id -> AlertRecord
        self._alerts_by_anomaly_id: Dict[str, str] = {}  # anomaly_id -> alert_id
        self._lock = asyncio.Lock()

    def _sync_with_anomalies(self) -> None:
        """Generates alert records for any newly detected anomalies."""
        anomalies = anomaly_engine.list_anomalies(limit=200)
        for a in anomalies:
            if a.anomaly_id not in self._alerts_by_anomaly_id:
                # Derive title
                factors_str = a.contributing_factors[0] if a.contributing_factors else "High risk anomalous behavior"
                title = f"{a.severity.value.upper()} Alert: {factors_str[:80]}"

                alert = AlertRecord(
                    anomaly_id=a.anomaly_id,
                    event_id=a.event_id,
                    title=title,
                    description=f"Anomaly detected on {a.http_method} {a.path} from client {a.client_ip}. Risk: {a.risk_score:.1f}.",
                    severity=a.severity,
                    risk_score=a.risk_score,
                    status=AlertStatus.NEW,
                    endpoint=a.path,
                    http_method=a.http_method,
                    client_ip=a.client_ip,
                    client_id=a.client_id,
                    contributing_factors=list(a.contributing_factors),
                    event_snapshot=dict(a.event_snapshot),
                    created_at=a.timestamp,
                    updated_at=a.timestamp,
                )
                self._alerts[alert.alert_id] = alert
                self._alerts_by_anomaly_id[a.anomaly_id] = alert.alert_id

    async def list_alerts(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AlertRecord]:
        """Lists alerts with filtering and pagination."""
        async with self._lock:
            self._sync_with_anomalies()
            results = list(self._alerts.values())

            if status:
                results = [a for a in results if a.status.value == status.lower()]
            if severity:
                results = [a for a in results if a.severity.value == severity.lower()]

            results.sort(key=lambda x: x.created_at, reverse=True)
            return results[offset : offset + limit]

    async def get_alert(self, alert_id: str) -> Optional[AlertRecord]:
        """Retrieves a single alert by its ID."""
        async with self._lock:
            self._sync_with_anomalies()
            return self._alerts.get(alert_id)

    async def update_alert(self, alert_id: str, req: AlertUpdate) -> Optional[AlertRecord]:
        """Updates alert status, assignee, or appends notes."""
        async with self._lock:
            alert = self._alerts.get(alert_id)
            if not alert:
                return None

            if req.status:
                alert.status = req.status
            if req.assignee is not None:
                alert.assignee = req.assignee
            if req.note:
                ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                alert.notes.append(f"[{ts}] {req.note}")

            alert.updated_at = datetime.now(timezone.utc)
            return alert

    async def mitigate_alert(self, alert_id: str, req: AlertMitigateRequest) -> Optional[AlertRecord]:
        """Executes a defensive mitigation for an alert."""
        async with self._lock:
            alert = self._alerts.get(alert_id)
            if not alert:
                return None

            if req.action == PolicyAction.BLOCK:
                await ip_ban_manager.ban_ip(
                    ip=alert.client_ip,
                    duration_seconds=req.ban_duration_seconds,
                    reason=f"Alert mitigation: {req.reason}",
                    policy_id="manual_alert_mitigation",
                )
            elif req.action == PolicyAction.QUARANTINE:
                await quarantine_manager.quarantine(
                    client_ip=alert.client_ip,
                    client_id=alert.client_id,
                    reason=f"Alert quarantine: {req.reason}",
                )

            alert.status = AlertStatus.MITIGATED
            alert.mitigation_action = req.action
            alert.notes.append(f"Mitigated via {req.action.value.upper()}: {req.reason}")
            alert.updated_at = datetime.now(timezone.utc)
            return alert

    async def mark_false_positive(self, alert_id: str, reason: str = "") -> Optional[AlertRecord]:
        """Marks an alert as false positive."""
        async with self._lock:
            alert = self._alerts.get(alert_id)
            if not alert:
                return None

            alert.status = AlertStatus.FALSE_POSITIVE
            note = f"Marked as False Positive. Reason: {reason}" if reason else "Marked as False Positive."
            alert.notes.append(note)
            alert.updated_at = datetime.now(timezone.utc)
            return alert


# Global singleton instance
alert_service = AlertService()
