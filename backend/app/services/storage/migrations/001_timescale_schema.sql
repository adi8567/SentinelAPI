-- TimescaleDB / PostgreSQL DDL for SentinelAPI

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- Enable TimescaleDB extension if installed
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS timescaledb;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'TimescaleDB extension not available, falling back to standard PostgreSQL tables.';
END $$;

-- 1. Raw Audit Events
CREATE TABLE IF NOT EXISTS raw_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_type VARCHAR(64) NOT NULL,
    gateway_id VARCHAR(128) NOT NULL,
    raw_log TEXT NOT NULL
);

-- 2. Standardized Normalized API Events
CREATE TABLE IF NOT EXISTS api_events (
    event_id UUID NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    source_type VARCHAR(64) NOT NULL,
    gateway_id VARCHAR(128) NOT NULL,
    http_method VARCHAR(16) NOT NULL,
    path VARCHAR(1024) NOT NULL,
    raw_path TEXT NOT NULL,
    query_params JSONB NOT NULL DEFAULT '{}',
    status_code INT NOT NULL,
    latency_ms DOUBLE PRECISION NOT NULL,
    client_ip VARCHAR(45) NOT NULL,
    user_agent VARCHAR(512) NOT NULL,
    auth_type VARCHAR(32) NOT NULL,
    auth_identity VARCHAR(128),
    request_size_bytes BIGINT NOT NULL DEFAULT 0,
    response_size_bytes BIGINT NOT NULL DEFAULT 0,
    headers_summary JSONB NOT NULL DEFAULT '{}',
    geo_country VARCHAR(8),
    is_tls BOOLEAN NOT NULL DEFAULT TRUE,
    tls_version VARCHAR(32),
    raw_log TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'
);

-- Convert to Timescale hypertable if extension is available
DO $$
BEGIN
    PERFORM create_hypertable('api_events', 'timestamp', if_not_exists => TRUE);
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Skipping create_hypertable.';
END $$;

-- Indices for rapid querying
CREATE INDEX IF NOT EXISTS idx_api_events_ts_path ON api_events (timestamp DESC, path);
CREATE INDEX IF NOT EXISTS idx_api_events_client_ip ON api_events (client_ip, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_api_events_status ON api_events (status_code, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_api_events_method ON api_events (http_method, timestamp DESC);
