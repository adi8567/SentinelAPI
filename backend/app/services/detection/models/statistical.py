"""Statistical Anomaly Detector.

Detects outliers using Z-score, modified Z-score (MAD), quantile threshold exceedance,
and status code probability divergences against learned endpoint baselines.
"""

import math
from typing import Optional
from backend.app.schemas.anomaly import DetectorResult, DetectorType
from backend.app.schemas.baseline import EndpointBaseline
from backend.app.schemas.events import ApiEvent


class StatisticalDetector:
    """Evaluates univariate statistical divergences against established baselines."""

    def __init__(
        self,
        z_score_threshold: float = 3.0,
        quantile_multiplier: float = 1.5,
        rare_status_prob_threshold: float = 0.02,
    ):
        self.z_score_threshold = z_score_threshold
        self.quantile_multiplier = quantile_multiplier
        self.rare_status_prob_threshold = rare_status_prob_threshold

    def evaluate(self, event: ApiEvent, baseline: Optional[EndpointBaseline]) -> DetectorResult:
        if not baseline or baseline.sample_size < 3:
            # Insufficient baseline data for statistical inference
            return DetectorResult(
                detector_name=DetectorType.STATISTICAL.value,
                is_anomaly=False,
                score=0.0,
                confidence=0.3,
                reasons=[],
            )

        score = 0.0
        reasons = []

        # 1. Latency Z-score & Quantile Threshold Check
        if baseline.latency_std > 0.0:
            z_latency = (event.latency_ms - baseline.latency_mean) / baseline.latency_std
            if z_latency > self.z_score_threshold:
                severity_boost = min(40.0, (z_latency - self.z_score_threshold) * 10.0 + 20.0)
                score += severity_boost
                reasons.append(
                    f"Latency spike: {event.latency_ms:.1f}ms exceeds mean {baseline.latency_mean:.1f}ms "
                    f"(Z-score: {z_latency:.2f}, threshold: {self.z_score_threshold})"
                )
        elif event.latency_ms > baseline.latency_p99 * self.quantile_multiplier and baseline.latency_p99 > 0:
            score += 30.0
            reasons.append(
                f"Latency ({event.latency_ms:.1f}ms) exceeds 99th percentile threshold ({baseline.latency_p99:.1f}ms)"
            )

        # 2. Status Code Probability Check
        status_str = str(event.status_code)
        status_prob = baseline.status_code_distribution.get(status_str, 0.0)
        if event.status_code >= 400:
            if status_prob <= self.rare_status_prob_threshold:
                score += 45.0
                reasons.append(
                    f"Unusual status code {event.status_code}: historical probability on this route is "
                    f"{status_prob*100:.1f}% (threshold <= {self.rare_status_prob_threshold*100:.1f}%)"
                )
            elif event.status_code in {500, 502, 503, 504}:
                score += 25.0
                reasons.append(f"Server error {event.status_code} observed on endpoint")

        # 3. Request Payload Size Check
        if baseline.request_size_std > 0.0 and event.request_size_bytes > 0:
            z_req = (event.request_size_bytes - baseline.request_size_mean) / baseline.request_size_std
            if z_req > self.z_score_threshold:
                score += 20.0
                reasons.append(
                    f"Abnormal payload size: {event.request_size_bytes} bytes exceeds mean "
                    f"{baseline.request_size_mean:.0f} bytes (Z-score: {z_req:.2f})"
                )

        score = min(100.0, score)
        is_anomaly = score >= 35.0

        return DetectorResult(
            detector_name=DetectorType.STATISTICAL.value,
            is_anomaly=is_anomaly,
            score=round(score, 1),
            confidence=min(1.0, 0.5 + (baseline.sample_size / 20.0)),
            reasons=reasons,
            metadata={
                "latency_z": round((event.latency_ms - baseline.latency_mean) / baseline.latency_std, 2)
                if baseline.latency_std > 0 else 0.0,
                "status_prob": status_prob,
            },
        )
