"""Storage Repository Interface.

Defines the contract for persisting and querying raw and normalized API events.
Supports ClickHouse, TimescaleDB, and DuckDB analytical storage engines.
"""

import abc
from datetime import datetime
from typing import Any, Dict, List, Optional
from backend.app.schemas.events import ApiEvent


class IStorageRepository(abc.ABC):
    """Contract for event storage engines."""

    @abc.abstractmethod
    async def initialize(self) -> None:
        """Runs migrations and prepares database schemas."""
        pass

    @abc.abstractmethod
    async def close(self) -> None:
        """Closes connection pools or file handles."""
        pass

    @abc.abstractmethod
    async def store_events(self, events: List[ApiEvent]) -> int:
        """Persists a batch of normalized ApiEvent records."""
        pass

    @abc.abstractmethod
    async def store_raw_log(self, raw_log: str, source_type: str, gateway_id: str) -> None:
        """Persists a raw unparsed log entry for auditing/forensics."""
        pass

    @abc.abstractmethod
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
        """Queries normalized events with multi-column filtering."""
        pass

    @abc.abstractmethod
    async def get_total_events_count(self) -> int:
        """Returns total count of stored events."""
        pass

    @abc.abstractmethod
    async def get_traffic_metrics(self) -> Dict[str, Any]:
        """Calculates aggregated metrics (requests by status, avg latency, top endpoints)."""
        pass

    @abc.abstractmethod
    async def store_inventory_records(
        self,
        endpoints: List[Any],
        clients: List[Any],
        sessions: List[Any],
    ) -> None:
        """Persists discovered endpoints, client profiles, and sessions."""
        pass

    @abc.abstractmethod
    async def store_baselines(
        self,
        endpoint_baselines: List[Any],
        client_baselines: List[Any],
    ) -> None:
        """Persists learned statistical behavioral baselines."""
        pass

    @abc.abstractmethod
    async def store_anomaly(self, anomaly: Any) -> None:
        """Persists an evaluated anomaly detection record."""
        pass

    @abc.abstractmethod
    async def query_anomalies(
        self,
        severity: Optional[str] = None,
        endpoint_id: Optional[str] = None,
        client_id: Optional[str] = None,
        min_risk_score: Optional[float] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Queries stored anomaly records with filtering."""
        pass

    @abc.abstractmethod
    async def apply_retention_policy(
        self,
        raw_retention_days: int = 30,
        events_retention_days: int = 90,
    ) -> Dict[str, int]:
        """Purges old records according to data retention policies."""
        pass

    @abc.abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Validates connection and returns engine health status."""
        pass
