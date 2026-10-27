"""SentinelAPI Ensemble Anomaly Detection Engine.

Orchestrates Statistical, Machine Learning (Isolation Forest), Markov Sequence,
Contextual, and Signature detectors to generate an explainable composite risk score.
"""

import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List, Optional

from backend.app.schemas.anomaly import (
    AnomalyRecord,
    DetectorResult,
    ModelRetrainResult,
    SeverityLevel,
)
from backend.app.schemas.events import ApiEvent
from backend.app.services.baseline.batch_learner import batch_baseline_learner
from backend.app.services.baseline.online_updater import online_baseline_updater
from backend.app.services.detection.models.contextual import ContextualRiskScorer
from backend.app.services.detection.models.isolation_forest import IsolationForestDetector
from backend.app.services.detection.models.sequence_markov import MarkovSequenceDetector
from backend.app.services.detection.models.signature_detector import SignatureThreatDetector
from backend.app.services.detection.models.statistical import StatisticalDetector
from backend.app.services.inventory.inventory_service import inventory_service
from backend.app.services.inventory.path_normalizer import generate_endpoint_id, parameterize_path
from backend.app.services.storage.factory import get_storage
from backend.app.services.storage.repository import IStorageRepository

logger = logging.getLogger("sentinelapi.detection.engine")


class AnomalyDetectionEngine:
    """Enterprise-grade Ensemble Anomaly Scoring and Explainability Engine."""

    def __init__(
        self,
        storage: Optional[IStorageRepository] = None,
        anomaly_threshold: float = 40.0,
    ):
        self._storage = storage
        self.anomaly_threshold = anomaly_threshold
        self.version = "sentinel-engine-v1.0"

        # Instantiate specialized detectors
        self.statistical_detector = StatisticalDetector()
        self.ml_detector = IsolationForestDetector()
        self.sequence_detector = MarkovSequenceDetector()
        self.contextual_scorer = ContextualRiskScorer()
        self.signature_detector = SignatureThreatDetector()

        # Detector weights
        self.weights = {
            "signature": 0.35,
            "statistical": 0.25,
            "isolation_forest": 0.20,
            "sequence": 0.10,
            "contextual": 0.10,
        }

        # Cache of recently detected anomalies
        self._recent_anomalies: List[AnomalyRecord] = []
        self._lock = asyncio.Lock()

    async def _get_storage(self) -> IStorageRepository:
        if self._storage is not None:
            return self._storage
        return await get_storage()

    def score_event(self, event: ApiEvent) -> Optional[AnomalyRecord]:
        """Evaluates an ApiEvent across all detectors and computes an explainable composite risk score."""
        path_template = parameterize_path(event.path)
        ep_id = generate_endpoint_id(event.http_method, path_template)

        # 1. Fetch contextual metadata
        baseline = batch_baseline_learner.get_endpoint_baseline(ep_id) or online_baseline_updater.get_baseline(ep_id)
        ep_record = inventory_service.get_endpoint(ep_id)
        client_id = event.auth_identity or event.client_ip
        client_record = inventory_service.get_client(client_id)

        # Get previous endpoint from session
        sess_key = f"{event.client_ip}:{event.user_agent}"
        session = inventory_service._active_sessions.get(sess_key)
        prev_endpoint = session.endpoint_sequence[-2] if session and len(session.endpoint_sequence) >= 2 else None

        # 2. Run all specialized detectors
        res_sig = self.signature_detector.evaluate(event)
        res_stat = self.statistical_detector.evaluate(event, baseline)
        res_ml = self.ml_detector.evaluate(event)
        res_seq = self.sequence_detector.evaluate_transition(event, prev_endpoint)
        res_ctx = self.contextual_scorer.evaluate(event, ep_record, client_record, baseline)

        # 3. Compute Composite Weighted Risk Score (0-100)
        composite_score = (
            (res_sig.score * self.weights["signature"])
            + (res_stat.score * self.weights["statistical"])
            + (res_ml.score * self.weights["isolation_forest"])
            + (res_seq.score * self.weights["sequence"])
            + (res_ctx.score * self.weights["contextual"])
        )

        # Attack override: If direct signature exploit detected (SQLi, BOLA, scanner), elevate immediately
        if res_sig.score >= 75.0:
            composite_score = max(composite_score, res_sig.score)

        composite_score = min(100.0, max(0.0, round(composite_score, 1)))

        # 4. Compile Explainability Diagnostics
        all_reasons = []
        detector_scores = {
            "signature": res_sig.score,
            "statistical": res_stat.score,
            "isolation_forest": res_ml.score,
            "sequence": res_seq.score,
            "contextual": res_ctx.score,
        }

        for r in [res_sig, res_stat, res_ml, res_seq, res_ctx]:
            if r.score > 0 and r.reasons:
                all_reasons.extend(r.reasons)

        # Determine primary detector
        primary = max(detector_scores.items(), key=lambda x: x[1])[0]

        # 5. Determine Severity Level
        if composite_score >= 80.0:
            severity = SeverityLevel.CRITICAL
        elif composite_score >= 60.0:
            severity = SeverityLevel.HIGH
        elif composite_score >= 40.0:
            severity = SeverityLevel.MEDIUM
        elif composite_score >= 20.0:
            severity = SeverityLevel.LOW
        else:
            severity = SeverityLevel.INFO

        # Only generate an AnomalyRecord if score meets anomaly threshold
        if composite_score >= self.anomaly_threshold:
            anomaly = AnomalyRecord(
                event_id=event.event_id,
                timestamp=event.timestamp,
                endpoint_id=ep_id,
                http_method=event.http_method,
                path=event.path,
                client_ip=event.client_ip,
                client_id=client_id,
                risk_score=composite_score,
                severity=severity,
                primary_detector=primary,
                detector_scores=detector_scores,
                contributing_factors=all_reasons,
                event_snapshot=event.model_dump(mode="json"),
                model_version=self.version,
            )
            return anomaly

        return None

    async def process_and_persist(self, event: ApiEvent) -> Optional[AnomalyRecord]:
        """Scores an event, and if anomalous, persists it to storage and internal memory."""
        anomaly = self.score_event(event)
        if anomaly:
            async with self._lock:
                self._recent_anomalies.append(anomaly)
                if len(self._recent_anomalies) > 500:
                    self._recent_anomalies.pop(0)

            storage = await self._get_storage()
            if hasattr(storage, "store_anomaly"):
                await storage.store_anomaly(anomaly)

        return anomaly

    async def retrain_models(self) -> ModelRetrainResult:
        """Trains or retrains Isolation Forest and Markov sequence models from all historical real data."""
        start_ts = time.perf_counter()
        storage = await self._get_storage()

        # Query events for training
        events_data = await storage.query_events(limit=50000)
        if not events_data:
            return ModelRetrainResult(
                success=False,
                models_retrained=[],
                training_sample_size=0,
                training_duration_ms=0.0,
                new_version=self.version,
            )

        events_objs = []
        for row in events_data:
            try:
                events_objs.append(ApiEvent(**row))
            except Exception:
                pass

        # 1. Train Isolation Forest
        ml_trained = self.ml_detector.fit(events_objs)

        # 2. Train Markov Transition Model from Session Sequences
        sessions = inventory_service.list_sessions(limit=500)
        seqs = [s.endpoint_sequence for s in sessions if len(s.endpoint_sequence) >= 2]
        self.sequence_detector.train_from_sessions(seqs)

        elapsed_ms = (time.perf_counter() - start_ts) * 1000.0
        self.version = f"sentinel-engine-v1.{int(time.time())}"

        retrained_list = []
        if ml_trained:
            retrained_list.append("isolation_forest")
        if seqs:
            retrained_list.append("markov_sequence")

        return ModelRetrainResult(
            success=True,
            models_retrained=retrained_list,
            training_sample_size=len(events_objs),
            training_duration_ms=round(elapsed_ms, 2),
            new_version=self.version,
        )

    def list_anomalies(
        self,
        severity: Optional[str] = None,
        min_risk_score: Optional[float] = None,
        endpoint_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AnomalyRecord]:
        results = list(self._recent_anomalies)
        if severity:
            results = [a for a in results if a.severity.value.lower() == severity.lower()]
        if min_risk_score is not None:
            results = [a for a in results if a.risk_score >= min_risk_score]
        if endpoint_id:
            results = [a for a in results if a.endpoint_id == endpoint_id]

        results.sort(key=lambda a: a.timestamp, reverse=True)
        return results[offset : offset + limit]

    def get_anomaly(self, anomaly_id: str) -> Optional[AnomalyRecord]:
        for a in self._recent_anomalies:
            if a.anomaly_id == anomaly_id:
                return a
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Calculates live anomaly rates and distributions."""
        total = len(self._recent_anomalies)
        sev_counts: Dict[str, int] = {"info": 0, "low": 0, "medium": 0, "high": 0, "critical": 0}
        risk_dist = {"0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80-100": 0}

        ep_anomalies: Dict[str, int] = {}
        client_anomalies: Dict[str, int] = {}

        for a in self._recent_anomalies:
            sev_counts[a.severity.value] = sev_counts.get(a.severity.value, 0) + 1
            score = a.risk_score
            if score < 20:
                risk_dist["0-20"] += 1
            elif score < 40:
                risk_dist["20-40"] += 1
            elif score < 60:
                risk_dist["40-60"] += 1
            elif score < 80:
                risk_dist["60-80"] += 1
            else:
                risk_dist["80-100"] += 1

            ep_anomalies[a.path] = ep_anomalies.get(a.path, 0) + 1
            client_anomalies[a.client_ip] = client_anomalies.get(a.client_ip, 0) + 1

        top_eps = [
            {"path": k, "count": v}
            for k, v in sorted(ep_anomalies.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        top_clients = [
            {"client_ip": k, "count": v}
            for k, v in sorted(client_anomalies.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        return {
            "total_anomalies": total,
            "severity_breakdown": sev_counts,
            "risk_score_distribution": risk_dist,
            "top_anomalous_endpoints": top_eps,
            "top_suspicious_clients": top_clients,
            "recent_anomalies_count_1h": total,
        }


# Global anomaly detection engine singleton
anomaly_engine = AnomalyDetectionEngine()
