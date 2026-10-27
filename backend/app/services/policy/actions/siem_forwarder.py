"""SentinelAPI SIEM Log Forwarder.

Formats and forwards adaptive protection decisions in standard Common Event Format (CEF)
and RFC 5424 Syslog for ingestion into Splunk, IBM QRadar, Microsoft Sentinel, or Elastic SIEM.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from backend.app.schemas.anomaly import SeverityLevel
from backend.app.schemas.policy import PolicyDecision

logger = logging.getLogger("sentinelapi.policy.siem")


class SIEMForwarder:
    """Formats and exports security events in industry-standard SIEM formats."""

    def __init__(self):
        self._forwarded_records: List[str] = []
        self._total_forwarded = 0

    @staticmethod
    def _map_cef_severity(severity: SeverityLevel, risk_score: float) -> int:
        """Maps SentinelAPI severity and risk score to standard CEF severity (0-10)."""
        if severity == SeverityLevel.CRITICAL or risk_score >= 80.0:
            return 10
        elif severity == SeverityLevel.HIGH or risk_score >= 60.0:
            return 8
        elif severity == SeverityLevel.MEDIUM or risk_score >= 40.0:
            return 5
        elif severity == SeverityLevel.LOW or risk_score >= 20.0:
            return 3
        return 1

    def format_cef(self, decision: PolicyDecision) -> str:
        """Formats a PolicyDecision into ArcSight Common Event Format (CEF:0)."""
        # CEF:Version|Device Vendor|Device Product|Device Version|SignatureID|Name|Severity|Extension
        cef_sev = self._map_cef_severity(decision.severity, decision.risk_score)
        sig_id = f"POL_{decision.action_taken.value.upper()}"
        name = f"Adaptive Protection: {decision.action_taken.value.upper()}"

        # Sanitize reason for CEF value
        safe_reason = decision.reason.replace("=", "\\=").replace("|", "\\|")
        safe_endpoint = decision.endpoint.replace("=", "\\=")

        # Build extension key-value pairs
        extensions = [
            f"src={decision.client_ip}",
            f"request={safe_endpoint}",
            f"requestMethod={decision.http_method}",
            f"act={decision.action_taken.value}",
            f"msg={safe_reason}",
            f"cs1={decision.matched_policy_id or 'none'}",
            f"cs1Label=PolicyId",
            f"cfp1={decision.risk_score}",
            f"cfp1Label=RiskScore",
            f"externalId={decision.event_id}",
            f"rt={int(decision.timestamp.timestamp() * 1000)}",
        ]
        extension_str = " ".join(extensions)

        return f"CEF:0|SentinelAPI|AdaptiveProtection|1.0|{sig_id}|{name}|{cef_sev}|{extension_str}"

    def format_syslog(self, decision: PolicyDecision) -> str:
        """Formats a PolicyDecision as an RFC 5424 structured syslog message."""
        ts = decision.timestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        cef_msg = self.format_cef(decision)
        return f"<134>1 {ts} sentinelapi.local sentinelapi - POLICY_AUDIT [sentinel@32473 action=\"{decision.action_taken.value}\" ip=\"{decision.client_ip}\"] {cef_msg}"

    def forward(self, decision: PolicyDecision) -> str:
        """Formats CEF and emits structured SIEM log."""
        cef_msg = self.format_cef(decision)
        logger.info(f"[SIEM CEF] {cef_msg}")
        self._forwarded_records.append(cef_msg)
        self._total_forwarded += 1
        if len(self._forwarded_records) > 500:
            self._forwarded_records.pop(0)
        return cef_msg

    def get_stats(self) -> Dict[str, Any]:
        """Returns statistics of forwarded events."""
        return {
            "total_siem_events_forwarded": self._total_forwarded,
            "buffer_count": len(self._forwarded_records),
            "last_cef_record": self._forwarded_records[-1] if self._forwarded_records else None,
        }

    def clear(self) -> None:
        """Clears buffer (for tests)."""
        self._forwarded_records.clear()
        self._total_forwarded = 0


# Global singleton instance
siem_forwarder = SIEMForwarder()
