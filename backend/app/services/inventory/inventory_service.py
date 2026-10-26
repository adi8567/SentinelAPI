"""SentinelAPI Inventory Discovery Service.

Discovers and updates Endpoints, Clients, and Sessions in real time and batch modes.
"""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from backend.app.schemas.events import ApiEvent, AuthType
from backend.app.schemas.inventory import (
    ClientRecord,
    ClientType,
    EndpointRecord,
    InventorySummary,
    ParameterInfo,
    SessionRecord,
)
from backend.app.services.inventory.path_normalizer import (
    evaluate_endpoint_risk,
    generate_endpoint_id,
    parameterize_path,
)
from backend.app.services.storage.factory import get_storage
from backend.app.services.storage.repository import IStorageRepository

logger = logging.getLogger("sentinelapi.inventory")


class InventoryService:
    """Manages API asset catalog discovery and client tracking."""

    def __init__(self, storage: Optional[IStorageRepository] = None):
        self._storage = storage
        self._lock = asyncio.Lock()

        # In-memory fast cache for real-time tracking
        self._endpoints_cache: Dict[str, EndpointRecord] = {}
        self._clients_cache: Dict[str, ClientRecord] = {}
        self._active_sessions: Dict[str, SessionRecord] = {}

    async def _get_storage(self) -> IStorageRepository:
        if self._storage is None:
            self._storage = await get_storage()
        return self._storage

    async def process_event(self, event: ApiEvent) -> EndpointRecord:
        """Processes an incoming ApiEvent, updating endpoint inventory, client profile, and session."""
        path_template = parameterize_path(event.path)
        ep_id = generate_endpoint_id(event.http_method, path_template)

        async with self._lock:
            # 1. Update Endpoint Record
            if ep_id in self._endpoints_cache:
                ep = self._endpoints_cache[ep_id]
                ep.last_seen_at = event.timestamp
                ep.call_count += 1
                if event.path not in ep.sample_raw_paths and len(ep.sample_raw_paths) < 10:
                    ep.sample_raw_paths.append(event.path)
            else:
                risk, tags = evaluate_endpoint_risk(event.http_method, path_template)
                ep = EndpointRecord(
                    endpoint_id=ep_id,
                    http_method=event.http_method,
                    path_template=path_template,
                    sample_raw_paths=[event.path],
                    first_seen_at=event.timestamp,
                    last_seen_at=event.timestamp,
                    call_count=1,
                    risk_level=risk,
                    tags=tags,
                )
                self._endpoints_cache[ep_id] = ep

            # Track status code
            status_str = str(event.status_code)
            ep.status_codes_observed[status_str] = ep.status_codes_observed.get(status_str, 0) + 1

            # Track Auth
            if event.auth_type != AuthType.NONE:
                ep.is_authenticated = True
                auth_str = event.auth_type.value
                if auth_str not in ep.auth_types_observed:
                    ep.auth_types_observed.append(auth_str)

            # Track Query Parameters
            for p_name, p_val in event.query_params.items():
                if p_name not in ep.parameters:
                    ep.parameters[p_name] = ParameterInfo(name=p_name, location="query")
                param_info = ep.parameters[p_name]
                val_type = "int" if str(p_val).isdigit() else "str"
                if val_type not in param_info.observed_types:
                    param_info.observed_types.append(val_type)
                if str(p_val) not in param_info.sample_values and len(param_info.sample_values) < 5:
                    param_info.sample_values.append(str(p_val))

            # 2. Update Client Record
            client_id = event.auth_identity or event.client_ip
            client_type = ClientType.USER if event.auth_identity else ClientType.IP
            if client_id in self._clients_cache:
                cl = self._clients_cache[client_id]
                cl.last_seen_at = event.timestamp
                cl.total_requests += 1
                if event.status_code >= 400:
                    cl.error_count += 1
                if path_template not in cl.observed_endpoints:
                    cl.observed_endpoints.append(path_template)
                    cl.distinct_endpoints_count = len(cl.observed_endpoints)
                if event.user_agent not in cl.user_agents_observed and len(cl.user_agents_observed) < 5:
                    cl.user_agents_observed.append(event.user_agent)
                # Compute reputation score
                err_ratio = cl.error_count / cl.total_requests if cl.total_requests > 0 else 0
                cl.reputation_score = max(0.0, round(100.0 - (err_ratio * 70.0), 1))
            else:
                cl = ClientRecord(
                    client_id=client_id,
                    client_type=client_type,
                    ip_address=event.client_ip,
                    user_agents_observed=[event.user_agent],
                    first_seen_at=event.timestamp,
                    last_seen_at=event.timestamp,
                    total_requests=1,
                    error_count=1 if event.status_code >= 400 else 0,
                    distinct_endpoints_count=1,
                    observed_endpoints=[path_template],
                    geo_country=event.geo_country,
                    reputation_score=100.0 if event.status_code < 400 else 80.0,
                )
                self._clients_cache[client_id] = cl

            # 3. Update Session Record
            sess_key = f"{event.client_ip}:{event.user_agent}"
            if sess_key in self._active_sessions:
                sess = self._active_sessions[sess_key]
                sess.last_activity_at = event.timestamp
                sess.event_count += 1
                sess.endpoint_sequence.append(path_template)
                sess.status_sequence.append(event.status_code)
                # Cap sequence length for memory efficiency
                if len(sess.endpoint_sequence) > 100:
                    sess.endpoint_sequence = sess.endpoint_sequence[-100:]
                    sess.status_sequence = sess.status_sequence[-100:]
            else:
                sess = SessionRecord(
                    client_ip=event.client_ip,
                    user_agent=event.user_agent,
                    identity=event.auth_identity,
                    started_at=event.timestamp,
                    last_activity_at=event.timestamp,
                    event_count=1,
                    endpoint_sequence=[path_template],
                    status_sequence=[event.status_code],
                )
                self._active_sessions[sess_key] = sess

        return ep

    async def process_batch(self, events: List[ApiEvent]) -> int:
        """Processes a batch of events through inventory discovery."""
        for ev in events:
            await self.process_event(ev)
        await self.persist_inventory()
        return len(events)

    async def persist_inventory(self) -> None:
        """Saves cached inventory and client profiles to the persistent repository."""
        storage = await self._get_storage()
        async with self._lock:
            endpoints = list(self._endpoints_cache.values())
            clients = list(self._clients_cache.values())
            sessions = list(self._active_sessions.values())

        if hasattr(storage, "store_inventory_records"):
            await storage.store_inventory_records(endpoints, clients, sessions)

    async def discover_from_history(self) -> Dict[str, Any]:
        """Scans all historical events in storage to discover inventory assets."""
        storage = await self._get_storage()
        events_data = await storage.query_events(limit=50000)

        discovered_count = 0
        for row in events_data:
            # Reconstruct ApiEvent from row dict
            from backend.app.schemas.events import ApiEvent
            try:
                ev = ApiEvent(
                    event_id=row["event_id"],
                    timestamp=row["timestamp"],
                    source_type=row["source_type"],
                    gateway_id=row["gateway_id"],
                    http_method=row["http_method"],
                    path=row["path"],
                    raw_path=row["raw_path"],
                    status_code=row["status_code"],
                    latency_ms=row["latency_ms"],
                    client_ip=row["client_ip"],
                    user_agent=row["user_agent"],
                    auth_type=row.get("auth_type", "none"),
                    auth_identity=row.get("auth_identity"),
                    request_size_bytes=row.get("request_size_bytes", 0),
                    response_size_bytes=row.get("response_size_bytes", 0),
                    geo_country=row.get("geo_country"),
                    raw_log=row.get("raw_log", ""),
                )
                await self.process_event(ev)
                discovered_count += 1
            except Exception as e:
                logger.error(f"Error parsing historical row during discovery: {e}")

        await self.persist_inventory()
        return {
            "events_scanned": discovered_count,
            "unique_endpoints": len(self._endpoints_cache),
            "unique_clients": len(self._clients_cache),
        }

    def list_endpoints(
        self,
        method: Optional[str] = None,
        risk_level: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[EndpointRecord]:
        results = list(self._endpoints_cache.values())
        if method:
            results = [e for e in results if e.http_method.upper() == method.upper()]
        if risk_level:
            results = [e for e in results if e.risk_level.value == risk_level.lower()]
        if search:
            search_lower = search.lower()
            results = [e for e in results if search_lower in e.path_template.lower()]

        # Sort by call_count descending
        results.sort(key=lambda x: x.call_count, reverse=True)
        return results[offset : offset + limit]

    def get_endpoint(self, endpoint_id: str) -> Optional[EndpointRecord]:
        return self._endpoints_cache.get(endpoint_id)

    def list_clients(self, limit: int = 100, offset: int = 0) -> List[ClientRecord]:
        results = list(self._clients_cache.values())
        results.sort(key=lambda x: x.total_requests, reverse=True)
        return results[offset : offset + limit]

    def get_client(self, client_id: str) -> Optional[ClientRecord]:
        return self._clients_cache.get(client_id)

    def list_sessions(self, limit: int = 50) -> List[SessionRecord]:
        results = list(self._active_sessions.values())
        results.sort(key=lambda x: x.last_activity_at, reverse=True)
        return results[:limit]

    def get_summary(self) -> InventorySummary:
        endpoints = list(self._endpoints_cache.values())
        by_method: Dict[str, int] = {}
        by_risk: Dict[str, int] = {}
        auth_count = 0

        for ep in endpoints:
            by_method[ep.http_method] = by_method.get(ep.http_method, 0) + 1
            by_risk[ep.risk_level.value] = by_risk.get(ep.risk_level.value, 0) + 1
            if ep.is_authenticated:
                auth_count += 1

        return InventorySummary(
            total_endpoints=len(endpoints),
            endpoints_by_method=by_method,
            endpoints_by_risk=by_risk,
            total_clients=len(self._clients_cache),
            authenticated_endpoints_count=auth_count,
        )


# Global inventory service singleton
inventory_service = InventoryService()
