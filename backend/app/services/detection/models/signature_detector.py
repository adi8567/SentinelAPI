"""Signature and OWASP API Threat Pattern Detector.

Detects active API security exploits: Broken Object Level Authorization (BOLA/IDOR),
Credential Stuffing / Brute Force, SQL Injection, and Path Traversal probes.
"""

from collections import defaultdict
from datetime import datetime, timezone
import re
from typing import Dict, List, Set
from urllib.parse import unquote

from backend.app.schemas.anomaly import DetectorResult, DetectorType
from backend.app.schemas.events import ApiEvent

# Regular expressions for security exploits
SQLI_PATTERN = re.compile(
    r"('|--|/\*|;|union\s+select|select\s+.*from|or\s+['\d]=['\d]|drop\s+table|exec\(|benchmark\()",
    re.IGNORECASE,
)
TRAVERSAL_PATTERN = re.compile(
    r"(\.\./|\.\.\\|/etc/passwd|/windows/win\.ini|/debug/env|\.env$)",
    re.IGNORECASE,
)
SCANNER_UA_PATTERN = re.compile(
    r"(sqlmap|nikto|nmap|masscan|dirbuster|acunetix|nessus)",
    re.IGNORECASE,
)


class SignatureThreatDetector:
    """Detects OWASP API Top 10 attack signatures and brute-force behavioral patterns."""

    def __init__(self):
        # Sliding state for BOLA and brute-force tracking: client_ip -> list of (timestamp, path, status)
        self._client_history: Dict[str, List[tuple]] = defaultdict(list)

    def evaluate(self, event: ApiEvent) -> DetectorResult:
        score = 0.0
        reasons = []
        now = event.timestamp

        raw_uri = unquote(event.raw_path)
        user_agent = event.user_agent or ""

        # 1. SQL Injection Detection in Path or Query Parameters
        if SQLI_PATTERN.search(raw_uri):
            score += 85.0
            reasons.append(f"SQL Injection attack probe detected in request: '{raw_uri[:80]}'")

        for k, v in event.query_params.items():
            val_str = unquote(str(v))
            if SQLI_PATTERN.search(val_str):
                score += 85.0
                reasons.append(f"SQL Injection payload in query parameter '{k}': '{val_str[:60]}'")
                break

        # 2. Path Traversal & Sensitive File Probe Detection
        if TRAVERSAL_PATTERN.search(raw_uri):
            score += 80.0
            reasons.append(f"Directory traversal / sensitive file extraction probe detected: '{raw_uri[:80]}'")

        # 3. Security Scanner User-Agent Fingerprint
        if SCANNER_UA_PATTERN.search(user_agent):
            score += 75.0
            reasons.append(f"Automated vulnerability scanner User-Agent identified: '{user_agent}'")

        # 4. State Tracking for BOLA / IDOR and Credential Stuffing
        history = self._client_history[event.client_ip]
        # Clean records older than 5 minutes
        cutoff = now.timestamp() - 300
        history = [item for item in history if item[0].timestamp() > cutoff]
        history.append((now, event.path, event.status_code))
        self._client_history[event.client_ip] = history

        # Check for BOLA / IDOR Pattern: Multiple forbidden (403) responses on entity routes
        recent_403s = [h for h in history if h[2] == 403 and any(seg.isdigit() or "_" in seg for seg in h[1].split("/"))]
        if len(recent_403s) >= 3:
            score += 75.0
            distinct_entities = len(set(h[1] for h in recent_403s))
            reasons.append(
                f"BOLA / IDOR Object Level Authorization attack: {len(recent_403s)} consecutive 403 Forbidden "
                f"responses across {distinct_entities} distinct resource IDs"
            )

        # Check for Credential Stuffing / Auth Brute Force
        if "/auth" in event.path or "/login" in event.path:
            recent_failed_logins = [h for h in history if ("/auth" in h[1] or "/login" in h[1]) and h[2] in {401, 429}]
            if len(recent_failed_logins) >= 4:
                score += 80.0
                reasons.append(
                    f"Credential Stuffing / Brute Force attack: {len(recent_failed_logins)} failed auth attempts "
                    f"(401/429) detected in short interval"
                )

        score = min(100.0, score)
        is_anomaly = score >= 50.0

        return DetectorResult(
            detector_name=DetectorType.SIGNATURE.value,
            is_anomaly=is_anomaly,
            score=round(score, 1),
            confidence=0.95 if score > 0 else 0.5,
            reasons=reasons,
        )
