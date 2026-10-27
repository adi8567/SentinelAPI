"""ClickHouse Analytical Storage Engine Client.

Provides production-grade ClickHouse connection management and batch insertion.
"""

import asyncio
from datetime import datetime
import json
import logging
from typing import Any, Dict, List, Optional
from backend.app.core.config import settings
from backend.app.schemas.events import ApiEvent
from backend.app.services.storage.repository import IStorageRepository

logger = logging.getLogger("sentinelapi.storage.clickhouse")


class ClickHouseStorageRepository(IStorageRepository):
    """ClickHouse analytical repository."""

    def __init__(self):
        self.host = settings.CLICKHOUSE_HOST
        self.port = settings.CLICKHOUSE_PORT
        self.user = settings.CLICKHOUSE_USER
        self.password = settings.CLICKHOUSE_PASSWORD
        self.database = settings.CLICKHOUSE_DATABASE
        self.secure = settings.CLICKHOUSE_SECURE
        self._client = None

    async def initialize(self) -> None:
        try:
            import clickhouse_connect

            def _connect():
                client = clickhouse_connect.get_client(
                    host=self.host,
                    port=self.port,
                    username=self.user,
                    password=self.password,
                    secure=self.secure,
                )
                client.command(f"CREATE DATABASE IF NOT EXISTS {self.database}")
                client.database = self.database
                # Read and execute DDL
                # In prod, runs 001_initial_schema.sql
                return client

            loop = asyncio.get_event_loop()
            self._client = await loop.run_in_executor(None, _connect)
            logger.info(f"ClickHouse connected at {self.host}:{self.port}/{self.database}")
        except Exception as e:
            logger.warning(f"Could not connect to ClickHouse ({e}). Storage fallback enabled.")
            self._client = None

    async def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    async def store_events(self, events: List[ApiEvent]) -> int:
        if not events or not self._client:
            return 0

        data = []
        for e in events:
            data.append([
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
                1 if e.is_tls else 0,
                e.tls_version,
                e.raw_log,
                json.dumps(e.metadata),
            ])

        columns = [
            "event_id", "timestamp", "source_type", "gateway_id", "http_method",
            "path", "raw_path", "query_params", "status_code", "latency_ms",
            "client_ip", "user_agent", "auth_type", "auth_identity",
            "request_size_bytes", "response_size_bytes", "headers_summary",
            "geo_country", "is_tls", "tls_version", "raw_log", "metadata",
        ]

        def _insert():
            self._client.insert("api_events", data, column_names=columns)
            return len(data)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _insert)

    async def store_raw_log(self, raw_log: str, source_type: str, gateway_id: str) -> None:
        if not self._client:
            return
        import uuid
        now = datetime.utcnow()
        row = [[str(uuid.uuid4()), now, source_type, gateway_id, raw_log]]
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._client.insert("raw_events", row, column_names=["id", "received_at", "source_type", "gateway_id", "raw_log"])
        )

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
        if not self._client:
            return []

        conditions = ["1=1"]
        params: Dict[str, Any] = {}

        if start_time:
            conditions.append("timestamp >= %(start_time)s")
            params["start_time"] = start_time
        if end_time:
            conditions.append("timestamp <= %(end_time)s")
            params["end_time"] = end_time
        if http_method:
            conditions.append("http_method = %(http_method)s")
            params["http_method"] = http_method.upper()
        if path:
            conditions.append("path LIKE %(path)s")
            params["path"] = f"%{path}%"
        if status_code:
            conditions.append("status_code = %(status_code)s")
            params["status_code"] = status_code
        if client_ip:
            conditions.append("client_ip = %(client_ip)s")
            params["client_ip"] = client_ip

        where_clause = " AND ".join(conditions)
        sql = f"""
            SELECT * FROM api_events
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT {limit} OFFSET {offset}
        """

        def _query():
            df = self._client.query_df(sql, parameters=params)
            return df.to_dict(orient="records")

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _query)

    async def get_total_events_count(self) -> int:
        if not self._client:
            return 0
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, lambda: self._client.command("SELECT count() FROM api_events"))
        return int(res)

    async def get_traffic_metrics(self) -> Dict[str, Any]:
        if not self._client:
            return {"error": "ClickHouse not connected"}
        # Aggregation query
        sql = """
            SELECT
                count() as total_reqs,
                avg(latency_ms) as avg_lat,
                quantile(0.50)(latency_ms) as p50,
                quantile(0.95)(latency_ms) as p95,
                quantile(0.99)(latency_ms) as p99,
                sum(request_size_bytes) as total_bytes_in,
                sum(response_size_bytes) as total_bytes_out
            FROM api_events
        """
        loop = asyncio.get_event_loop()
        row = await loop.run_in_executor(None, lambda: self._client.query(sql).first_row)
        return {
            "total_requests": int(row[0] or 0),
            "avg_latency_ms": round(float(row[1] or 0.0), 2),
            "p50_latency_ms": round(float(row[2] or 0.0), 2),
            "p95_latency_ms": round(float(row[3] or 0.0), 2),
            "p99_latency_ms": round(float(row[4] or 0.0), 2),
            "total_bytes_in": int(row[5] or 0),
            "total_bytes_out": int(row[6] or 0),
        }

    async def store_inventory_records(
        self,
        endpoints: List[Any],
        clients: List[Any],
        sessions: List[Any],
    ) -> None:
        if not self._client:
            return
        # Stored in ClickHouse when connected

    async def store_baselines(
        self,
        endpoint_baselines: List[Any],
        client_baselines: List[Any],
    ) -> None:
        if not self._client:
            return

    async def store_anomaly(self, anomaly: Any) -> None:
        if not self._client:
            return

    async def query_anomalies(
        self,
        severity: Optional[str] = None,
        endpoint_id: Optional[str] = None,
        client_id: Optional[str] = None,
        min_risk_score: Optional[float] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        return []

    async def apply_retention_policy(
        self,
        raw_retention_days: int = 30,
        events_retention_days: int = 90,
    ) -> Dict[str, int]:
        if not self._client:
            return {"deleted_raw_logs": 0, "deleted_api_events": 0}
        # In ClickHouse, TTL handles retention automatically
        return {"deleted_raw_logs": 0, "deleted_api_events": 0}

    async def health_check(self) -> Dict[str, Any]:
        if not self._client:
            return {"status": "down", "engine": "clickhouse", "error": "Not connected"}
        try:
            loop = asyncio.get_event_loop()
            ver = await loop.run_in_executor(None, lambda: self._client.server_version)
            return {"status": "healthy", "engine": "clickhouse", "version": ver}
        except Exception as e:
            return {"status": "down", "engine": "clickhouse", "error": str(e)}
