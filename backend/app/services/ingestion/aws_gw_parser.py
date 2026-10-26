"""AWS API Gateway & CloudWatch Log Parser.

Parses AWS API Gateway structured CloudWatch JSON access logs.
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


class AwsApiGwParser(BaseLogParser):
    source_type = LogSource.AWS_APIGW

    def can_parse(self, sample_line: str) -> bool:
        line = sample_line.strip()
        if not (line.startswith("{") and line.endswith("}")):
            return False
        try:
            data = json.loads(line)
            return (
                "requestId" in data
                and ("httpMethod" in data or "resourcePath" in data or "responseLatency" in data)
            )
        except Exception:
            return False

    def parse_line(self, line: str, gateway_id: str = "aws-apigw") -> ApiEvent:
        data = json.loads(line)

        timestamp = parse_timestamp_flexible(
            data.get("requestTimeEpoch") or data.get("requestTime") or data.get("timestamp")
        )

        method = data.get("httpMethod") or "GET"
        raw_uri = data.get("path") or data.get("resourcePath") or "/"
        path, raw_path, query_params = parse_uri_parts(raw_uri)

        status_code = int(data.get("status") or 200)

        # AWS responseLatency is in milliseconds
        latency_ms = float(data.get("responseLatency") or data.get("integrationLatency") or 0.0)

        client_ip = (
            data.get("ip")
            or data.get("sourceIp")
            or (data.get("identity", {}).get("sourceIp") if isinstance(data.get("identity"), dict) else None)
            or "127.0.0.1"
        )

        user_agent = (
            data.get("userAgent")
            or (data.get("identity", {}).get("userAgent") if isinstance(data.get("identity"), dict) else None)
            or "unknown"
        )

        res_bytes = int(data.get("responseLength") or 0)
        req_bytes = int(data.get("requestLength") or 0)

        # Principal from Cognito / Lambda authorizer
        auth_id = None
        auth_type = AuthType.NONE
        if "authorizer" in data and isinstance(data["authorizer"], dict):
            auth_id = data["authorizer"].get("principalId") or data["authorizer"].get("claims", {}).get("sub")
            if auth_id:
                auth_type = AuthType.BEARER
        elif "identity" in data and isinstance(data["identity"], dict):
            auth_id = data["identity"].get("userArn") or data["identity"].get("cognitoIdentityId")
            if auth_id:
                auth_type = AuthType.BEARER

        metadata = {
            "aws_request_id": data.get("requestId"),
            "stage": data.get("stage"),
            "integration_latency_ms": data.get("integrationLatency"),
            "api_id": data.get("apiId"),
            "protocol": data.get("protocol"),
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
