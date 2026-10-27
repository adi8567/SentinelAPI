-- SentinelAPI Phase 3 Migration: Anomalies Store

CREATE TABLE IF NOT EXISTS anomalies (
    anomaly_id VARCHAR PRIMARY KEY,
    event_id VARCHAR NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    endpoint_id VARCHAR NOT NULL,
    http_method VARCHAR NOT NULL,
    path VARCHAR NOT NULL,
    client_ip VARCHAR NOT NULL,
    client_id VARCHAR NOT NULL,
    risk_score DOUBLE NOT NULL,
    severity VARCHAR NOT NULL,
    primary_detector VARCHAR NOT NULL,
    detector_scores VARCHAR,          -- JSON map
    contributing_factors VARCHAR,     -- JSON list
    event_snapshot VARCHAR,           -- JSON map
    is_mitigated BOOLEAN DEFAULT FALSE,
    is_false_positive BOOLEAN DEFAULT FALSE,
    model_version VARCHAR DEFAULT 'v1.0.0'
);

CREATE INDEX IF NOT EXISTS idx_anomalies_ts ON anomalies (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_anomalies_risk ON anomalies (risk_score DESC);
CREATE INDEX IF NOT EXISTS idx_anomalies_endpoint ON anomalies (endpoint_id);
CREATE INDEX IF NOT EXISTS idx_anomalies_client ON anomalies (client_id);
