"""SentinelAPI Batch Baseline Learning Engine.

Computes comprehensive historical statistical baselines (quantiles, means,
standard deviations, status distributions, and seasonality) over stored real traffic.
"""

from collections import defaultdict
from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List, Optional
import numpy as np

from backend.app.schemas.baseline import (
    BaselineWindow,
    ClientBaseline,
    EndpointBaseline,
    RecomputeBaselinesResult,
)
from backend.app.services.inventory.path_normalizer import (
    generate_endpoint_id,
    parameterize_path,
)
from backend.app.services.storage.factory import get_storage
from backend.app.services.storage.repository import IStorageRepository

logger = logging.getLogger("sentinelapi.baseline.batch")


class BatchBaselineLearner:
    """Historical batch learning engine for behavioral API baselines."""

    def __init__(self, storage: Optional[IStorageRepository] = None):
        self._storage = storage
        self._endpoint_baselines: Dict[str, EndpointBaseline] = {}
        self._client_baselines: Dict[str, ClientBaseline] = {}

    async def _get_storage(self) -> IStorageRepository:
        if self._storage is None:
            self._storage = await get_storage()
        return self._storage

    async def compute_all_baselines(self, limit: int = 100000) -> RecomputeBaselinesResult:
        """Executes full baseline recomputation from historical traffic."""
        start_ts = time.perf_counter()
        storage = await self._get_storage()

        # Query all events from analytical store
        events = await storage.query_events(limit=limit)
        if not events:
            return RecomputeBaselinesResult(
                success=True,
                endpoints_computed=0,
                clients_computed=0,
                total_events_analyzed=0,
                execution_time_ms=0.0,
            )

        # 1. Group events by endpoint
        ep_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        # 2. Group events by client
        client_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for ev in events:
            method = ev["http_method"]
            path = ev["path"]
            path_tmpl = parameterize_path(path)
            ep_id = generate_endpoint_id(method, path_tmpl)

            # Enrich event with template
            ev["path_template"] = path_tmpl
            ev["endpoint_id"] = ep_id

            ep_groups[ep_id].append(ev)

            client_id = ev.get("auth_identity") or ev.get("client_ip", "127.0.0.1")
            client_groups[client_id].append(ev)

        # 3. Calculate Endpoint Baselines
        computed_ep_baselines = {}
        for ep_id, ep_events in ep_groups.items():
            baseline = self._calculate_endpoint_baseline(ep_id, ep_events)
            computed_ep_baselines[ep_id] = baseline

        # 4. Calculate Client Baselines
        computed_client_baselines = {}
        for client_id, cl_events in client_groups.items():
            c_base = self._calculate_client_baseline(client_id, cl_events)
            computed_client_baselines[client_id] = c_base

        self._endpoint_baselines = computed_ep_baselines
        self._client_baselines = computed_client_baselines

        # 5. Persist to storage repository
        if hasattr(storage, "store_baselines"):
            await storage.store_baselines(
                list(computed_ep_baselines.values()),
                list(computed_client_baselines.values()),
            )

        elapsed_ms = (time.perf_counter() - start_ts) * 1000.0
        return RecomputeBaselinesResult(
            success=True,
            endpoints_computed=len(computed_ep_baselines),
            clients_computed=len(computed_client_baselines),
            total_events_analyzed=len(events),
            execution_time_ms=round(elapsed_ms, 2),
        )

    def _calculate_endpoint_baseline(
        self, endpoint_id: str, events: List[Dict[str, Any]]
    ) -> EndpointBaseline:
        n = len(events)
        latencies = np.array([float(e["latency_ms"]) for e in events], dtype=np.float64)
        req_sizes = np.array([float(e.get("request_size_bytes", 0)) for e in events], dtype=np.float64)
        res_sizes = np.array([float(e.get("response_size_bytes", 0)) for e in events], dtype=np.float64)

        # Quantiles
        p50 = float(np.percentile(latencies, 50))
        p90 = float(np.percentile(latencies, 90))
        p95 = float(np.percentile(latencies, 95))
        p99 = float(np.percentile(latencies, 99))

        # Status distribution
        status_counts = defaultdict(int)
        hour_counts = defaultdict(int)
        day_counts = defaultdict(int)

        for e in events:
            status_counts[str(e["status_code"])] += 1
            ts = e["timestamp"]
            if isinstance(ts, str):
                from dateutil.parser import parse
                ts = parse(ts)
            hour_counts[ts.hour] += 1
            day_counts[ts.weekday()] += 1

        status_dist = {k: round(v / n, 4) for k, v in status_counts.items()}
        hour_dist = {k: round(v / n, 4) for k, v in hour_counts.items()}
        day_dist = {k: round(v / n, 4) for k, v in day_counts.items()}

        # Request rate approximation
        timestamps = sorted([
            e["timestamp"] if isinstance(e["timestamp"], datetime) else datetime.fromisoformat(str(e["timestamp"]))
            for e in events
        ])
        time_span_sec = max(1.0, (timestamps[-1] - timestamps[0]).total_seconds()) if len(timestamps) > 1 else 1.0
        req_rate_mean = round(n / time_span_sec, 4)

        return EndpointBaseline(
            baseline_id=f"base_{endpoint_id}",
            endpoint_id=endpoint_id,
            window_type=BaselineWindow.GLOBAL,
            sample_size=n,
            req_rate_mean=req_rate_mean,
            req_rate_std=round(req_rate_mean * 0.25, 4),  # Initial dispersion
            latency_p50=round(p50, 2),
            latency_p90=round(p90, 2),
            latency_p95=round(p95, 2),
            latency_p99=round(p99, 2),
            latency_mean=round(float(np.mean(latencies)), 2),
            latency_std=round(float(np.std(latencies)), 2),
            request_size_mean=round(float(np.mean(req_sizes)), 2),
            request_size_std=round(float(np.std(req_sizes)), 2),
            response_size_mean=round(float(np.mean(res_sizes)), 2),
            response_size_std=round(float(np.std(res_sizes)), 2),
            status_code_distribution=status_dist,
            seasonality_hour_of_day=hour_dist,
            seasonality_day_of_week=day_dist,
            updated_at=datetime.now(timezone.utc),
            version=1,
        )

    def _calculate_client_baseline(
        self, client_id: str, events: List[Dict[str, Any]]
    ) -> ClientBaseline:
        n = len(events)
        latencies = [float(e["latency_ms"]) for e in events]
        errors = sum(1 for e in events if int(e["status_code"]) >= 400)
        error_ratio = round(errors / n, 4) if n > 0 else 0.0

        ep_counter = defaultdict(int)
        for e in events:
            ep_counter[e.get("path_template", e["path"])] += 1
        top_eps = [k for k, _ in sorted(ep_counter.items(), key=lambda x: x[1], reverse=True)[:5]]

        return ClientBaseline(
            client_id=client_id,
            sample_size=n,
            req_rate_mean=round(n / 60.0, 4),
            req_rate_std=round((n / 60.0) * 0.2, 4),
            error_ratio=error_ratio,
            avg_latency_ms=round(float(np.mean(latencies)), 2),
            top_endpoints=top_eps,
            updated_at=datetime.now(timezone.utc),
            version=1,
        )

    def get_endpoint_baseline(self, endpoint_id: str) -> Optional[EndpointBaseline]:
        return self._endpoint_baselines.get(endpoint_id)

    def get_client_baseline(self, client_id: str) -> Optional[ClientBaseline]:
        return self._client_baselines.get(client_id)

    def get_all_endpoint_baselines(self) -> List[EndpointBaseline]:
        return list(self._endpoint_baselines.values())


# Global batch learner singleton
batch_baseline_learner = BatchBaselineLearner()
