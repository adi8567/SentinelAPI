"""SentinelAPI Webhook Notification Dispatcher.

Dispatches non-blocking HTTP webhook notifications to external SIEMs, Slack,
PagerDuty, or incident response systems when adaptive protection actions trigger.
"""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import httpx
from backend.app.schemas.policy import PolicyDecision

logger = logging.getLogger("sentinelapi.policy.webhook")


class WebhookDispatcher:
    """Asynchronous dispatcher for adaptive response webhooks."""

    def __init__(self, default_webhook_url: Optional[str] = None, timeout_seconds: float = 3.0):
        self.default_webhook_url = default_webhook_url
        self.timeout_seconds = timeout_seconds
        self._dispatched_count = 0
        self._dispatch_history: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self.is_dry_run = False  # If True, records dispatch without HTTP call

    async def dispatch(
        self,
        decision: PolicyDecision,
        webhook_url: Optional[str] = None,
        custom_payload: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Dispatches an alert webhook for a policy decision asynchronously."""
        target_url = webhook_url or self.default_webhook_url
        if not target_url and not self.is_dry_run:
            logger.debug("No webhook URL configured; skipping external dispatch.")
            return False

        payload = custom_payload or {
            "sentinel_alert_type": "adaptive_protection_action",
            "decision_id": decision.decision_id,
            "timestamp": decision.timestamp.isoformat(),
            "action_taken": decision.action_taken.value,
            "policy_id": decision.matched_policy_id,
            "policy_name": decision.matched_policy_name,
            "reason": decision.reason,
            "risk_score": decision.risk_score,
            "severity": decision.severity.value,
            "client_ip": decision.client_ip,
            "endpoint": decision.endpoint,
            "http_method": decision.http_method,
            "action_details": decision.action_details,
        }

        async with self._lock:
            self._dispatched_count += 1
            self._dispatch_history.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "url": target_url or "mock://dry-run",
                "decision_id": decision.decision_id,
                "action": decision.action_taken.value,
                "status": "dispatched" if not self.is_dry_run else "simulated",
            })
            if len(self._dispatch_history) > 200:
                self._dispatch_history.pop(0)

        if self.is_dry_run or not target_url:
            logger.info(f"[WEBHOOK SIMULATED] Action={decision.action_taken.value} IP={decision.client_ip}")
            return True

        # Non-blocking network dispatch
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(target_url, json=payload)
                if resp.is_success:
                    logger.info(f"[WEBHOOK SUCCESS] Target={target_url} Status={resp.status_code}")
                    return True
                else:
                    logger.warning(f"[WEBHOOK ERROR] Target={target_url} Status={resp.status_code}")
                    return False
        except Exception as e:
            logger.warning(f"[WEBHOOK FAILED] Target={target_url} Error={e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Returns operational metrics for webhooks."""
        return {
            "total_webhooks_dispatched": self._dispatched_count,
            "recent_dispatches_count": len(self._dispatch_history),
            "last_dispatch": self._dispatch_history[-1] if self._dispatch_history else None,
        }

    def clear_history(self) -> None:
        """Clears dispatch history."""
        self._dispatch_history.clear()
        self._dispatched_count = 0


# Global singleton instance
webhook_dispatcher = WebhookDispatcher()
