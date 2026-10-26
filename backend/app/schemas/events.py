"""SentinelAPI Normalized Event Schemas.

Defines the core standardized ApiEvent model representing any API interaction
ingested from NGINX, Envoy, Kong, AWS API GW, Azure APIM, GCP Endpoints,
OpenTelemetry traces, or public research datasets.
"""

from datetime import datetime, timezone
from enum import Enum
import ipaddress
from typing import Any, Dict, List, Optional, Union
import uuid
from pydantic import BaseModel, Field, field_validator


class LogSource(str, Enum):
    NGINX = "nginx"
    ENVOY = "envoy"
    KONG = "kong"
    AWS_APIGW = "aws_apigw"
    AZURE_APIM = "azure_apim"
    GCP_ENDPOINTS = "gcp_endpoints"
    OPENTELEMETRY = "opentelemetry"
    GENERIC_HTTP = "generic_http"
    PUBLIC_DATASET = "public_dataset"
    AUTO = "auto"


class AuthType(str, Enum):
    BEARER = "bearer"
    API_KEY = "api_key"
    BASIC = "basic"
    OAUTH2 = "oauth2"
    NONE = "none"
    UNKNOWN = "unknown"


class ApiEvent(BaseModel):
    """Standardized normalized API access event schema."""

    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique event UUID"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event UTC timestamp"
    )
    source_type: LogSource = Field(
        ...,
        description="Origin gateway or logging format"
    )
    gateway_id: str = Field(
        default="default-gw",
        description="Identifier of the gateway cluster or host"
    )
    http_method: str = Field(
        ...,
        description="HTTP method (e.g. GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD)"
    )
    path: str = Field(
        ...,
        description="Normalized request path without query parameters"
    )
    raw_path: str = Field(
        ...,
        description="Full request path including query parameters"
    )
    query_params: Dict[str, Union[str, List[str]]] = Field(
        default_factory=dict,
        description="Extracted key-value query parameters"
    )
    status_code: int = Field(
        ...,
        ge=100,
        le=599,
        description="HTTP response status code"
    )
    latency_ms: float = Field(
        ...,
        ge=0.0,
        description="End-to-end request latency in milliseconds"
    )
    client_ip: str = Field(
        ...,
        description="Client IPv4 or IPv6 address"
    )
    user_agent: str = Field(
        default="unknown",
        description="Client User-Agent header"
    )
    auth_type: AuthType = Field(
        default=AuthType.NONE,
        description="Detected authentication mechanism"
    )
    auth_identity: Optional[str] = Field(
        default=None,
        description="Sanitized non-sensitive identity identifier (e.g., token hash, subject, principal ID)"
    )
    request_size_bytes: int = Field(
        default=0,
        ge=0,
        description="Size of incoming request payload in bytes"
    )
    response_size_bytes: int = Field(
        default=0,
        ge=0,
        description="Size of returned response payload in bytes"
    )
    headers_summary: Dict[str, str] = Field(
        default_factory=dict,
        description="Sanitized dictionary of non-sensitive HTTP headers"
    )
    geo_country: Optional[str] = Field(
        default=None,
        description="Country code (ISO-3166 alpha-2) resolved from client IP"
    )
    is_tls: bool = Field(
        default=True,
        description="Whether request used TLS/HTTPS"
    )
    tls_version: Optional[str] = Field(
        default=None,
        description="TLS protocol version (e.g. TLSv1.3)"
    )
    raw_log: str = Field(
        default="",
        description="Verbatim original log line or raw JSON payload"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Gateway-specific attributes (route_id, service_id, upstream_cluster, trace_id, etc.)"
    )

    @field_validator("http_method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        v_upper = v.strip().upper()
        allowed = {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD", "CONNECT", "TRACE"}
        if v_upper not in allowed:
            # Handle non-standard or custom methods gracefully
            return v_upper if len(v_upper) <= 16 else "UNKNOWN"
        return v_upper

    @field_validator("path")
    @classmethod
    def normalize_path(cls, v: str) -> str:
        if not v:
            return "/"
        clean = v.split("?")[0].strip()
        if not clean.startswith("/"):
            clean = "/" + clean
        return clean

    @field_validator("client_ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        clean_ip = v.strip().split(",")[0].strip()  # Take leftmost IP if forwarded list
        # Remove IPv6 scope ID if present (e.g. %eth0)
        if "%" in clean_ip:
            clean_ip = clean_ip.split("%")[0]
        try:
            ipaddress.ip_address(clean_ip)
            return clean_ip
        except ValueError:
            # If standard IP validation fails, check if port is attached e.g. 1.2.3.4:5678
            if ":" in clean_ip and clean_ip.count(":") == 1:
                ip_part = clean_ip.split(":")[0]
                try:
                    ipaddress.ip_address(ip_part)
                    return ip_part
                except ValueError:
                    pass
            # Default fallback for unparseable raw IP strings
            return "127.0.0.1"


class RawLogRecord(BaseModel):
    """Container for an unparsed raw log line or payload."""
    line: str = Field(..., description="Verbatim raw log line or JSON string")
    source_type: Optional[LogSource] = Field(default=LogSource.AUTO)
    gateway_id: Optional[str] = Field(default=None)


class BatchRawLogRequest(BaseModel):
    """Batch ingestion request payload."""
    source_type: LogSource = Field(default=LogSource.AUTO)
    gateway_id: Optional[str] = Field(default="default-gw")
    logs: List[str] = Field(..., min_length=1, max_length=50000)


class BatchEventsRequest(BaseModel):
    """Direct batch ingestion of already-normalized ApiEvents."""
    events: List[ApiEvent] = Field(..., min_length=1, max_length=50000)


class ParseErrorDetail(BaseModel):
    index: int
    line_snippet: str
    error: str


class IngestionResult(BaseModel):
    """Summary response for an ingestion request."""
    success: bool
    total_received: int
    accepted_count: int
    rejected_count: int
    processing_time_ms: float
    source_detected: Optional[str] = None
    parse_errors: List[ParseErrorDetail] = Field(default_factory=list)
