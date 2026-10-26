"""Envoy Proxy Access Log Parser.

Parses Envoy JSON structured access logs and Envoy standard text access logs.
"""

import json
import re
from typing import Any, Dict
from backend.app.schemas.events import ApiEvent, AuthType, LogSource
from backend.app.services.ingestion.base import (
    BaseLogParser,
    extract_auth_info,
    parse_timestamp_flexible,
    parse_uri_parts,
    sanitize_headers,
)

# Standard Envoy Text Access Log Pattern
# [START_TIME] "REQ" RESPONSE_CODE RESPONSE_FLAGS BYTES_RECEIVED BYTES_SENT DURATION UPSTREAM_SERVICE_TIME "X-FORWARDED-FOR" "USER-AGENT" "REQ-ID" "AUTHORITY" "UPSTREAM-CLUSTER"
ENVOY_TEXT_PATTERN = re.compile(
    r'^\[(?P<start_time>[^\]]+)\]\s+'
    r'"(?P<method>[A-Z]+)\s+(?P<uri>\S+)(?:\s+(?P<protocol>[^"]+))?"\s+'
    r'(?P<response_code>\d{3})\s+'
    r'(?P<response_flags>\S+)\s+'
    r'(?P<bytes_received>\S+)\s+'
    r'(?P<bytes_sent>\S+)\s+'
    r'(?P<duration>\S+)\s+'
    r'(?P<upstream_service_time>\S+)\s+'
    r'"(?P<client_ip>[^"]*)"\s+'
    r'"(?P<user_agent>[^"]*)"'
    r'(?:\s+"(?P<request_id>[^"]*)")?'
    r'(?:\s+"(?P<authority>[^"]*)")?'
    r'(?:\s+"(?P<upstream_cluster>[^"]*)")?'
)


class EnvoyParser(BaseLogParser):
    source_type = LogSource.ENVOY

    def can_parse(self, sample_line: str) -> bool:
        line = sample_line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                data = json.loads(line)
                return "response_flags" in data or "upstream_cluster" in data or "upstream_service_time" in data
            except Exception:
                return False
        return bool(ENVOY_TEXT_PATTERN.match(line))

    def parse_line(self, line: str, gateway_id: str = "default-gw") -> ApiEvent:
        line_clean = line.strip()
        if line_clean.startswith("{") and line_clean.endswith("}"):
            return self._parse_json(line_clean, gateway_id)
        return self._parse_text(line_clean, gateway_id)

    def _parse_json(self, line: str, gateway_id: str) -> ApiEvent:
        data = json.loads(line)

        timestamp = parse_timestamp_flexible(
            data.get("start_time") or data.get("timestamp") or data.get("@timestamp")
        )

        method = data.get("method") or "GET"
        raw_uri = data.get("path") or data.get("uri") or "/"
        path, raw_path, query_params = parse_uri_parts(raw_uri)

        status_code = int(data.get("response_code") or data.get("status") or 200)

        # Duration is reported in milliseconds in Envoy JSON
        duration_raw = data.get("duration") or data.get("latency_ms") or 0.0
        try:
            latency_ms = float(duration_raw)
        except (ValueError, TypeError):
            latency_ms = 0.0

        client_ip = (
            data.get("x_forwarded_for")
            or data.get("downstream_remote_address")
            or data.get("client_ip")
            or "127.0.0.1"
        )
        user_agent = str(data.get("user_agent") or "unknown")

        bytes_in = int(data.get("bytes_received") or 0)
        bytes_out = int(data.get("bytes_sent") or 0)

        raw_headers = data.get("headers") or {}
        headers_summary = sanitize_headers(raw_headers)
        auth_type, auth_id = extract_auth_info(raw_headers)

        metadata = {
            "response_flags": data.get("response_flags"),
            "upstream_cluster": data.get("upstream_cluster"),
            "upstream_host": data.get("upstream_host"),
            "upstream_service_time_ms": data.get("upstream_service_time"),
            "authority": data.get("authority"),
            "protocol": data.get("protocol"),
            "envoy_request_id": data.get("request_id"),
        }

        return ApiEvent(
            timestamp=timestamp,
            source_type=self.source_type,
            gateway_id=gateway_id,
            http_method=method,
            path=path,
            raw_path=raw_path,
            query_params=query_params,
            status_code=status_code,
            latency_ms=latency_ms,
            client_ip=client_ip,
            user_agent=user_agent,
            auth_type=auth_type,
            auth_identity=auth_id,
            request_size_bytes=bytes_in,
            response_size_bytes=bytes_out,
            headers_summary=headers_summary,
            raw_log=line,
            metadata=metadata,
        )

    def _parse_text(self, line: str, gateway_id: str) -> ApiEvent:
        match = ENVOY_TEXT_PATTERN.match(line)
        if not match:
            raise ValueError(f"Line does not match Envoy text log format: {line[:100]}")

        groups = match.groupdict()
        timestamp = parse_timestamp_flexible(groups["start_time"])
        method = groups.get("method") or "GET"
        raw_uri = groups.get("uri") or "/"
        path, raw_path, query_params = parse_uri_parts(raw_uri)
        status_code = int(groups["response_code"])

        try:
            latency_ms = float(groups.get("duration") or 0.0)
        except ValueError:
            latency_ms = 0.0

        bytes_in = int(groups["bytes_received"]) if groups.get("bytes_received", "-") != "-" else 0
        bytes_out = int(groups["bytes_sent"]) if groups.get("bytes_sent", "-") != "-" else 0

        client_ip = groups.get("client_ip") or "127.0.0.1"
        user_agent = groups.get("user_agent") or "unknown"

        metadata = {
            "response_flags": groups.get("response_flags"),
            "upstream_cluster": groups.get("upstream_cluster"),
            "authority": groups.get("authority"),
            "protocol": groups.get("protocol"),
            "envoy_request_id": groups.get("request_id"),
        }

        return ApiEvent(
            timestamp=timestamp,
            source_type=self.source_type,
            gateway_id=gateway_id,
            http_method=method,
            path=path,
            raw_path=raw_path,
            query_params=query_params,
            status_code=status_code,
            latency_ms=latency_ms,
            client_ip=client_ip,
            user_agent=user_agent,
            auth_type=AuthType.NONE,
            request_size_bytes=bytes_in,
            response_size_bytes=bytes_out,
            headers_summary={"user-agent": user_agent},
            raw_log=line,
            metadata=metadata,
        )
