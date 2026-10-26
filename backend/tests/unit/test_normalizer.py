"""Unit Tests for Schema Validation and Normalization."""

import pytest
from backend.app.schemas.events import ApiEvent, AuthType, LogSource
from backend.app.services.ingestion.base import (
    extract_auth_info,
    parse_timestamp_flexible,
    parse_uri_parts,
    sanitize_headers,
)


def test_api_event_ip_normalization():
    # Forwarded IP list: extract leftmost
    event1 = ApiEvent(
        source_type=LogSource.GENERIC_HTTP,
        http_method="GET",
        path="/items",
        raw_path="/items",
        status_code=200,
        latency_ms=10.0,
        client_ip="203.0.113.195, 10.0.0.1",
    )
    assert event1.client_ip == "203.0.113.195"

    # IP with port: strip port
    event2 = ApiEvent(
        source_type=LogSource.GENERIC_HTTP,
        http_method="GET",
        path="/items",
        raw_path="/items",
        status_code=200,
        latency_ms=10.0,
        client_ip="198.51.100.22:54321",
    )
    assert event2.client_ip == "198.51.100.22"


def test_api_event_path_normalization():
    event = ApiEvent(
        source_type=LogSource.GENERIC_HTTP,
        http_method="get",
        path="api/v1/users?admin=true",
        raw_path="/api/v1/users?admin=true",
        status_code=200,
        latency_ms=15.0,
        client_ip="127.0.0.1",
    )
    assert event.http_method == "GET"
    assert event.path == "/api/v1/users"


def test_header_sanitization():
    headers = {
        "Authorization": "Bearer secret_token_xyz_12345",
        "Cookie": "session_id=s3cr3t; tracking=abc",
        "X-Api-Key": "key_production_secret",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    sanitized = sanitize_headers(headers)
    assert sanitized["authorization"] == "[REDACTED]"
    assert sanitized["cookie"] == "[REDACTED]"
    assert sanitized["x-api-key"] == "[REDACTED]"
    assert sanitized["content-type"] == "application/json"
    assert sanitized["user-agent"] == "Mozilla/5.0"


def test_extract_auth_info_bearer():
    headers = {"Authorization": "Bearer secret_user_token"}
    auth_type, fingerprint = extract_auth_info(headers)
    assert auth_type == AuthType.BEARER
    assert fingerprint.startswith("sha256:")
    assert len(fingerprint) > 10


def test_extract_auth_info_api_key():
    headers = {"X-API-Key": "my-secret-api-key"}
    auth_type, fingerprint = extract_auth_info(headers)
    assert auth_type == AuthType.API_KEY
    assert fingerprint.startswith("key:")


def test_parse_uri_parts():
    path, raw_path, query_params = parse_uri_parts("/api/v1/products?cat=electronics&limit=10&tag=sale&tag=new")
    assert path == "/api/v1/products"
    assert query_params["cat"] == "electronics"
    assert query_params["limit"] == "10"
    assert isinstance(query_params["tag"], list)
    assert len(query_params["tag"]) == 2
