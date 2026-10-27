-- SentinelAPI Phase 4 Migration: Policies, Decisions, Blocklist & Quarantine

-- 1. Declarative Policies
CREATE TABLE IF NOT EXISTS policies (
    policy_id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    description VARCHAR,
    is_enabled BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 100,
    conditions VARCHAR,        -- JSON serialized PolicyCondition
    action VARCHAR NOT NULL,
    action_params VARCHAR,     -- JSON serialized dict
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_policies_priority ON policies (priority ASC);

-- 2. Policy Enforcement Decision Audit Trail
CREATE TABLE IF NOT EXISTS policy_decisions (
    decision_id VARCHAR PRIMARY KEY,
    event_id VARCHAR NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    client_ip VARCHAR NOT NULL,
    endpoint VARCHAR NOT NULL,
    http_method VARCHAR NOT NULL,
    risk_score DOUBLE NOT NULL,
    severity VARCHAR NOT NULL,
    action_taken VARCHAR NOT NULL,
    matched_policy_id VARCHAR,
    matched_policy_name VARCHAR,
    reason VARCHAR NOT NULL,
    action_details VARCHAR,    -- JSON serialized dict
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_decisions_ts ON policy_decisions (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_decisions_action ON policy_decisions (action_taken);
CREATE INDEX IF NOT EXISTS idx_decisions_ip ON policy_decisions (client_ip);

-- 3. IP Blocklist Store
CREATE TABLE IF NOT EXISTS ip_blocklist (
    ip VARCHAR PRIMARY KEY,
    reason VARCHAR NOT NULL,
    banned_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    policy_id VARCHAR,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_blocklist_active ON ip_blocklist (is_active, expires_at);

-- 4. Quarantine Store
CREATE TABLE IF NOT EXISTS quarantine_records (
    client_ip VARCHAR PRIMARY KEY,
    client_id VARCHAR,
    quarantined_at TIMESTAMP WITH TIME ZONE NOT NULL,
    reason VARCHAR NOT NULL,
    policy_id VARCHAR,
    is_active BOOLEAN DEFAULT TRUE
);
