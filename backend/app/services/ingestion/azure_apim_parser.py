"""Azure API Management (APIM) Log Parser.

Parses Azure Monitor / Log Analytics / Event Hub export logs for Azure APIM.
"""

import json
from typing import Any, Dict
from backend.app.schemas.events import ApiEvent, AuthType, LogSource
from backend.app.services.ingestion.base import (
    BaseLogParser,
    parse_timestamp_flexible,
    parse_uri_parts,
)


class AzureApimParser(BaseLogParser):
    source_type = LogSource.AZURE_APIM

    def can_parse(self, sample_line: str) -> bool:
        line = sample_line.strip()
        if not (line.startswith("{") and line.endswith("}")):
            return False
        try:
            data = json.loads(line)
            if "operationName" in data and "ApiManagement" in data["operationName"]:
                return True
            if "properties" in data and ("serviceId" in data["properties"] or "operationId" in data["properties"]):
                return True
            if "serviceId" in data and ("operationId" in data or "requestUrl" in data):
                return True
            return False
        except Exception:
            return False

    def parse_line(self, line: str, gateway_id: str = "azure-apim") -> ApiEvent:
        data = json.loads(line)
        props = data.get("properties") if isinstance(data.get("properties"), dict) else data

        timestamp = parse_timestamp_flexible(
            data.get("time") or props.get("clientTime") or data.get("timestamp")
        )

        method = props.get("method") or props.get("requestMethod") or "GET"
        raw_url = props.get("url") or props.get("requestUrl") or "/"
        path, raw_path, query_params = parse_uri_parts(raw_url)

        status_code = int(props.get("responseCode") or props.get("statusCode") or 200)
        latency_ms = float(props.get("durationMs") or props.get("backendTime") or 0.0)

        client_ip = props.get("clientIp") or props.get("callerIpAddress") or "127.0.0.1"
        user_agent = str(props.get("userAgent") or "unknown")

        res_bytes = int(props.get("responseSize") or 0)
        req_bytes = int(props.get("requestSize") or 0)

        auth_id = props.get("userId") or props.get("subscriptionId")
        auth_type = AuthType.API_KEY if auth_id else AuthType.NONE

        metadata = {
            "azure_correlation_id": props.get("correlationId"),
            "api_id": props.get("apiId"),
            "operation_id": props.get("operationId"),
            "service_id": props.get("serviceId"),
            "backend_time_ms": props.get("backendTime"),
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
            request_size_bytes=req_bytes,
            response_size_bytes=res_bytes,
            headers_summary={"user-agent": user_agent},
            raw_log=line,
            metadata=metadata,
        )
