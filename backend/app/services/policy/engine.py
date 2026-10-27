"""SentinelAPI Adaptive Policy Evaluation Engine.

Evaluates incoming API events and detected anomalies against active Policy-as-Code rules,
determines adaptive responses (allow, throttle, challenge, block, quarantine),
executes protective actions, dispatches webhooks and SIEM logs, and records immutable audit trails.
"""

import asyncio
from datetime import datetime, timezone
import ipaddress
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
from backend.app.schemas.anomaly import AnomalyRecord, SeverityLevel
from backend.app.schemas.events import ApiEvent, LogSource
from backend.app.schemas.policy import (
    BlocklistEntry,
    PolicyAction,
    PolicyCondition,
    PolicyDecision,
    PolicyEvaluationRequest,
    PolicyEvaluationResponse,
    PolicyRule,
    PolicyStats,
)
from backend.app.services.inventory.inventory_service import inventory_service
from backend.app.services.policy.actions.ban_manager import ip_ban_manager
from backend.app.services.policy.actions.quarantine_manager import quarantine_manager
from backend.app.services.policy.actions.siem_forwarder import siem_forwarder
from backend.app.services.policy.actions.throttler import adaptive_throttler
from backend.app.services.policy.actions.webhook_dispatcher import webhook_dispatcher
from backend.app.services.policy.loader import PolicyLoader

logger = logging.getLogger("sentinelapi.policy.engine")


class PolicyEngine:
    """Evaluates events against security policies and executes closed-loop adaptive protection."""

    def __init__(self, policy_file_path: Optional[str] = None):
        self.policy_file_path = policy_file_path or str(
            Path(__file__).resolve().parents[4] / "policies" / "default_policies.yaml"
        )
        self._rules: List[PolicyRule] = []
        self._decisions_history: List[PolicyDecision] = []
        self._total_decisions_evaluated = 0
        self._actions_breakdown: Dict[str, int] = {
            PolicyAction.ALLOW.value: 0,
            PolicyAction.THROTTLE.value: 0,
            PolicyAction.CHALLENGE.value: 0,
            PolicyAction.BLOCK.value: 0,
            PolicyAction.QUARANTINE.value: 0,
        }
        self._lock = asyncio.Lock()
        self._initialized = False
        self._storage = None

    async def _get_storage(self):
        if self._storage is not None:
            return self._storage
        from backend.app.services.storage.factory import get_storage
        return await get_storage()

    async def initialize(self) -> None:
        """Loads default policies from configuration file or storage."""
        if self._initialized:
            return

        async with self._lock:
            if not self._rules:
                # 1. Try loading from YAML file
                p = Path(self.policy_file_path)
                if p.exists():
                    self._rules = PolicyLoader.load_from_yaml_file(str(p))
                else:
                    logger.warning(f"Default policies file not found at '{self.policy_file_path}'. Initializing baseline rule.")
                    self._rules = [
                        PolicyRule(
                            policy_id="pol_default_allow",
                            name="Default Allow",
                            description="Fallback allow rule",
                            is_enabled=True,
                            priority=1000,
                            action=PolicyAction.ALLOW,
                        )
                    ]
            self._initialized = True
            logger.info(f"PolicyEngine initialized with {len(self._rules)} active rules.")

    def _matches_ip_cidr(self, client_ip: str, cidr_or_ip: Optional[str]) -> bool:
        """Checks if a client IP matches an IP address or CIDR range."""
        if not cidr_or_ip:
            return True
        try:
            target_ip = ipaddress.ip_address(client_ip)
            net = ipaddress.ip_network(cidr_or_ip, strict=False)
            return target_ip in net
        except ValueError:
            return client_ip == cidr_or_ip

    def _matches_endpoint(self, path: str, pattern: Optional[str]) -> bool:
        """Matches path against regex pattern."""
        if not pattern:
            return True
        try:
            return bool(re.search(pattern, path, re.IGNORECASE))
        except re.error:
            # Fallback simple string match
            return pattern.lower() in path.lower()

    def _matches_attack_types(
        self,
        rule_attack_types: Optional[List[str]],
        anomaly: Optional[AnomalyRecord],
        event: ApiEvent,
    ) -> bool:
        """Evaluates whether an event/anomaly matches specific attack types."""
        if not rule_attack_types:
            return True
        if not anomaly:
            return False

        detected_clues = []
        # Add contributing factors
        for f in anomaly.contributing_factors:
            detected_clues.append(f.lower())

        # Add event path / query indicators
        detected_clues.append(event.path.lower())
        if isinstance(event.query_params, dict):
            for k, v in event.query_params.items():
                detected_clues.append(f"{k}={v}".lower())
        else:
            detected_clues.append(str(event.query_params).lower())
        detected_clues.append(event.user_agent.lower())

        for req_type in rule_attack_types:
            req_lower = req_type.lower()
            if req_lower in ["sqli", "sql_injection"]:
                if any("sql" in c or "union select" in c or "1=1" in c or "' or '" in c for c in detected_clues):
                    return True
            elif req_lower in ["path_traversal", "traversal"]:
                if any("traversal" in c or "../" in c or "etc/passwd" in c for c in detected_clues):
                    return True
            elif req_lower in ["vulnerability_scanner", "scanner"]:
                if any("scanner" in c or "nikto" in c or "sqlmap" in c or "acunetix" in c for c in detected_clues):
                    return True
            elif req_lower in ["brute_force", "credential_stuffing"]:
                if any("brute" in c or "stuffing" in c or ("auth" in event.path.lower() and event.status_code in [401, 429]) for c in detected_clues):
                    return True
            elif req_lower in ["bola_idor", "bola", "idor"]:
                if any("bola" in c or "idor" in c or (event.status_code == 403 and "/users/" in event.path) for c in detected_clues):
                    return True
            else:
                if any(req_lower in c for c in detected_clues):
                    return True

        return False

    def _evaluate_rule(
        self,
        rule: PolicyRule,
        event: ApiEvent,
        anomaly: Optional[AnomalyRecord],
        client_reputation: Optional[float],
    ) -> Tuple[bool, str]:
        """Evaluates if an individual rule matches."""
        cond = rule.conditions
        risk_score = anomaly.risk_score if anomaly else 0.0
        severity = anomaly.severity if anomaly else SeverityLevel.INFO

        # 1. Endpoint match
        if cond.endpoint_pattern and not self._matches_endpoint(event.path, cond.endpoint_pattern):
            return False, "Endpoint pattern did not match"

        # 2. HTTP method
        if cond.http_methods:
            if event.http_method.upper() not in [m.upper() for m in cond.http_methods]:
                return False, "HTTP method did not match"

        # 3. Client IP / CIDR
        if cond.client_ip_cidr and not self._matches_ip_cidr(event.client_ip, cond.client_ip_cidr):
            return False, "Client IP CIDR did not match"

        # 4. Auth type
        if cond.auth_types and event.auth_type.value not in cond.auth_types:
            return False, "Auth type did not match"

        # 5. Risk score range
        if cond.min_risk_score is not None and risk_score < cond.min_risk_score:
            return False, f"Risk score ({risk_score}) below min threshold ({cond.min_risk_score})"
        if cond.max_risk_score is not None and risk_score > cond.max_risk_score:
            return False, f"Risk score ({risk_score}) above max threshold ({cond.max_risk_score})"

        # 6. Severity
        if cond.severities and severity not in cond.severities:
            return False, f"Severity ({severity.value}) not in allowed severities"

        # 7. Attack types
        if cond.attack_types and not self._matches_attack_types(cond.attack_types, anomaly, event):
            return False, "Attack category did not match"

        # 8. Client reputation
        if cond.max_client_reputation is not None:
            rep = client_reputation if client_reputation is not None else 100.0
            if rep > cond.max_client_reputation:
                return False, f"Client reputation ({rep}) exceeds max limit ({cond.max_client_reputation})"

        return True, "All rule conditions satisfied"

    async def evaluate(
        self,
        event: ApiEvent,
        anomaly: Optional[AnomalyRecord] = None,
    ) -> PolicyDecision:
        """Evaluates an event and anomaly against policies and returns the decision without executing side effects."""
        if not self._initialized:
            await self.initialize()

        client_ip = event.client_ip
        risk_score = anomaly.risk_score if anomaly else 0.0
        severity = anomaly.severity if anomaly else SeverityLevel.INFO

        # Pre-check 1: Is IP already on active blocklist?
        is_banned, ban_entry = await ip_ban_manager.is_banned(client_ip)
        if is_banned and ban_entry:
            expires_str = ban_entry.expires_at.isoformat() if ban_entry.expires_at else "permanent"
            return PolicyDecision(
                event_id=event.event_id,
                timestamp=event.timestamp,
                client_ip=client_ip,
                endpoint=event.path,
                http_method=event.http_method,
                risk_score=risk_score,
                severity=severity,
                action_taken=PolicyAction.BLOCK,
                matched_policy_id="active_ip_ban",
                matched_policy_name="Enforced IP Blocklist",
                reason=f"IP {client_ip} is currently banned on blocklist ({ban_entry.reason}). Expires at {expires_str}.",
                action_details={"ban_active": True, "expires_at": expires_str},
            )

        # Pre-check 2: Is IP in quarantine?
        is_quarantined, q_entry = await quarantine_manager.is_quarantined(client_ip)
        if is_quarantined and q_entry:
            return PolicyDecision(
                event_id=event.event_id,
                timestamp=event.timestamp,
                client_ip=client_ip,
                endpoint=event.path,
                http_method=event.http_method,
                risk_score=risk_score,
                severity=severity,
                action_taken=PolicyAction.QUARANTINE,
                matched_policy_id="active_quarantine",
                matched_policy_name="Active Quarantine Isolation",
                reason=f"Client IP {client_ip} is currently quarantined ({q_entry.reason}).",
                action_details={"quarantined": True},
            )

        # Retrieve client reputation if available
        client_rec = inventory_service.get_client(client_ip)
        reputation = client_rec.reputation_score if client_rec else None

        # Iterate active policies by priority
        async with self._lock:
            active_rules = [r for r in self._rules if r.is_enabled]

        for rule in active_rules:
            matched, reason_detail = self._evaluate_rule(rule, event, anomaly, reputation)
            if matched:
                reason = f"Policy '{rule.name}' matched: {rule.description}"
                if anomaly and anomaly.contributing_factors:
                    reason += f" Factors: {', '.join(anomaly.contributing_factors[:2])}"

                return PolicyDecision(
                    event_id=event.event_id,
                    timestamp=event.timestamp,
                    client_ip=client_ip,
                    endpoint=event.path,
                    http_method=event.http_method,
                    risk_score=risk_score,
                    severity=severity,
                    action_taken=rule.action,
                    matched_policy_id=rule.policy_id,
                    matched_policy_name=rule.name,
                    reason=reason,
                    action_details=dict(rule.action_params),
                )

        # Fallback allow
        return PolicyDecision(
            event_id=event.event_id,
            timestamp=event.timestamp,
            client_ip=client_ip,
            endpoint=event.path,
            http_method=event.http_method,
            risk_score=risk_score,
            severity=severity,
            action_taken=PolicyAction.ALLOW,
            matched_policy_id="default_allow",
            matched_policy_name="Default Allow Policy",
            reason="No restrictive policy conditions matched.",
            action_details={},
        )

    async def evaluate_and_enforce(
        self,
        event: ApiEvent,
        anomaly: Optional[AnomalyRecord] = None,
    ) -> PolicyDecision:
        """Evaluates policy and executes corresponding response actions (ban, throttle, webhook, SIEM)."""
        decision = await self.evaluate(event, anomaly)

        # 1. Execute Protective Action
        if decision.action_taken == PolicyAction.BLOCK:
            duration = decision.action_details.get("ban_duration_seconds", 3600)
            ban_entry = await ip_ban_manager.ban_ip(
                ip=decision.client_ip,
                duration_seconds=duration,
                reason=decision.reason,
                policy_id=decision.matched_policy_id,
            )
            decision.action_details["ban_expires_at"] = (
                ban_entry.expires_at.isoformat() if ban_entry.expires_at else "permanent"
            )

        elif decision.action_taken == PolicyAction.THROTTLE:
            rpm = decision.action_details.get("rate_limit_rpm", 5)
            is_throttled, retry_after, count = await adaptive_throttler.record_and_check(
                key=decision.client_ip,
                limit_rpm=rpm,
            )
            decision.action_details["current_count"] = count
            decision.action_details["retry_after_seconds"] = retry_after
            decision.action_details["is_throttled"] = is_throttled

        elif decision.action_taken == PolicyAction.QUARANTINE:
            await quarantine_manager.quarantine(
                client_ip=decision.client_ip,
                client_id=event.client_id,
                reason=decision.reason,
                policy_id=decision.matched_policy_id,
            )

        # 2. Forward to SIEM (CEF / Syslog)
        siem_forwarder.forward(decision)

        # 3. Webhook Dispatch (if configured or enabled)
        if decision.action_details.get("notify_webhook") or decision.action_taken in [
            PolicyAction.BLOCK,
            PolicyAction.QUARANTINE,
        ]:
            asyncio.create_task(webhook_dispatcher.dispatch(decision))

        # 4. Record to Audit Log & In-memory History
        async with self._lock:
            self._total_decisions_evaluated += 1
            act_val = decision.action_taken.value
            self._actions_breakdown[act_val] = self._actions_breakdown.get(act_val, 0) + 1
            self._decisions_history.append(decision)
            if len(self._decisions_history) > 1000:
                self._decisions_history.pop(0)

        # 5. Persist to Storage
        storage = await self._get_storage()
        if hasattr(storage, "store_policy_decision"):
            await storage.store_policy_decision(decision)

        return decision

    async def add_or_update_rule(self, rule: PolicyRule) -> PolicyRule:
        """Adds or updates a policy rule."""
        async with self._lock:
            # Check if exists
            updated = False
            for idx, r in enumerate(self._rules):
                if r.policy_id == rule.policy_id:
                    self._rules[idx] = rule
                    updated = True
                    break
            if not updated:
                self._rules.append(rule)

            self._rules.sort(key=lambda r: r.priority)

        # Persist if storage supports it
        storage = await self._get_storage()
        if hasattr(storage, "store_policy"):
            await storage.store_policy(rule)

        return rule

    async def delete_rule(self, policy_id: str) -> bool:
        """Deletes a policy rule by ID."""
        async with self._lock:
            initial_count = len(self._rules)
            self._rules = [r for r in self._rules if r.policy_id != policy_id]
            deleted = len(self._rules) < initial_count

        if deleted:
            storage = await self._get_storage()
            if hasattr(storage, "delete_policy"):
                await storage.delete_policy(policy_id)

        return deleted

    async def get_rules(self, enabled_only: bool = False) -> List[PolicyRule]:
        """Returns all loaded policy rules."""
        if not self._initialized:
            await self.initialize()
        async with self._lock:
            if enabled_only:
                return [r for r in self._rules if r.is_enabled]
            return list(self._rules)

    async def get_decisions(
        self,
        action: Optional[str] = None,
        client_ip: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[PolicyDecision]:
        """Queries stored or in-memory policy audit decisions."""
        storage = await self._get_storage()
        if hasattr(storage, "get_policy_decisions"):
            persisted = await storage.get_policy_decisions(
                limit=limit,
                offset=offset,
                action=action,
                client_ip=client_ip,
            )
            if persisted:
                return [PolicyDecision(**d) if isinstance(d, dict) else d for d in persisted]

        # In-memory fallback
        async with self._lock:
            filtered = list(self._decisions_history)
            if action:
                filtered = [d for d in filtered if d.action_taken.value == action.lower()]
            if client_ip:
                filtered = [d for d in filtered if d.client_ip == client_ip]

            filtered.reverse()  # most recent first
            return filtered[offset : offset + limit]

    async def dry_run_evaluate(self, req: PolicyEvaluationRequest) -> PolicyEvaluationResponse:
        """Executes a dry-run evaluation on synthetic test criteria."""
        if not self._initialized:
            await self.initialize()

        dummy_event = ApiEvent(
            timestamp=datetime.now(timezone.utc),
            source_type=LogSource.AUTO,
            http_method=req.http_method,
            path=req.endpoint,
            raw_path=req.endpoint,
            status_code=200,
            latency_ms=10.0,
            client_ip=req.client_ip,
        )

        dummy_anomaly = None
        if req.risk_score > 0 or req.attack_types:
            dummy_anomaly = AnomalyRecord(
                event_id=dummy_event.event_id,
                endpoint_id="dry_run",
                http_method=req.http_method,
                path=req.endpoint,
                client_ip=req.client_ip,
                client_id="dry_run_client",
                risk_score=req.risk_score,
                severity=req.severity,
                contributing_factors=req.attack_types,
            )

        decision = await self.evaluate(dummy_event, dummy_anomaly)

        return PolicyEvaluationResponse(
            action=decision.action_taken,
            matched_policy_id=decision.matched_policy_id,
            matched_policy_name=decision.matched_policy_name,
            reason=decision.reason,
            action_params=decision.action_details,
            applied_in_dry_run=True,
        )

    async def get_stats(self) -> PolicyStats:
        """Returns comprehensive operational statistics."""
        if not self._initialized:
            await self.initialize()

        rules = await self.get_rules()
        enabled_count = sum(1 for r in rules if r.is_enabled)
        banned_count = await ip_ban_manager.count_active()
        quarantined_count = await quarantine_manager.count_active()
        webhook_stats = webhook_dispatcher.get_stats()
        siem_stats = siem_forwarder.get_stats()

        async with self._lock:
            return PolicyStats(
                total_policies=len(rules),
                enabled_policies=enabled_count,
                total_decisions_evaluated=self._total_decisions_evaluated,
                actions_breakdown=dict(self._actions_breakdown),
                active_banned_ips_count=banned_count,
                active_quarantined_count=quarantined_count,
                total_webhooks_dispatched=webhook_stats.get("total_webhooks_dispatched", 0),
                total_siem_events_forwarded=siem_stats.get("total_siem_events_forwarded", 0),
            )

    async def reset(self) -> None:
        """Resets engine state and clears all actions (for tests)."""
        async with self._lock:
            self._decisions_history.clear()
            self._total_decisions_evaluated = 0
            self._actions_breakdown = {k: 0 for k in self._actions_breakdown}
        await ip_ban_manager.clear_all()
        await quarantine_manager.clear_all()
        await adaptive_throttler.reset()
        webhook_dispatcher.clear_history()
        siem_forwarder.clear()


# Global singleton instance
policy_engine = PolicyEngine()
