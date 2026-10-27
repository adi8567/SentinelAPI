"""Contextual Risk Scorer.

Evaluates multi-faceted contextual attributes including client reputation,
endpoint criticality/sensitivity, and hour-of-day seasonality divergence.
"""

from typing import Optional
from backend.app.schemas.anomaly import DetectorResult, DetectorType
from backend.app.schemas.baseline import EndpointBaseline
from backend.app.schemas.events import ApiEvent
from backend.app.schemas.inventory import ClientRecord, EndpointRecord, RiskLevel


class ContextualRiskScorer:
    """Computes environmental, temporal, and identity risk factors."""

    def evaluate(
        self,
        event: ApiEvent,
        endpoint_record: Optional[EndpointRecord],
        client_record: Optional[ClientRecord],
        baseline: Optional[EndpointBaseline],
    ) -> DetectorResult:
        score = 0.0
        reasons = []

        # 1. Client Identity & Historical Reputation
        if client_record:
            rep = client_record.reputation_score
            if rep < 70.0:
                rep_penalty = (70.0 - rep) * 0.8
                score += rep_penalty
                reasons.append(
                    f"Degraded client reputation ({rep:.1f}/100.0) with {client_record.error_count} "
                    f"prior errors across {client_record.total_requests} requests"
                )

        # 2. Endpoint Criticality & Sensitivity Multiplier
        if endpoint_record:
            if endpoint_record.risk_level == RiskLevel.CRITICAL:
                score += 35.0
                reasons.append(f"Target is a CRITICAL sensitive route ({endpoint_record.path_template})")
            elif endpoint_record.risk_level == RiskLevel.HIGH:
                score += 20.0
                reasons.append(f"Target is a HIGH-risk sensitive route ({endpoint_record.path_template})")

            # Check for unauthenticated access on an authenticated endpoint
            if endpoint_record.is_authenticated and event.auth_type.value == "none":
                score += 30.0
                reasons.append(f"Unauthenticated request to protected endpoint '{endpoint_record.path_template}'")

        # 3. Temporal Seasonality Mismatch
        if baseline and baseline.seasonality_hour_of_day:
            hour = event.timestamp.hour
            hour_prob = baseline.seasonality_hour_of_day.get(hour, 0.0)
            if hour_prob < 0.01 and baseline.sample_size >= 10:
                score += 25.0
                reasons.append(
                    f"Seasonality anomaly: request at hour {hour:02d}:00 UTC accounts for only "
                    f"{hour_prob*100:.2f}% of baseline endpoint volume"
                )

        score = min(100.0, score)
        is_anomaly = score >= 50.0

        return DetectorResult(
            detector_name=DetectorType.CONTEXTUAL.value,
            is_anomaly=is_anomaly,
            score=round(score, 1),
            confidence=0.8,
            reasons=reasons,
            metadata={"endpoint_risk": endpoint_record.risk_level.value if endpoint_record else "unknown"},
        )
