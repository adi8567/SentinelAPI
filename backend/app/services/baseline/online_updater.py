"""SentinelAPI Online Streaming Baseline Engine.

Calculates real-time running statistical baselines (mean, variance, EMA, rate)
using Welford's algorithm as events stream through the system.
"""

from collections import defaultdict
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional
from backend.app.schemas.baseline import BaselineWindow, EndpointBaseline
from backend.app.schemas.events import ApiEvent
from backend.app.services.inventory.path_normalizer import (
    generate_endpoint_id,
    parameterize_path,
)


class WelfordAccumulator:
    """Computes running mean and variance in O(1) space with numerical stability."""

    def __init__(self):
        self.count: int = 0
        self.mean: float = 0.0
        self.M2: float = 0.0

    def update(self, x: float) -> None:
        self.count += 1
        delta = x - self.mean
        self.mean += delta / self.count
        delta2 = x - self.mean
        self.M2 += delta * delta2

    @property
    def variance(self) -> float:
        return self.M2 / self.count if self.count > 1 else 0.0

    @property
    def std_dev(self) -> float:
        return math.sqrt(self.variance)


class OnlineEndpointTracker:
    """Tracks running streaming statistics for a single endpoint."""

    def __init__(self, endpoint_id: str):
        self.endpoint_id = endpoint_id
        self.latency_acc = WelfordAccumulator()
        self.req_size_acc = WelfordAccumulator()
        self.res_size_acc = WelfordAccumulator()
        self.status_counts: Dict[str, int] = defaultdict(int)
        self.hour_counts: Dict[int, int] = defaultdict(int)
        self.day_counts: Dict[int, int] = defaultdict(int)
        self.recent_latencies: List[float] = []
        self.last_updated: datetime = datetime.now(timezone.utc)
        self.version: int = 1

    def observe(self, latency_ms: float, req_bytes: int, res_bytes: int, status_code: int, ts: datetime) -> None:
        self.latency_acc.update(latency_ms)
        self.req_size_acc.update(float(req_bytes))
        self.res_size_acc.update(float(res_bytes))
        self.status_counts[str(status_code)] += 1
        self.hour_counts[ts.hour] += 1
        self.day_counts[ts.weekday()] += 1

        self.recent_latencies.append(latency_ms)
        if len(self.recent_latencies) > 200:
            self.recent_latencies.pop(0)

        self.last_updated = ts

    def to_baseline(self) -> EndpointBaseline:
        n = self.latency_acc.count
        if n == 0:
            return EndpointBaseline(
                baseline_id=f"base_{self.endpoint_id}",
                endpoint_id=self.endpoint_id,
            )

        # Approximate quantiles from recent reservoir
        sorted_lats = sorted(self.recent_latencies)
        def _q(pct: float) -> float:
            if not sorted_lats:
                return 0.0
            idx = int(pct * (len(sorted_lats) - 1))
            return sorted_lats[idx]

        # Status code distribution probabilities
        status_dist = {k: round(v / n, 4) for k, v in self.status_counts.items()}
        hour_dist = {k: round(v / n, 4) for k, v in self.hour_counts.items()}
        day_dist = {k: round(v / n, 4) for k, v in self.day_counts.items()}

        return EndpointBaseline(
            baseline_id=f"base_{self.endpoint_id}",
            endpoint_id=self.endpoint_id,
            window_type=BaselineWindow.GLOBAL,
            sample_size=n,
            latency_p50=round(_q(0.50), 2),
            latency_p90=round(_q(0.90), 2),
            latency_p95=round(_q(0.95), 2),
            latency_p99=round(_q(0.99), 2),
            latency_mean=round(self.latency_acc.mean, 2),
            latency_std=round(self.latency_acc.std_dev, 2),
            request_size_mean=round(self.req_size_acc.mean, 2),
            request_size_std=round(self.req_size_acc.std_dev, 2),
            response_size_mean=round(self.res_size_acc.mean, 2),
            response_size_std=round(self.res_size_acc.std_dev, 2),
            status_code_distribution=status_dist,
            seasonality_hour_of_day=hour_dist,
            seasonality_day_of_week=day_dist,
            updated_at=self.last_updated,
            version=self.version,
        )


class OnlineBaselineUpdater:
    """Manages online streaming baseline updates across all active endpoints."""

    def __init__(self):
        self._trackers: Dict[str, OnlineEndpointTracker] = {}

    def observe_event(self, event: ApiEvent) -> EndpointBaseline:
        path_template = parameterize_path(event.path)
        ep_id = generate_endpoint_id(event.http_method, path_template)

        if ep_id not in self._trackers:
            self._trackers[ep_id] = OnlineEndpointTracker(ep_id)

        tracker = self._trackers[ep_id]
        tracker.observe(
            latency_ms=event.latency_ms,
            req_bytes=event.request_size_bytes,
            res_bytes=event.response_size_bytes,
            status_code=event.status_code,
            ts=event.timestamp,
        )
        return tracker.to_baseline()

    def get_baseline(self, endpoint_id: str) -> Optional[EndpointBaseline]:
        tracker = self._trackers.get(endpoint_id)
        if tracker:
            return tracker.to_baseline()
        return None

    def get_all_baselines(self) -> List[EndpointBaseline]:
        return [t.to_baseline() for t in self._trackers.values()]


# Global online baseline updater singleton
online_baseline_updater = OnlineBaselineUpdater()
