"""SentinelAPI Prometheus Metrics & Telemetry Exporter.

Exposes high-resolution production metrics across HTTP traffic, ingestion rates,
detection engine inferences, and adaptive policy enforcement.
"""

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# Custom isolated registry to avoid collisions
REGISTRY = CollectorRegistry(auto_describe=True)

# 1. HTTP Traffic Metrics
HTTP_REQUESTS_TOTAL = Counter(
    "sentinel_http_requests_total",
    "Total HTTP requests handled by SentinelAPI service",
    ["method", "endpoint", "status_code"],
    registry=REGISTRY,
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "sentinel_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=REGISTRY,
)

# 2. Ingestion Pipeline Metrics
EVENTS_INGESTED_TOTAL = Counter(
    "sentinel_events_ingested_total",
    "Total real API interaction events ingested into the analytical pipeline",
    ["source_type"],
    registry=REGISTRY,
)

INGESTION_PARSE_ERRORS_TOTAL = Counter(
    "sentinel_ingestion_parse_errors_total",
    "Total log lines that failed parsing",
    ["source_type"],
    registry=REGISTRY,
)

# 3. Anomaly Detection Engine Metrics
ANOMALIES_DETECTED_TOTAL = Counter(
    "sentinel_anomalies_detected_total",
    "Total behavioral anomalies detected by the ensemble engine",
    ["severity", "primary_detector"],
    registry=REGISTRY,
)

ANOMALY_RISK_SCORE = Histogram(
    "sentinel_anomaly_risk_score",
    "Distribution of calculated composite risk scores (0-100)",
    buckets=(10.0, 25.0, 40.0, 50.0, 60.0, 75.0, 85.0, 95.0, 100.0),
    registry=REGISTRY,
)

DETECTOR_INFERENCE_SECONDS = Histogram(
    "sentinel_detector_inference_seconds",
    "Ensemble detector inference latency in seconds",
    ["detector"],
    buckets=(0.0001, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.05),
    registry=REGISTRY,
)

# 4. Adaptive Policy Enforcement Metrics
POLICY_ACTIONS_TOTAL = Counter(
    "sentinel_policy_actions_total",
    "Total adaptive defense actions executed against traffic",
    ["action", "policy_id"],
    registry=REGISTRY,
)

ACTIVE_IP_BANS = Gauge(
    "sentinel_active_ip_bans",
    "Current number of active IP blocks enforced",
    registry=REGISTRY,
)

ACTIVE_QUARANTINES = Gauge(
    "sentinel_active_quarantines",
    "Current number of quarantined client identities",
    registry=REGISTRY,
)

# 5. Streaming & WebSocket Telemetry
ACTIVE_WS_CONNECTIONS = Gauge(
    "sentinel_active_ws_connections",
    "Current number of live connected WebSocket clients",
    registry=REGISTRY,
)


def export_metrics() -> bytes:
    """Renders all Prometheus metrics in standard exposition text format."""
    return generate_latest(REGISTRY)
