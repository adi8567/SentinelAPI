"""Unit Tests for API Gateway Log Parsers."""

import pytest
from backend.app.schemas.events import AuthType, LogSource
from backend.app.services.ingestion.auto_detector import parser_registry
from backend.app.services.ingestion.aws_gw_parser import AwsApiGwParser
from backend.app.services.ingestion.azure_apim_parser import AzureApimParser
from backend.app.services.ingestion.envoy_parser import EnvoyParser
from backend.app.services.ingestion.gcp_endpoints_parser import GcpEndpointsParser
from backend.app.services.ingestion.kong_parser import KongParser
from backend.app.services.ingestion.nginx_parser import NginxParser
from backend.app.services.ingestion.otel_parser import OtelTraceParser


def test_nginx_parser_combined_format():
    line = '198.51.100.42 - - [25/Oct/2026:10:00:01 +0000] "GET /api/v1/health HTTP/1.1" 200 48 "-" "kube-probe/1.28"'
    parser = NginxParser()
    assert parser.can_parse(line)

    event = parser.parse_line(line)
    assert event.source_type == LogSource.NGINX
    assert event.http_method == "GET"
    assert event.path == "/api/v1/health"
    assert event.status_code == 200
    assert event.client_ip == "198.51.100.42"
    assert event.response_size_bytes == 48


def test_nginx_parser_extended_format():
    line = '203.0.113.15 - - [25/Oct/2026:10:00:05 +0000] "POST /api/v1/auth/login HTTP/1.1" 200 642 "-" "Mozilla/5.0" 0.085 0.082 340'
    parser = NginxParser()
    event = parser.parse_line(line)
    assert event.http_method == "POST"
    assert event.path == "/api/v1/auth/login"
    assert event.latency_ms == pytest.approx(85.0, 0.1)
    assert event.request_size_bytes == 340
    assert event.response_size_bytes == 642


def test_envoy_parser_json():
    line = '{"start_time": "2026-10-25T10:05:00.100Z", "method": "GET", "path": "/api/v1/inventory/items?cat=electronics", "protocol": "HTTP/2", "response_code": 200, "response_flags": "-", "bytes_received": 145, "bytes_sent": 4210, "duration": 22.4, "upstream_service_time": 20.1, "x_forwarded_for": "198.51.100.55", "upstream_cluster": "inventory_service"}'
    parser = EnvoyParser()
    assert parser.can_parse(line)

    event = parser.parse_line(line)
    assert event.source_type == LogSource.ENVOY
    assert event.http_method == "GET"
    assert event.path == "/api/v1/inventory/items"
    assert event.query_params.get("cat") == "electronics"
    assert event.status_code == 200
    assert event.latency_ms == 22.4
    assert event.client_ip == "198.51.100.55"
    assert event.metadata.get("upstream_cluster") == "inventory_service"


def test_kong_parser_json():
    line = '{"latencies": {"request": 34.5, "kong": 2.1, "proxy": 32.4}, "service": {"name": "account-service"}, "route": {"id": "r-1"}, "request": {"method": "GET", "uri": "/api/v1/accounts/123", "size": 185, "headers": {"host": "api.sentinel.io", "authorization": "Bearer eyJhbGciOi..."}}, "response": {"status": 200, "size": 640}, "client_ip": "198.51.100.22"}'
    parser = KongParser()
    assert parser.can_parse(line)

    event = parser.parse_line(line)
    assert event.source_type == LogSource.KONG
    assert event.http_method == "GET"
    assert event.path == "/api/v1/accounts/123"
    assert event.status_code == 200
    assert event.latency_ms == 34.5
    assert event.auth_type == AuthType.BEARER
    assert event.auth_identity.startswith("sha256:")


def test_aws_gw_parser():
    line = '{"requestId": "req-991", "ip": "203.0.113.19", "requestTimeEpoch": 1761473400000, "httpMethod": "GET", "resourcePath": "/subscriptions/sub-12", "status": "200", "responseLength": "1420", "responseLatency": 38, "userAgent": "aws-sdk-js", "authorizer": {"principalId": "cognito_user_1"}}'
    parser = AwsApiGwParser()
    assert parser.can_parse(line)

    event = parser.parse_line(line)
    assert event.source_type == LogSource.AWS_APIGW
    assert event.http_method == "GET"
    assert event.path == "/subscriptions/sub-12"
    assert event.status_code == 200
    assert event.latency_ms == 38.0
    assert event.auth_identity == "cognito_user_1"


def test_azure_apim_parser():
    line = '{"time": "2026-10-25T10:15:00.000Z", "operationName": "Microsoft.ApiManagement/GatewayLogs", "properties": {"apiId": "cust-api", "operationId": "get-cust", "method": "GET", "url": "https://api.net/customers/c_1", "responseCode": 200, "responseSize": 2400, "durationMs": 35.4, "clientIp": "198.51.100.11", "userId": "usr-1"}}'
    parser = AzureApimParser()
    assert parser.can_parse(line)

    event = parser.parse_line(line)
    assert event.source_type == LogSource.AZURE_APIM
    assert event.http_method == "GET"
    assert event.path == "/customers/c_1"
    assert event.status_code == 200
    assert event.latency_ms == 35.4
    assert event.auth_identity == "usr-1"


def test_gcp_endpoints_parser():
    line = '{"httpRequest": {"requestMethod": "GET", "requestUrl": "https://esp.endpoints.cloud.goog/v1/locations", "status": 200, "responseSize": "3120", "latency": "0.038s", "userAgent": "gcloud", "remoteIp": "198.51.100.90"}, "resource": {"labels": {"service": "my-service"}}}'
    parser = GcpEndpointsParser()
    assert parser.can_parse(line)

    event = parser.parse_line(line)
    assert event.source_type == LogSource.GCP_ENDPOINTS
    assert event.http_method == "GET"
    assert event.path == "/v1/locations"
    assert event.status_code == 200
    assert event.latency_ms == 38.0
    assert event.client_ip == "198.51.100.90"


def test_otel_trace_parser():
    line = '{"trace_id": "4bf92f3577b34da6", "span_id": "00f067aa0b", "name": "GET /api/v1/customers", "start_time_unix_nano": 1761474000000000000, "end_time_unix_nano": 1761474000028000000, "attributes": {"http.request.method": "GET", "url.path": "/api/v1/customers", "http.response.status_code": 200, "client.address": "198.51.100.44"}}'
    parser = OtelTraceParser()
    assert parser.can_parse(line)

    event = parser.parse_line(line)
    assert event.source_type == LogSource.OPENTELEMETRY
    assert event.http_method == "GET"
    assert event.path == "/api/v1/customers"
    assert event.status_code == 200
    assert event.latency_ms == 28.0
    assert event.client_ip == "198.51.100.44"


def test_parser_registry_auto_detection():
    nginx_sample = '198.51.100.42 - - [25/Oct/2026:10:00:01 +0000] "GET /api/v1/test HTTP/1.1" 200 100'
    kong_sample = '{"latencies": {"request": 10}, "service": {"name": "s1"}}'
    aws_sample = '{"requestId": "r1", "httpMethod": "POST", "resourcePath": "/test"}'

    assert isinstance(parser_registry.detect_parser(nginx_sample), NginxParser)
    assert isinstance(parser_registry.detect_parser(kong_sample), KongParser)
    assert isinstance(parser_registry.detect_parser(aws_sample), AwsApiGwParser)
