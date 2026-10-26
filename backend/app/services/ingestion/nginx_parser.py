"""NGINX Access Log Parser.

Parses NGINX Combined Log format, Extended/Performance log format (with latency
and upstream times), and NGINX structured JSON logs.
"""

import json
import re
from typing import Any, Dict, Optional
from backend.app.schemas.events import ApiEvent, AuthType, LogSource
from backend.app.services.ingestion.base import (
    BaseLogParser,
    extract_auth_info,
    parse_timestamp_flexible,
    parse_uri_parts,
    sanitize_headers,
)

# Standard NGINX Combined / Extended Regex
# Captures: ip, ident, user, time, request (method uri proto), status, bytes_sent, referer, user_agent, [request_time, upstream_time, req_length]
NGINX_COMBINED_PATTERN = re.compile(
    r'^(?P<ip>\S+)\s+'
    r'(?P<ident>\S+)\s+'
    r'(?P<user>\S+)\s+'
    r'\[(?P<time>[^\]]+)\]\s+'
    r'"(?P<method>[A-Z]+)\s+(?P<uri>\S+)(?:\s+(?P<proto>[^"]+))?"\s+'
    r'(?P<status>\d{3})\s+'
    r'(?P<bytes>\S+)'
    r'(?:\s+"(?P<referer>[^"]*)")?'
    r'(?:\s+"(?P<user_agent>[^"]*)")?'
    r'(?:\s+(?P<request_time>\d+\.?\d*|-))?'
    r'(?:\s+(?P<upstream_time>\d+\.?\d*|-))?'
    r'(?:\s+(?P<request_length>\d+|-))?'
)


class NginxParser(BaseLogParser):
    source_type = LogSource.NGINX

    def can_parse(self, sample_line: str) -> bool:
        line = sample_line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                data = json.loads(line)
                return "remote_addr" in data or "request" in data or "time_local" in data
            except Exception:
                return False
        return bool(NGINX_COMBINED_PATTERN.match(line))

    def parse_line(self, line: str, gateway_id: str = "default-gw") -> ApiEvent:
        line_clean = line.strip()
        if line_clean.startswith("{") and line_clean.endswith("}"):
            return self._parse_json(line_clean, gateway_id)
        return self._parse_text(line_clean, gateway_id)

    def _parse_text(self, line: str, gateway_id: str) -> ApiEvent:
        match = NGINX_COMBINED_PATTERN.match(line)
        if not match:
            raise ValueError(f"Line does not match NGINX log format: {line[:100]}")

        groups = match.groupdict()
        method = groups.get("method") or "GET"
        raw_uri = groups.get("uri") or "/"
        path, raw_path, query_params = parse_uri_parts(raw_uri)
        status_code = int(groups["status"])

        # Latency in ms (Nginx request_time is in seconds)
        req_time_str = groups.get("request_time")
        latency_ms = 0.0
        if req_time_str and req_time_str != "-":
            try:
                latency_ms = float(req_time_str) * 1000.0
            except ValueError:
                latency_ms = 0.0

        # Body bytes sent
        bytes_sent = 0
        raw_bytes = groups.get("bytes")
        if raw_bytes and raw_bytes != "-":
            try:
                bytes_sent = int(raw_bytes)
            except ValueError:
                bytes_sent = 0

        # Request length
        req_length = 0
        raw_req_len = groups.get("request_length")
        if raw_req_len and raw_req_len != "-":
            try:
                req_length = int(raw_req_len)
            except ValueError:
                req_length = 0

        timestamp = parse_timestamp_flexible(groups["time"])
        client_ip = groups["ip"]
        user_agent = groups.get("user_agent") or "unknown"

        metadata = {}
        if groups.get("upstream_time") and groups["upstream_time"] != "-":
            try:
                metadata["upstream_response_time_ms"] = float(groups["upstream_time"]) * 1000.0
            except ValueError:
                pass
        if groups.get("referer") and groups["referer"] != "-":
            metadata["referer"] = groups["referer"]

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
            request_size_bytes=req_length,
            response_size_bytes=bytes_sent,
            headers_summary={"user-agent": user_agent},
            raw_log=line,
            metadata=metadata,
        )

    def _parse_json(self, line: str, gateway_id: str) -> ApiEvent:
        data = json.loads(line)
        timestamp = parse_timestamp_flexible(
            data.get("time_local") or data.get("time") or data.get("@timestamp")
        )

        request_str = data.get("request", "")
        if " " in request_str:
            parts = request_str.split()
            method = parts[0]
            raw_uri = parts[1] if len(parts) > 1 else "/"
        else:
            method = data.get("request_method") or data.get("method") or "GET"
            raw_uri = data.get("request_uri") or data.get("uri") or "/"

        path, raw_path, query_params = parse_uri_parts(raw_uri)
        status_code = int(data.get("status") or data.get("status_code", 200))

        # Latency
        req_time = data.get("request_time") or data.get("response_time", 0.0)
        try:
            latency_ms = float(req_time) * 1000.0 if float(req_time) < 1000.0 else float(req_time)
        except (ValueError, TypeError):
            latency_ms = 0.0

        client_ip = str(data.get("remote_addr") or data.get("client_ip") or "127.0.0.1")
        user_agent = str(data.get("http_user_agent") or data.get("user_agent") or "unknown")

        req_bytes = int(data.get("request_length") or data.get("bytes_received") or 0)
        res_bytes = int(data.get("body_bytes_sent") or data.get("bytes_sent") or 0)

        # Headers if present
        raw_headers = data.get("headers") or {}
        headers_summary = sanitize_headers(raw_headers)
        auth_type, auth_id = extract_auth_info(raw_headers)

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
            request_size_bytes=req_bytes,
            response_size_bytes=res_bytes,
            headers_summary=headers_summary,
            raw_log=line,
            metadata={"upstream": data.get("upstream_addr"), "protocol": data.get("server_protocol")},
        )
