"""Sequence Anomaly Detector via First-Order Markov Transition Chains.

Learns the probability distribution of transitions between consecutive API endpoints
in client sessions and flags unnatural, skipped, or unauthorized call paths.
"""

from collections import defaultdict
import logging
from typing import Dict, List, Optional
from backend.app.schemas.anomaly import DetectorResult, DetectorType
from backend.app.schemas.events import ApiEvent
from backend.app.services.inventory.path_normalizer import parameterize_path

logger = logging.getLogger("sentinelapi.detection.sequence")


class MarkovSequenceDetector:
    """Detects sequential anomalies and unauthorized call sequences using transition probabilities."""

    def __init__(self, rare_transition_threshold: float = 0.02, auto_load: bool = True):
        self.rare_transition_threshold = rare_transition_threshold
        # transition_counts[prev_endpoint][next_endpoint] = count
        self.transition_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.state_totals: Dict[str, int] = defaultdict(int)
        self.is_trained: bool = False

        if auto_load:
            self._load_from_disk()

    def _load_from_disk(self) -> bool:
        from pathlib import Path
        import json
        base = Path(__file__).resolve().parents[5]
        model_p = base / "models" / "markov_transitions.json"
        if model_p.exists():
            try:
                data = json.loads(model_p.read_text(encoding="utf-8"))
                for src, dsts in data.get("transitions", {}).items():
                    for dst, count in dsts.items():
                        self.transition_counts[src][dst] = count
                for src, total in data.get("state_totals", {}).items():
                    self.state_totals[src] = total
                self.is_trained = True
                logger.info(f"Loaded pre-trained Markov Transitions model ({len(self.transition_counts)} states).")
                return True
            except Exception as e:
                logger.warning(f"Could not load pre-trained Markov model: {e}")
        return False

    def train_from_sessions(self, sessions_sequences: List[List[str]]) -> None:
        """Learns transition probabilities from historical session sequences."""
        total_transitions = 0
        for seq in sessions_sequences:
            if len(seq) < 2:
                continue
            for i in range(len(seq) - 1):
                src = seq[i]
                dst = seq[i + 1]
                self.transition_counts[src][dst] += 1
                self.state_totals[src] += 1
                total_transitions += 1

        if total_transitions > 0:
            self.is_trained = True
            logger.info(
                f"Markov Chain trained on {len(sessions_sequences)} sessions ({total_transitions} transitions, "
                f"{len(self.transition_counts)} states)."
            )

    def get_transition_probability(self, src: str, dst: str) -> float:
        total = self.state_totals.get(src, 0)
        if total == 0:
            return 0.0
        return self.transition_counts[src].get(dst, 0) / total

    def evaluate_transition(
        self, current_event: ApiEvent, previous_endpoint: Optional[str]
    ) -> DetectorResult:
        if not self.is_trained or not previous_endpoint:
            return DetectorResult(
                detector_name=DetectorType.MARKOV_SEQUENCE.value,
                is_anomaly=False,
                score=0.0,
                confidence=0.3,
                reasons=[],
            )

        curr_template = parameterize_path(current_event.path)
        prev_template = previous_endpoint

        # Self-loops on same endpoint (e.g. pagination or polling) are generally normal
        if curr_template == prev_template:
            return DetectorResult(
                detector_name=DetectorType.MARKOV_SEQUENCE.value,
                is_anomaly=False,
                score=0.0,
                confidence=0.8,
                reasons=[],
            )

        prob = self.get_transition_probability(prev_template, curr_template)
        reasons = []
        score = 0.0
        is_anomaly = False

        if prob == 0.0:
            # Transition never observed in historical baseline
            score = 65.0
            is_anomaly = True
            reasons.append(
                f"Unprecedented sequence transition: '{prev_template}' -> '{curr_template}' "
                f"has never been observed in baseline traffic."
            )
        elif prob < self.rare_transition_threshold:
            # Unusually rare sequence
            score = 45.0
            is_anomaly = True
            reasons.append(
                f"Unusual workflow transition: '{prev_template}' -> '{curr_template}' "
                f"probability is {prob*100:.2f}% (threshold <= {self.rare_transition_threshold*100:.1f}%)"
            )

        return DetectorResult(
            detector_name=DetectorType.MARKOV_SEQUENCE.value,
            is_anomaly=is_anomaly,
            score=round(score, 1),
            confidence=0.8,
            reasons=reasons,
            metadata={"transition": f"{prev_template} -> {curr_template}", "probability": round(prob, 4)},
        )
