-- SentinelAPI Phase 2 Migration: API Inventory, Clients, Sessions, and Baselines

-- 1. Discovered Endpoints
CREATE TABLE IF NOT EXISTS endpoints (
    endpoint_id VARCHAR PRIMARY KEY,
    http_method VARCHAR NOT NULL,
    path_template VARCHAR NOT NULL,
    sample_raw_paths VARCHAR,          -- JSON list
    first_seen_at TIMESTAMP WITH TIME ZONE,
    last_seen_at TIMESTAMP WITH TIME ZONE,
    call_count BIGINT DEFAULT 0,
    parameters VARCHAR,                -- JSON map
    is_authenticated BOOLEAN DEFAULT FALSE,
    auth_types_observed VARCHAR,       -- JSON list
    status_codes_observed VARCHAR,     -- JSON map
    risk_level VARCHAR DEFAULT 'low',
    tags VARCHAR,                      -- JSON list
    metadata VARCHAR                   -- JSON map
);

-- 2. Discovered Clients / Actors
CREATE TABLE IF NOT EXISTS clients (
    client_id VARCHAR PRIMARY KEY,
    client_type VARCHAR DEFAULT 'ip',
    ip_address VARCHAR NOT NULL,
    user_agents_observed VARCHAR,      -- JSON list
    first_seen_at TIMESTAMP WITH TIME ZONE,
    last_seen_at TIMESTAMP WITH TIME ZONE,
    total_requests BIGINT DEFAULT 0,
    error_count BIGINT DEFAULT 0,
    distinct_endpoints_count INT DEFAULT 0,
    observed_endpoints VARCHAR,        -- JSON list
    geo_country VARCHAR,
    reputation_score DOUBLE DEFAULT 100.0
);

-- 3. Sessions
CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR PRIMARY KEY,
    identity VARCHAR,
    client_ip VARCHAR NOT NULL,
    user_agent VARCHAR,
    started_at TIMESTAMP WITH TIME ZONE,
    last_activity_at TIMESTAMP WITH TIME ZONE,
    event_count INT DEFAULT 0,
    endpoint_sequence VARCHAR,         -- JSON list
    status_sequence VARCHAR            -- JSON list
);

-- 4. Statistical Behavioral Baselines
CREATE TABLE IF NOT EXISTS baselines (
    baseline_id VARCHAR PRIMARY KEY,
    endpoint_id VARCHAR,
    client_id VARCHAR,
    window_type VARCHAR DEFAULT 'global',
    sample_size BIGINT DEFAULT 0,
    req_rate_mean DOUBLE DEFAULT 0.0,
    req_rate_std DOUBLE DEFAULT 0.0,
    latency_p50 DOUBLE DEFAULT 0.0,
    latency_p90 DOUBLE DEFAULT 0.0,
    latency_p95 DOUBLE DEFAULT 0.0,
    latency_p99 DOUBLE DEFAULT 0.0,
    latency_mean DOUBLE DEFAULT 0.0,
    latency_std DOUBLE DEFAULT 0.0,
    request_size_mean DOUBLE DEFAULT 0.0,
    request_size_std DOUBLE DEFAULT 0.0,
    response_size_mean DOUBLE DEFAULT 0.0,
    response_size_std DOUBLE DEFAULT 0.0,
    status_code_distribution VARCHAR,  -- JSON map
    seasonality_hour_of_day VARCHAR,   -- JSON map
    seasonality_day_of_week VARCHAR,   -- JSON map
    updated_at TIMESTAMP WITH TIME ZONE,
    version INT DEFAULT 1
);
