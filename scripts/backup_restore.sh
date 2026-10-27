#!/usr/bin/env bash
# ==============================================================================
# SentinelAPI Automated Backup & Disaster Recovery Script
# Supports: ClickHouse, TimescaleDB, and DuckDB analytical storage snapshots.
# RPO Target: < 1 minute | RTO Target: < 15 minutes
# ==============================================================================

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/sentinelapi}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RETENTION_DAYS="${RETENTION_DAYS:-14}"

mkdir -p "${BACKUP_DIR}/${TIMESTAMP}"

echo "========================================================"
echo " SentinelAPI Automated Backup Initiated: ${TIMESTAMP}"
echo "========================================================"

# 1. ClickHouse Columnar Data Backup
backup_clickhouse() {
    echo "[1/3] Backing up ClickHouse tables and metadata..."
    if command -v clickhouse-client &>/dev/null; then
        clickhouse-client --query="FREEZE DATABASE sentinelapi" || true
        cp -r /var/lib/clickhouse/shadow "${BACKUP_DIR}/${TIMESTAMP}/clickhouse_shadow"
        echo "✓ ClickHouse partition freeze completed."
    else
        echo "ℹ ClickHouse client not locally installed, skipping local binary freeze."
    fi
}

# 2. TimescaleDB / PostgreSQL Logical Dump
backup_timescale() {
    echo "[2/3] Dumping TimescaleDB metadata and policies..."
    if command -v pg_dump &>/dev/null; then
        PGPASSWORD="${POSTGRES_PASSWORD:-postgrespassword}" pg_dump \
            -h "${POSTGRES_HOST:-localhost}" \
            -p "${POSTGRES_PORT:-5432}" \
            -U "${POSTGRES_USER:-postgres}" \
            -F c -b -v \
            -f "${BACKUP_DIR}/${TIMESTAMP}/timescale_sentinelapi.dump" \
            "${POSTGRES_DB:-sentinelapi}"
        echo "✓ TimescaleDB pg_dump complete."
    else
        echo "ℹ pg_dump not locally installed, skipping PostgreSQL dump."
    fi
}

# 3. DuckDB Embedded Database Snapshot
backup_duckdb() {
    echo "[3/3] Backing up embedded DuckDB database file..."
    DUCKDB_PATH="${DUCKDB_PATH:-./data/sentinelapi.duckdb}"
    if [ -f "${DUCKDB_PATH}" ]; then
        cp "${DUCKDB_PATH}" "${BACKUP_DIR}/${TIMESTAMP}/sentinelapi.duckdb"
        echo "✓ DuckDB database file copied."
    fi
}

# Execute Backups
backup_clickhouse
backup_timescale
backup_duckdb

# Compress Archive
ARCHIVE_PATH="${BACKUP_DIR}/sentinelapi_backup_${TIMESTAMP}.tar.gz"
tar -czf "${ARCHIVE_PATH}" -C "${BACKUP_DIR}" "${TIMESTAMP}"
rm -rf "${BACKUP_DIR}/${TIMESTAMP}"

echo "========================================================"
echo "✓ Backup successfully created at: ${ARCHIVE_PATH}"
echo "========================================================"

# Cleanup old backups based on retention policy
find "${BACKUP_DIR}" -name "sentinelapi_backup_*.tar.gz" -mtime +"${RETENTION_DAYS}" -delete
echo "Cleaned up backups older than ${RETENTION_DAYS} days."
