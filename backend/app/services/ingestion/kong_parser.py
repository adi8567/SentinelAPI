"""Kong API Gateway Log Parser.

Parses Kong Gateway standard HTTP/File log plugin JSON records.
"""

import json
from typing import Any, Dict
from backend.app.schemas.events import ApiEvent, AuthType, LogSource
from backend.app.services.ingestion.base import (
    BaseLogParser,
    extract_auth_info,
    parse_timestamp_flexible,
    parse_uri_parts,
    sanitize_headers,
)


class KongParser(BaseLogParser):
    source_type = LogSource.KONG

    def can_parse(self, sample_line: str) -> bool:
        line = sample_line.strip()
        if not (line.startswith("{") and line.endswith("}")):
            return False
        try:
            data = json.loads(line)
            return "latencies" in data and ("service" in data or "route" in data)
        except Exception:
            return False

    def parse_line(self, line: str, gateway_id: str = "default-gw") -> ApiEvent:
        data = json.loads(line)

        # Kong started_at is usually epoch milliseconds
        timestamp = parse_timestamp_flexible(
            data.get("started_at") or data.get("timestamp")
        )

        req_info = data.get("request", {})
        res_info = data.get("response", {})
        latencies = data.get("latencies", {})

        method = req_info.get("method") or "GET"
        raw_uri = req_info.get("uri") or req_info.get("url") or "/"
        path, raw_path, query_params = parse_uri_parts(raw_uri)

        # Merge querystring dict if provided explicitly by Kong
        if "querystring" in req_info and isinstance(req_info["querystring"], dict):
            query_params.update(req_info["querystring"])

        status_code = int(res_info.get("status") or 200)
        latency_ms = float(latencies.get("request") or 0.0)

        client_ip = (
            data.get("client_ip")
            or req_info.get("headers", {}).get("x-forwarded-for")
            or "127.0.0.1"
        )

        raw_headers = req_info.get("headers") or {}
        headers_summary = sanitize_headers(raw_headers)
        auth_type, auth_id = extract_auth_info(raw_headers)

        # Kong authenticated entity fallback
        if not auth_id and "authenticated_entity" in data and isinstance(data["authenticated_entity"], dict):
            consumer_id = data["authenticated_entity"].get("id")
            if consumer_id:
                auth_id = f"kong_consumer:{consumer_id}"
                auth_type = AuthType.API_KEY

        user_agent = str(raw_headers.get("user-agent") or "unknown")
        req_size = int(req_info.get("size") or 0)
        res_size = int(res_info.get("size") or 0)

        service_data = data.get("service") or {}
        route_data = data.get("route") or {}

        metadata = {
            "service_id": service_data.get("id"),
            "service_name": service_data.get("name"),
            "route_id": route_data.get("id"),
            "proxy_latency_ms": latencies.get("proxy"),
            "kong_gateway_latency_ms": latencies.get("kong"),
            "consumer_id": data.get("consumer", {}).get("id") if isinstance(data.get("consumer"), dict) else None,
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
            request_size_bytes=req_size,
            response_size_bytes=res_size,
            headers_summary=headers_summary,
            raw_log=line,
            metadata=metadata,
        )
