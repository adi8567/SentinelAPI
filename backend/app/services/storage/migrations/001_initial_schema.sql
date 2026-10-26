-- ClickHouse DDL for SentinelAPI Time-Series Event Store

CREATE DATABASE IF NOT EXISTS sentinelapi;

-- 1. Raw Audit Events
CREATE TABLE IF NOT EXISTS sentinelapi.raw_events (
    id UUID,
    received_at DateTime64(3, 'UTC') DEFAULT now64(3),
    source_type LowCardinality(String),
    gateway_id LowCardinality(String),
    raw_log String
) ENGINE = MergeTree()
ORDER BY (received_at, gateway_id, id)
TTL received_at + INTERVAL 30 DAY;

-- 2. Standardized Normalized API Events
CREATE TABLE IF NOT EXISTS sentinelapi.api_events (
    event_id UUID,
    timestamp DateTime64(3, 'UTC'),
    source_type LowCardinality(String),
    gateway_id LowCardinality(String),
    http_method LowCardinality(String),
    path String,
    raw_path String,
    query_params String,          -- JSON string
    status_code UInt16,
    latency_ms Float64,
    client_ip String,
    user_agent String,
    auth_type LowCardinality(String),
    auth_identity Nullable(String),
    request_size_bytes UInt64,
    response_size_bytes UInt64,
    headers_summary String,       -- JSON string
    geo_country LowCardinality(Nullable(String)),
    is_tls UInt8,
    tls_version LowCardinality(Nullable(String)),
    raw_log String,
    metadata String               -- JSON string
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, http_method, status_code, path, event_id)
TTL timestamp + INTERVAL 90 DAY;

-- Materialized View for Real-time Aggregated Metrics
CREATE TABLE IF NOT EXISTS sentinelapi.api_metrics_hourly (
    window_hour DateTime,
    path String,
    http_method LowCardinality(String),
    status_group UInt16,
    request_count UInt64,
    avg_latency_ms Float64,
    max_latency_ms Float64,
    p95_latency_ms Float64,
    total_bytes_in UInt64,
    total_bytes_out UInt64
) ENGINE = SummingMergeTree()
ORDER BY (window_hour, path, http_method, status_group);
