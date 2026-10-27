"""Unsupervised Machine Learning Anomaly Detector (Isolation Forest).

Extracts multivariate feature vectors from real API traffic events and identifies
multi-dimensional outliers using tree-based isolation space partitioning.
"""

import logging
from typing import Any, Dict, List, Optional
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from backend.app.schemas.anomaly import DetectorResult, DetectorType
from backend.app.schemas.events import ApiEvent

logger = logging.getLogger("sentinelapi.detection.ml")


class IsolationForestDetector:
    """Multivariate outlier detector based on scikit-learn Isolation Forest."""

    def __init__(self, contamination: float = 0.05, n_estimators: int = 100):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.model: Optional[IsolationForest] = None
        self.scaler = StandardScaler()
        self.is_trained: bool = False
        self.sample_size: int = 0
        self.model_version: str = "iforest-v1.0"

    def extract_features(self, event: ApiEvent) -> np.ndarray:
        """Converts an ApiEvent into a numerical feature vector."""
        return np.array([
            float(event.latency_ms),
            float(event.request_size_bytes),
            float(event.response_size_bytes),
            1.0 if event.status_code >= 400 else 0.0,
            float(event.timestamp.hour),
            float(event.timestamp.weekday()),
        ], dtype=np.float64)

    def fit(self, events: List[ApiEvent]) -> bool:
        """Trains the Isolation Forest model on historical real events."""
        if len(events) < 10:
            logger.warning(f"Insufficient events ({len(events)}) to train Isolation Forest. Minimum 10 required.")
            return False

        feature_matrix = np.array([self.extract_features(e) for e in events])
        scaled_features = self.scaler.fit_transform(feature_matrix)

        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=42,
            n_jobs=-1,
        )
        self.model.fit(scaled_features)
        self.is_trained = True
        self.sample_size = len(events)
        logger.info(f"Isolation Forest trained successfully on {len(events)} real events.")
        return True

    def evaluate(self, event: ApiEvent) -> DetectorResult:
        if not self.is_trained or not self.model:
            return DetectorResult(
                detector_name=DetectorType.ISOLATION_FOREST.value,
                is_anomaly=False,
                score=0.0,
                confidence=0.2,
                reasons=[],
            )

        features = self.extract_features(event).reshape(1, -1)
        scaled = self.scaler.transform(features)

        # decision_function yields < 0 for outliers, > 0 for inliers
        decision = float(self.model.decision_function(scaled)[0])
        pred = int(self.model.predict(scaled)[0])  # -1 for anomaly, 1 for inlier

        # Normalize decision score to 0..100 risk scale
        # Typical decision scores range from -0.35 to +0.25
        if decision < 0 or pred == -1:
            # Outlier: scale from 50 to 100
            risk_score = min(100.0, 50.0 + (max(0.02, abs(decision)) * 150.0))
            is_anomaly = True
            reasons = [
                f"Multivariate isolation outlier: score {decision:.3f} indicates abnormal feature combination "
                f"(latency={event.latency_ms}ms, req={event.request_size_bytes}B, status={event.status_code})"
            ]
        else:
            # Inlier: scale from 0 to 45
            risk_score = max(0.0, 45.0 - (decision * 150.0))
            is_anomaly = False
            reasons = []

        return DetectorResult(
            detector_name=DetectorType.ISOLATION_FOREST.value,
            is_anomaly=is_anomaly,
            score=round(risk_score, 1),
            confidence=0.85,
            reasons=reasons,
            metadata={"decision_score": round(decision, 4), "prediction": pred},
        )
