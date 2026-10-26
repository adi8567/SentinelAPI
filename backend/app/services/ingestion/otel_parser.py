"""OpenTelemetry Traces & Spans Parser.

Parses OTel Server Span JSON records emitted by OpenTelemetry collectors or agents.
"""

import json
from typing import Any, Dict
from backend.app.schemas.events import ApiEvent, AuthType, LogSource
from backend.app.services.ingestion.base import (
    BaseLogParser,
    parse_timestamp_flexible,
    parse_uri_parts,
)


class OtelTraceParser(BaseLogParser):
    source_type = LogSource.OPENTELEMETRY

    def can_parse(self, sample_line: str) -> bool:
        line = sample_line.strip()
        if not (line.startswith("{") and line.endswith("}")):
            return False
        try:
            data = json.loads(line)
            return (
                ("trace_id" in data or "traceId" in data)
                and ("span_id" in data or "spanId" in data or "attributes" in data)
            )
        except Exception:
            return False

    def parse_line(self, line: str, gateway_id: str = "otel-collector") -> ApiEvent:
        data = json.loads(line)
        attrs = data.get("attributes") or {}

        # Timestamp from start_time_unix_nano
        start_nano = data.get("start_time_unix_nano") or data.get("startTimeUnixNano")
        if start_nano:
            timestamp = parse_timestamp_flexible(int(start_nano) / 1e9)
        else:
            timestamp = parse_timestamp_flexible(data.get("timestamp") or data.get("time"))

        # Latency calculated from end - start nano or duration_ms
        latency_ms = 0.0
        end_nano = data.get("end_time_unix_nano") or data.get("endTimeUnixNano")
        if start_nano and end_nano:
            latency_ms = (int(end_nano) - int(start_nano)) / 1e6  # ns to ms
        elif "duration_ms" in data:
            latency_ms = float(data["duration_ms"])

        method = (
            attrs.get("http.request.method")
            or attrs.get("http.method")
            or (data.get("name", "").split()[0] if " " in data.get("name", "") else "GET")
        )

        raw_uri = (
            attrs.get("http.target")
            or attrs.get("url.path")
            or attrs.get("http.route")
            or (data.get("name", "").split()[1] if " " in data.get("name", "") else "/")
        )
        path, raw_path, query_params = parse_uri_parts(raw_uri)

        status_code = int(
            attrs.get("http.response.status_code")
            or attrs.get("http.status_code")
            or 200
        )

        client_ip = (
            attrs.get("http.client_ip")
            or attrs.get("client.address")
            or attrs.get("net.peer.ip")
            or attrs.get("network.peer.address")
            or "127.0.0.1"
        )

        user_agent = str(
            attrs.get("user_agent.original")
            or attrs.get("http.user_agent")
            or "unknown"
        )

        req_size = int(attrs.get("http.request.header.content-length") or attrs.get("http.request_content_length") or 0)
        res_size = int(attrs.get("http.response.header.content-length") or attrs.get("http.response_content_length") or 0)

        metadata = {
            "trace_id": data.get("trace_id") or data.get("traceId"),
            "span_id": data.get("span_id") or data.get("spanId"),
            "span_name": data.get("name"),
            "http_route": attrs.get("http.route"),
            "service_name": attrs.get("service.name") or data.get("resource", {}).get("service.name"),
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
            request_size_bytes=req_size,
            response_size_bytes=res_size,
            headers_summary={"user-agent": user_agent},
            raw_log=line,
            metadata=metadata,
        )
