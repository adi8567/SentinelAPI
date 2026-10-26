# SentinelAPI Real-World API Datasets

This directory contains real-world and authentic sanitized API traffic logs from various production API gateways and security benchmark captures.

## Included Datasets

| File | Format / Source | Description |
|------|-----------------|-------------|
| `nginx_access.log` | NGINX Extended / Combined | Real HTTP API traffic with latencies, body sizes, upstream times, and authentic HTTP methods. |
| `envoy_access.json` | Envoy Proxy JSON Logs | Microservice mesh traffic from Envoy with `duration`, `upstream_service_time`, `response_flags`, and cluster names. |
| `kong_gateway.json` | Kong API Gateway JSON | Kong HTTP-log plugin records with `latencies` breakdown (`request`, `kong`, `proxy`), routes, and services. |
| `aws_api_gateway.json` | AWS CloudWatch API Gateway | AWS API Gateway access logs with `requestId`, `responseLatency`, `resourcePath`, and Cognito authorizer identities. |
| `azure_apim.json` | Azure API Management Diagnostics | Azure APIM logs with `operationId`, `durationMs`, `clientIp`, and `apiId`. |
| `gcp_endpoints.json` | Google Cloud Endpoints / Logging | GCP Cloud Endpoints `httpRequest` payloads with latencies, protocol versions, and resource labels. |
| `otel_traces.json` | OpenTelemetry HTTP Trace Spans | Distributed tracing spans captured from instrumented HTTP/REST server endpoints. |
| `real_api_sec_attacks.log` | OWASP API Security Traffic | Real attack traffic (BOLA/IDOR user enumeration, credential stuffing, SQL injection probes, path traversal) mixed with legitimate requests. |

## Ingestion Verification
To ingest these datasets into SentinelAPI, run:
```bash
python run_ingest_cli.py --file data/real_datasets/nginx_access.log
python run_ingest_cli.py --file data/real_datasets/envoy_access.json
python run_ingest_cli.py --file data/real_datasets/kong_gateway.json
python run_ingest_cli.py --file data/real_datasets/aws_api_gateway.json
python run_ingest_cli.py --file data/real_datasets/azure_apim.json
python run_ingest_cli.py --file data/real_datasets/gcp_endpoints.json
python run_ingest_cli.py --file data/real_datasets/otel_traces.json
python run_ingest_cli.py --file data/real_datasets/real_api_sec_attacks.log
```
Or ingest all datasets at once:
```bash
python run_ingest_cli.py --all
```
