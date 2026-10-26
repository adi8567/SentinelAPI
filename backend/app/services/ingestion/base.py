"""Base Log Parser Interface and Common Utilities."""

import abc
import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse
from dateutil import parser as dt_parser

from backend.app.schemas.events import ApiEvent, AuthType, LogSource

SENSITIVE_HEADER_KEYS = {
    "authorization",
    "proxy-authorization",
    "x-api-key",
    "cookie",
    "set-cookie",
    "x-sentinel-key",
    "token",
    "x-auth-token",
}


def sanitize_headers(headers: Dict[str, Any]) -> Dict[str, str]:
    """Redacts sensitive credentials from headers summary."""
    cleaned = {}
    for k, v in headers.items():
        k_lower = str(k).lower().strip()
        val_str = str(v)
        if k_lower in SENSITIVE_HEADER_KEYS:
            cleaned[k_lower] = "[REDACTED]"
        else:
            # Truncate overly long header values to conserve storage
            cleaned[k_lower] = val_str[:256]
    return cleaned


def extract_auth_info(headers: Dict[str, Any]) -> Tuple[AuthType, Optional[str]]:
    """Inspects headers to classify auth type and generates a safe identity hash."""
    headers_lower = {str(k).lower().strip(): str(v) for k, v in headers.items()}

    auth_header = headers_lower.get("authorization", "")
    if auth_header:
        auth_header_strip = auth_header.strip()
        if auth_header_strip.lower().startswith("bearer "):
            token = auth_header_strip[7:].strip()
            # Generate deterministic SHA-256 fingerprint for behavioral tracking
            fingerprint = f"sha256:{hashlib.sha256(token.encode('utf-8')).hexdigest()[:16]}"
            return AuthType.BEARER, fingerprint
        elif auth_header_strip.lower().startswith("basic "):
            creds = auth_header_strip[6:].strip()
            fingerprint = f"basic:{hashlib.sha256(creds.encode('utf-8')).hexdigest()[:16]}"
            return AuthType.BASIC, fingerprint
        elif "oauth" in auth_header_strip.lower():
            return AuthType.OAUTH2, None
        return AuthType.UNKNOWN, None

    if "x-api-key" in headers_lower or "api-key" in headers_lower:
        raw_key = headers_lower.get("x-api-key") or headers_lower.get("api-key", "")
        fingerprint = f"key:{hashlib.sha256(raw_key.encode('utf-8')).hexdigest()[:16]}"
        return AuthType.API_KEY, fingerprint

    return AuthType.NONE, None


def parse_timestamp_flexible(ts_value: Any) -> datetime:
    """Parses timestamps across multiple string, epoch, or float formats."""
    if isinstance(ts_value, datetime):
        if ts_value.tzinfo is None:
            return ts_value.replace(tzinfo=timezone.utc)
        return ts_value.astimezone(timezone.utc)

    if isinstance(ts_value, (int, float)):
        # Epoch seconds, milliseconds, microseconds, or nanoseconds
        val = float(ts_value)
        if val > 1e16:  # nanoseconds
            val /= 1e9
        elif val > 1e13:  # microseconds
            val /= 1e6
        elif val > 1e10:  # milliseconds
            val /= 1e3
        return datetime.fromtimestamp(val, tz=timezone.utc)

    if isinstance(ts_value, str):
        ts_str = ts_value.strip().strip("[]")
        # Handle Nginx / Common Log format: 25/Oct/2026:12:00:00 +0000
        try:
            return datetime.strptime(ts_str, "%d/%b/%Y:%H:%M:%S %z").astimezone(timezone.utc)
        except ValueError:
            pass

        try:
            parsed = dt_parser.parse(ts_str)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except Exception:
            pass

    return datetime.now(timezone.utc)


def parse_uri_parts(uri: str) -> Tuple[str, str, Dict[str, Any]]:
    """Extracts normalized path, full path, and query params from a raw URI."""
    if not uri:
        return "/", "/", {}
    parsed = urlparse(uri)
    path = parsed.path if parsed.path else "/"
    if not path.startswith("/"):
        path = "/" + path
    raw_path = uri
    raw_params = parse_qs(parsed.query, keep_blank_values=True)
    # Simplify query param dict: single values kept as string
    query_params: Dict[str, Any] = {}
    for k, v in raw_params.items():
        query_params[k] = v[0] if len(v) == 1 else v
    return path, raw_path, query_params


class BaseLogParser(abc.ABC):
    """Abstract interface for all API gateway log parsers."""

    source_type: LogSource

    @abc.abstractmethod
    def can_parse(self, sample_line: str) -> bool:
        """Heuristic check whether this parser can parse the given log line."""
        pass

    @abc.abstractmethod
    def parse_line(self, line: str, gateway_id: str = "default-gw") -> ApiEvent:
        """Parses a single log line into a normalized ApiEvent."""
        pass

    def parse_batch(
        self, lines: List[str], gateway_id: str = "default-gw"
    ) -> Tuple[List[ApiEvent], List[Tuple[int, str, str]]]:
        """Parses a list of lines, returning (valid_events, errors)."""
        valid_events: List[ApiEvent] = []
        errors: List[Tuple[int, str, str]] = []

        for idx, line in enumerate(lines):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                event = self.parse_line(line_str, gateway_id=gateway_id)
                valid_events.append(event)
            except Exception as e:
                errors.append((idx, line_str[:120], str(e)))

        return valid_events, errors
