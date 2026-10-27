"""SentinelAPI Forensic Investigation Service.

Correlates raw logs, normalized telemetry, baseline deviations, ML detector scores,
client reputations, and Markov sequence paths for deep root-cause analysis.
"""

from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional
from backend.app.schemas.investigation import (
    ClientInvestigation,
    EndpointInvestigation,
    EventForensicTrace,
    SequenceFlowGraph,
    SequenceFlowLink,
    SequenceFlowNode,
)
from backend.app.services.baseline.batch_learner import batch_baseline_learner
from backend.app.services.detection.engine import anomaly_engine
from backend.app.services.inventory.inventory_service import inventory_service
from backend.app.services.policy.actions.ban_manager import ip_ban_manager
from backend.app.services.policy.actions.quarantine_manager import quarantine_manager
from backend.app.services.policy.engine import policy_engine
from backend.app.services.storage.factory import get_storage

logger = logging.getLogger("sentinelapi.investigation")


class InvestigationService:
    """Forensic investigation engine for root-cause analysis and behavioral profiling."""

    def __init__(self):
        self._storage = None

    async def _get_storage(self):
        if self._storage is not None:
            return self._storage
        return await get_storage()

    async def trace_event(self, event_id: str) -> Optional[EventForensicTrace]:
        """Performs full root-cause forensic correlation for a single API interaction."""
        storage = await self._get_storage()
        if not hasattr(storage, "_conn") or not storage._conn:
            return None

        # 1. Fetch normalized event
        cursor = storage._conn.execute("SELECT * FROM api_events WHERE event_id = ?", [event_id])
        row = cursor.fetchone()
        if not row:
            return None
        cols = [desc[0] for desc in cursor.description]
        event_dict = dict(zip(cols, row))

        # 2. Fetch raw log snippet if available
        raw_cursor = storage._conn.execute("SELECT raw_log FROM raw_events WHERE id = ?", [event_id])
        raw_row = raw_cursor.fetchone()
        raw_log = raw_row[0] if raw_row else event_dict.get("raw_log")

        # 3. Fetch anomaly scoring record
        anom_cursor = storage._conn.execute("SELECT * FROM anomalies WHERE event_id = ?", [event_id])
        anom_row = anom_cursor.fetchone()
        anom_details = None
        detector_scores = {}
        contributing_factors = []

        if anom_row:
            anom_cols = [desc[0] for desc in anom_cursor.description]
            anom_details = dict(zip(anom_cols, anom_row))
            if isinstance(anom_details.get("detector_scores"), str):
                try:
                    detector_scores = json.loads(anom_details["detector_scores"])
                except Exception:
                    pass
            if isinstance(anom_details.get("contributing_factors"), str):
                try:
                    contributing_factors = json.loads(anom_details["contributing_factors"])
                except Exception:
                    pass

        # 4. Fetch policy decision
        dec_cursor = storage._conn.execute("SELECT * FROM policy_decisions WHERE event_id = ?", [event_id])
        dec_row = dec_cursor.fetchone()
        policy_decision = None
        if dec_row:
            dec_cols = [desc[0] for desc in dec_cursor.description]
            policy_decision = dict(zip(dec_cols, dec_row))
            if isinstance(policy_decision.get("action_details"), str):
                try:
                    policy_decision["action_details"] = json.loads(policy_decision["action_details"])
                except Exception:
                    pass

        # 5. Client Reputation & Endpoint Baseline
        client_ip = event_dict.get("client_ip", "")
        client_rec = inventory_service.get_client(client_ip)
        reputation = client_rec.reputation_score if client_rec else 100.0

        endpoint_id = event_dict.get("path", "")
        baseline = batch_baseline_learner.get_baseline(endpoint_id)
        baseline_dict = baseline.model_dump(mode="json") if baseline else None

        return EventForensicTrace(
            event_id=event_id,
            timestamp=event_dict.get("timestamp"),
            raw_log=raw_log,
            normalized_event=event_dict,
            anomaly_details=anom_details,
            detector_scores=detector_scores,
            contributing_factors=contributing_factors,
            policy_decision=policy_decision,
            client_reputation=reputation,
            endpoint_baseline=baseline_dict,
        )

    async def investigate_client(self, client_ip: str) -> ClientInvestigation:
        """Constructs a comprehensive behavioral investigation dossier on a client."""
        client_rec = inventory_service.get_client(client_ip)
        is_banned, ban_entry = await ip_ban_manager.is_banned(client_ip)
        is_q, q_entry = await quarantine_manager.is_quarantined(client_ip)

        ban_details = ban_entry.model_dump(mode="json") if ban_entry else None

        # Fetch anomalies for this IP
        storage = await self._get_storage()
        past_anomalies = []
        if hasattr(storage, "_conn") and storage._conn:
            try:
                cursor = storage._conn.execute(
                    "SELECT * FROM anomalies WHERE client_ip = ? ORDER BY timestamp DESC LIMIT 20",
                    [client_ip]
                )
                cols = [desc[0] for desc in cursor.description]
                for r in cursor.fetchall():
                    past_anomalies.append(dict(zip(cols, r)))
            except Exception as e:
                logger.error(f"Error querying anomalies for client {client_ip}: {e}")

        # Fetch active sessions for this client
        recent_sessions = []
        for sess in inventory_service.list_sessions(limit=100):
            if sess.client_ip == client_ip:
                recent_sessions.append(sess.model_dump(mode="json"))

        reputation = client_rec.reputation_score if client_rec else 100.0
        total_reqs = client_rec.total_requests if client_rec else len(past_anomalies)
        error_count = client_rec.error_count if client_rec else 0
        observed = client_rec.observed_endpoints if client_rec else []

        return ClientInvestigation(
            client_ip=client_ip,
            reputation_score=reputation,
            total_requests=total_reqs,
            error_count=error_count,
            distinct_endpoints_count=len(observed),
            observed_endpoints=observed,
            is_banned=is_banned,
            ban_details=ban_details,
            is_quarantined=is_q,
            past_anomalies_count=len(past_anomalies),
            past_anomalies=past_anomalies,
            recent_sessions=recent_sessions,
        )

    async def investigate_endpoint(self, endpoint_id: str) -> Optional[EndpointInvestigation]:
        """Provides full deviation context and forensic status for an endpoint."""
        ep_rec = inventory_service.get_endpoint(endpoint_id)
        if not ep_rec:
            # Try searching by path
            for e in inventory_service.list_endpoints():
                if e.endpoint_id == endpoint_id or e.path_template == endpoint_id:
                    ep_rec = e
                    break

        if not ep_rec:
            return None

        baseline = batch_baseline_learner.get_baseline(ep_rec.endpoint_id)
        base_dict = baseline.model_dump(mode="json") if baseline else None

        # Fetch recent anomalies targeting this endpoint
        storage = await self._get_storage()
        anoms = []
        if hasattr(storage, "_conn") and storage._conn:
            try:
                cursor = storage._conn.execute(
                    "SELECT * FROM anomalies WHERE endpoint_id = ? ORDER BY timestamp DESC LIMIT 20",
                    [ep_rec.endpoint_id]
                )
                cols = [desc[0] for desc in cursor.description]
                for r in cursor.fetchall():
                    anoms.append(dict(zip(cols, r)))
            except Exception as e:
                logger.error(f"Error querying endpoint anomalies: {e}")

        status_dist = {str(k): v for k, v in ep_rec.status_codes.items()}

        return EndpointInvestigation(
            endpoint_id=ep_rec.endpoint_id,
            http_method=ep_rec.http_method,
            path_template=ep_rec.path_template,
            risk_level=ep_rec.risk_level.value,
            total_calls=ep_rec.call_count,
            status_distribution=status_dist,
            baseline_metrics=base_dict,
            observed_parameters=dict(ep_rec.parameters),
            recent_anomalies_count=len(anoms),
            recent_anomalies=anoms,
        )

    async def get_sequence_flow_graph(self) -> SequenceFlowGraph:
        """Constructs call-chain transition graph from observed sessions and Markov models."""
        sessions = inventory_service.list_sessions(limit=100)
        transition_counts: Dict[str, Dict[str, int]] = {}
        node_counts: Dict[str, int] = {}

        for sess in sessions:
            seq = sess.endpoint_sequence
            for i in range(len(seq)):
                curr_ep = seq[i]
                node_counts[curr_ep] = node_counts.get(curr_ep, 0) + 1
                if i < len(seq) - 1:
                    next_ep = seq[i + 1]
                    if curr_ep not in transition_counts:
                        transition_counts[curr_ep] = {}
                    transition_counts[curr_ep][next_ep] = transition_counts[curr_ep].get(next_ep, 0) + 1

        # Build nodes
        nodes = []
        for ep_path, count in node_counts.items():
            ep_rec = None
            for e in inventory_service.list_endpoints():
                if e.path_template == ep_path:
                    ep_rec = e
                    break
            risk = ep_rec.risk_level.value if ep_rec else "low"
            nodes.append(SequenceFlowNode(
                id=ep_path,
                label=ep_path,
                call_count=count,
                risk_level=risk,
            ))

        # Build links
        links = []
        for src, targets in transition_counts.items():
            total_out = sum(targets.values())
            for tgt, weight in targets.items():
                prob = round(weight / total_out, 3) if total_out > 0 else 1.0
                links.append(SequenceFlowLink(
                    source=src,
                    target=tgt,
                    value=weight,
                    probability=prob,
                ))

        if not nodes:
            # Fallback sample node from inventory
            for ep in inventory_service.list_endpoints(limit=5):
                nodes.append(SequenceFlowNode(
                    id=ep.path_template,
                    label=ep.path_template,
                    call_count=ep.call_count,
                    risk_level=ep.risk_level.value,
                ))

        return SequenceFlowGraph(nodes=nodes, links=links)


# Global singleton instance
investigation_service = InvestigationService()
