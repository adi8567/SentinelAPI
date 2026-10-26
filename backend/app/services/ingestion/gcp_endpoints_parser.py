"""Google Cloud Endpoints / Cloud Logging Parser.

Parses Google Cloud Logging format logs containing an httpRequest object.
"""

import json
from typing import Any, Dict
from backend.app.schemas.events import ApiEvent, AuthType, LogSource
from backend.app.services.ingestion.base import (
    BaseLogParser,
    parse_timestamp_flexible,
    parse_uri_parts,
)


class GcpEndpointsParser(BaseLogParser):
    source_type = LogSource.GCP_ENDPOINTS

    def can_parse(self, sample_line: str) -> bool:
        line = sample_line.strip()
        if not (line.startswith("{") and line.endswith("}")):
            return False
        try:
            data = json.loads(line)
            return "httpRequest" in data or ("logName" in data and "endpoints" in data["logName"])
        except Exception:
            return False

    def parse_line(self, line: str, gateway_id: str = "gcp-endpoints") -> ApiEvent:
        data = json.loads(line)
        http_req = data.get("httpRequest", {})

        timestamp = parse_timestamp_flexible(
            data.get("timestamp") or data.get("receiveTimestamp")
        )

        method = http_req.get("requestMethod") or "GET"
        raw_url = http_req.get("requestUrl") or "/"
        path, raw_path, query_params = parse_uri_parts(raw_url)

        status_code = int(http_req.get("status") or 200)

        # GCP latency is often string with unit suffix e.g. "0.045s" or float seconds
        latency_str = str(http_req.get("latency", "0s"))
        if latency_str.endswith("s"):
            try:
                latency_ms = float(latency_str[:-1]) * 1000.0
            except ValueError:
                latency_ms = 0.0
        else:
            try:
                latency_ms = float(latency_str) * 1000.0 if float(latency_str) < 1000.0 else float(latency_str)
            except ValueError:
                latency_ms = 0.0

        client_ip = http_req.get("remoteIp") or "127.0.0.1"
        user_agent = str(http_req.get("userAgent") or "unknown")

        req_size = int(http_req.get("requestSize") or 0)
        res_size = int(http_req.get("responseSize") or 0)

        resource = data.get("resource", {})
        labels = resource.get("labels", {})

        metadata = {
            "gcp_insert_id": data.get("insertId"),
            "gcp_service": labels.get("service"),
            "gcp_method": labels.get("method"),
            "protocol": http_req.get("protocol"),
            "severity": data.get("severity"),
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
