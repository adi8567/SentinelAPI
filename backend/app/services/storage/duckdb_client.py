"""DuckDB Analytical Storage Engine Client.

Provides embedded, columnar, in-process time-series storage compatible with ClickHouse
SQL semantics. Perfect for local execution, tests, and standalone deployments.
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import duckdb
from backend.app.core.config import settings
from backend.app.schemas.events import ApiEvent
from backend.app.services.storage.repository import IStorageRepository

logger = logging.getLogger("sentinelapi.storage.duckdb")


class DuckDBStorageRepository(IStorageRepository):
    """Columnar time-series repository powered by DuckDB."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.DUCKDB_PATH
        self._conn: Optional[duckdb.DuckDBPyConnection] = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initializes DuckDB database and creates tables & indices."""
        def _init_db():
            if self.db_path != ":memory:":
                Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            conn = duckdb.connect(self.db_path)
            
            # 1. Raw Audit Events
            conn.execute("""
                CREATE TABLE IF NOT EXISTS raw_events (
                    id VARCHAR PRIMARY KEY,
                    received_at TIMESTAMP WITH TIME ZONE,
                    source_type VARCHAR,
                    gateway_id VARCHAR,
                    raw_log VARCHAR
                );
            """)

            # 2. Standardized Normalized API Events
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_events (
                    event_id VARCHAR PRIMARY KEY,
                    timestamp TIMESTAMP WITH TIME ZONE,
                    source_type VARCHAR,
                    gateway_id VARCHAR,
                    http_method VARCHAR,
                    path VARCHAR,
                    raw_path VARCHAR,
                    query_params VARCHAR,
                    status_code INTEGER,
                    latency_ms DOUBLE,
                    client_ip VARCHAR,
                    user_agent VARCHAR,
                    auth_type VARCHAR,
                    auth_identity VARCHAR,
                    request_size_bytes BIGINT,
                    response_size_bytes BIGINT,
                    headers_summary VARCHAR,
                    geo_country VARCHAR,
                    is_tls BOOLEAN,
                    tls_version VARCHAR,
                    raw_log VARCHAR,
                    metadata VARCHAR
                );
            """)

            # Indices for rapid querying
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON api_events (timestamp);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_path ON api_events (path);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_status ON api_events (status_code);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ip ON api_events (client_ip);")

            # 3. Discovered Endpoints
            conn.execute("""
                CREATE TABLE IF NOT EXISTS endpoints (
                    endpoint_id VARCHAR PRIMARY KEY,
                    http_method VARCHAR,
                    path_template VARCHAR,
                    sample_raw_paths VARCHAR,
                    first_seen_at TIMESTAMP WITH TIME ZONE,
                    last_seen_at TIMESTAMP WITH TIME ZONE,
                    call_count BIGINT,
                    parameters VARCHAR,
                    is_authenticated BOOLEAN,
                    auth_types_observed VARCHAR,
                    status_codes_observed VARCHAR,
                    risk_level VARCHAR,
                    tags VARCHAR,
                    metadata VARCHAR
                );
            """)

            # 4. Discovered Clients
            conn.execute("""
                CREATE TABLE IF NOT EXISTS clients (
                    client_id VARCHAR PRIMARY KEY,
                    client_type VARCHAR,
                    ip_address VARCHAR,
                    user_agents_observed VARCHAR,
                    first_seen_at TIMESTAMP WITH TIME ZONE,
                    last_seen_at TIMESTAMP WITH TIME ZONE,
                    total_requests BIGINT,
                    error_count BIGINT,
                    distinct_endpoints_count INT,
                    observed_endpoints VARCHAR,
                    geo_country VARCHAR,
                    reputation_score DOUBLE
                );
            """)

            # 5. Client Sessions
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id VARCHAR PRIMARY KEY,
                    identity VARCHAR,
                    client_ip VARCHAR,
                    user_agent VARCHAR,
                    started_at TIMESTAMP WITH TIME ZONE,
                    last_activity_at TIMESTAMP WITH TIME ZONE,
                    event_count INT,
                    endpoint_sequence VARCHAR,
                    status_sequence VARCHAR
                );
            """)

            # 6. Statistical Baselines
            conn.execute("""
                CREATE TABLE IF NOT EXISTS baselines (
                    baseline_id VARCHAR PRIMARY KEY,
                    endpoint_id VARCHAR,
                    client_id VARCHAR,
                    window_type VARCHAR,
                    sample_size BIGINT,
                    req_rate_mean DOUBLE,
                    req_rate_std DOUBLE,
                    latency_p50 DOUBLE,
                    latency_p90 DOUBLE,
                    latency_p95 DOUBLE,
                    latency_p99 DOUBLE,
                    latency_mean DOUBLE,
                    latency_std DOUBLE,
                    request_size_mean DOUBLE,
                    request_size_std DOUBLE,
                    response_size_mean DOUBLE,
                    response_size_std DOUBLE,
                    status_code_distribution VARCHAR,
                    seasonality_hour_of_day VARCHAR,
                    seasonality_day_of_week VARCHAR,
                    updated_at TIMESTAMP WITH TIME ZONE,
                    version INT
                );
            """)
            return conn

        loop = asyncio.get_event_loop()
        self._conn = await loop.run_in_executor(None, _init_db)
        logger.info(f"DuckDB storage engine initialized at '{self.db_path}'.")

    async def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("DuckDB storage connection closed.")

    async def store_events(self, events: List[ApiEvent]) -> int:
        if not events:
            return 0
        if not self._conn:
            await self.initialize()

        rows = []
        for e in events:
            rows.append((
                e.event_id,
                e.timestamp,
                e.source_type.value,
                e.gateway_id,
                e.http_method,
                e.path,
                e.raw_path,
                json.dumps(e.query_params),
                e.status_code,
                e.latency_ms,
                e.client_ip,
                e.user_agent,
                e.auth_type.value,
                e.auth_identity,
                e.request_size_bytes,
                e.response_size_bytes,
                json.dumps(e.headers_summary),
                e.geo_country,
                e.is_tls,
                e.tls_version,
                e.raw_log,
                json.dumps(e.metadata),
            ))

        def _insert(conn):
            conn.executemany("""
                INSERT OR REPLACE INTO api_events VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                );
            """, rows)
            return len(rows)

        async with self._lock:
            loop = asyncio.get_event_loop()
            inserted = await loop.run_in_executor(None, _insert, self._conn)
            return inserted

    async def store_raw_log(self, raw_log: str, source_type: str, gateway_id: str) -> None:
        if not self._conn:
            await self.initialize()
        import uuid
        now = datetime.now(timezone.utc)
        record_id = str(uuid.uuid4())

        def _insert_raw(conn):
            conn.execute("""
                INSERT INTO raw_events (id, received_at, source_type, gateway_id, raw_log)
                VALUES (?, ?, ?, ?, ?);
            """, (record_id, now, source_type, gateway_id, raw_log))

        async with self._lock:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _insert_raw, self._conn)

    async def query_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        http_method: Optional[str] = None,
        path: Optional[str] = None,
        status_code: Optional[int] = None,
        client_ip: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        if not self._conn:
            await self.initialize()

        conditions = ["1=1"]
        params: List[Any] = []

        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time)
        if http_method:
            conditions.append("http_method = ?")
            params.append(http_method.upper())
        if path:
            conditions.append("path LIKE ?")
            params.append(f"%{path}%")
        if status_code:
            conditions.append("status_code = ?")
            params.append(status_code)
        if client_ip:
            conditions.append("client_ip = ?")
            params.append(client_ip)

        where_clause = " AND ".join(conditions)
        sql = f"""
            SELECT * FROM api_events
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        def _query(conn):
            cursor = conn.execute(sql, params)
            columns = [desc[0] for desc in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            return results

        async with self._lock:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _query, self._conn)

    async def get_total_events_count(self) -> int:
        if not self._conn:
            await self.initialize()

        def _count(conn):
            return conn.execute("SELECT count(*) FROM api_events").fetchone()[0]

        async with self._lock:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _count, self._conn)

    async def get_traffic_metrics(self) -> Dict[str, Any]:
        if not self._conn:
            await self.initialize()

        def _metrics(conn):
            total_reqs = conn.execute("SELECT count(*) FROM api_events").fetchone()[0]
            if total_reqs == 0:
                return {
                    "total_requests": 0,
                    "avg_latency_ms": 0.0,
                    "p50_latency_ms": 0.0,
                    "p95_latency_ms": 0.0,
                    "p99_latency_ms": 0.0,
                    "status_breakdown": {},
                    "top_endpoints": [],
                    "methods_breakdown": {},
                }

            # Latencies & aggregates
            stats_row = conn.execute("""
                SELECT
                    avg(latency_ms) as avg_lat,
                    quantile_cont(latency_ms, 0.50) as p50,
                    quantile_cont(latency_ms, 0.95) as p95,
                    quantile_cont(latency_ms, 0.99) as p99,
                    sum(request_size_bytes) as total_bytes_in,
                    sum(response_size_bytes) as total_bytes_out
                FROM api_events
            """).fetchone()

            # Status breakdown
            status_rows = conn.execute("""
                SELECT status_code, count(*) as cnt
                FROM api_events
                GROUP BY status_code
                ORDER BY cnt DESC
            """).fetchall()
            status_map = {str(r[0]): r[1] for r in status_rows}

            # Methods breakdown
            methods_rows = conn.execute("""
                SELECT http_method, count(*) as cnt
                FROM api_events
                GROUP BY http_method
                ORDER BY cnt DESC
            """).fetchall()
            methods_map = {str(r[0]): r[1] for r in methods_rows}

            # Top endpoints
            top_eps = conn.execute("""
                SELECT http_method, path, count(*) as cnt, avg(latency_ms) as avg_lat
                FROM api_events
                GROUP BY http_method, path
                ORDER BY cnt DESC
                LIMIT 10
            """).fetchall()
            endpoints = [
                {"method": r[0], "path": r[1], "count": r[2], "avg_latency_ms": round(float(r[3]), 2)}
                for r in top_eps
            ]

            return {
                "total_requests": total_reqs,
                "avg_latency_ms": round(float(stats_row[0] or 0.0), 2),
                "p50_latency_ms": round(float(stats_row[1] or 0.0), 2),
                "p95_latency_ms": round(float(stats_row[2] or 0.0), 2),
                "p99_latency_ms": round(float(stats_row[3] or 0.0), 2),
                "total_bytes_in": int(stats_row[4] or 0),
                "total_bytes_out": int(stats_row[5] or 0),
                "status_breakdown": status_map,
                "methods_breakdown": methods_map,
                "top_endpoints": endpoints,
            }

        async with self._lock:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _metrics, self._conn)

    async def store_inventory_records(
        self,
        endpoints: List[Any],
        clients: List[Any],
        sessions: List[Any],
    ) -> None:
        if not self._conn:
            await self.initialize()

        ep_rows = [
            (
                e.endpoint_id,
                e.http_method,
                e.path_template,
                json.dumps(e.sample_raw_paths),
                e.first_seen_at,
                e.last_seen_at,
                e.call_count,
                json.dumps({k: v.model_dump() for k, v in e.parameters.items()}),
                e.is_authenticated,
                json.dumps(e.auth_types_observed),
                json.dumps(e.status_codes_observed),
                e.risk_level.value,
                json.dumps(e.tags),
                json.dumps(e.metadata),
            )
            for e in endpoints
        ]

        cl_rows = [
            (
                c.client_id,
                c.client_type.value,
                c.ip_address,
                json.dumps(c.user_agents_observed),
                c.first_seen_at,
                c.last_seen_at,
                c.total_requests,
                c.error_count,
                c.distinct_endpoints_count,
                json.dumps(c.observed_endpoints),
                c.geo_country,
                c.reputation_score,
            )
            for c in clients
        ]

        sess_rows = [
            (
                s.session_id,
                s.identity,
                s.client_ip,
                s.user_agent,
                s.started_at,
                s.last_activity_at,
                s.event_count,
                json.dumps(s.endpoint_sequence),
                json.dumps(s.status_sequence),
            )
            for s in sessions
        ]

        def _persist(conn):
            if ep_rows:
                conn.executemany("""
                    INSERT OR REPLACE INTO endpoints VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    );
                """, ep_rows)
            if cl_rows:
                conn.executemany("""
                    INSERT OR REPLACE INTO clients VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    );
                """, cl_rows)
            if sess_rows:
                conn.executemany("""
                    INSERT OR REPLACE INTO sessions VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?
                    );
                """, sess_rows)

        async with self._lock:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _persist, self._conn)

    async def store_baselines(
        self,
        endpoint_baselines: List[Any],
        client_baselines: List[Any],
    ) -> None:
        if not self._conn:
            await self.initialize()

        base_rows = [
            (
                b.baseline_id,
                b.endpoint_id,
                None,
                b.window_type.value,
                b.sample_size,
                b.req_rate_mean,
                b.req_rate_std,
                b.latency_p50,
                b.latency_p90,
                b.latency_p95,
                b.latency_p99,
                b.latency_mean,
                b.latency_std,
                b.request_size_mean,
                b.request_size_std,
                b.response_size_mean,
                b.response_size_std,
                json.dumps(b.status_code_distribution),
                json.dumps(b.seasonality_hour_of_day),
                json.dumps(b.seasonality_day_of_week),
                b.updated_at,
                b.version,
            )
            for b in endpoint_baselines
        ]

        def _persist_baselines(conn):
            if base_rows:
                conn.executemany("""
                    INSERT OR REPLACE INTO baselines VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    );
                """, base_rows)

        async with self._lock:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _persist_baselines, self._conn)

    async def apply_retention_policy(
        self,
        raw_retention_days: int = 30,
        events_retention_days: int = 90,
    ) -> Dict[str, int]:
        if not self._conn:
            await self.initialize()

        def _purge(conn):
            now = datetime.now(timezone.utc)
            # Delete old raw audit records
            raw_res = conn.execute(
                f"DELETE FROM raw_events WHERE received_at < now() - INTERVAL '{raw_retention_days} days'"
            ).fetchone()
            deleted_raw = raw_res[0] if raw_res else 0

            # Delete old api_events
            ev_res = conn.execute(
                f"DELETE FROM api_events WHERE timestamp < now() - INTERVAL '{events_retention_days} days'"
            ).fetchone()
            deleted_events = ev_res[0] if ev_res else 0

            return {"deleted_raw_logs": deleted_raw, "deleted_api_events": deleted_events}

        async with self._lock:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _purge, self._conn)

    async def health_check(self) -> Dict[str, Any]:
        try:
            if not self._conn:
                await self.initialize()
            count = await self.get_total_events_count()
            return {
                "status": "healthy",
                "engine": "duckdb",
                "database": self.db_path,
                "events_count": count,
            }
        except Exception as e:
            return {
                "status": "down",
                "engine": "duckdb",
                "error": str(e),
            }
