"""SentinelAPI OpenTelemetry Distributed Tracing & Correlation.

Implements standard W3C Trace Context (traceparent / tracestate) propagation,
span lifecycle management, and contextual distributed tracing across ingestion,
scoring, and policy enforcement pipelines.
"""

from contextvars import ContextVar
from datetime import datetime, timezone
import logging
import os
import time
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("sentinelapi.telemetry")

# Context variable tracking current active span
_current_span: ContextVar[Optional["Span"]] = ContextVar("current_span", default=None)


class Span:
    """Represents a distributed tracing span."""

    def __init__(
        self,
        name: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.trace_id = trace_id or uuid.uuid4().hex
        self.span_id = uuid.uuid4().hex[:16]
        self.parent_span_id = parent_span_id
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.duration_ms: float = 0.0
        self.attributes: Dict[str, Any] = attributes or {}
        self.events: List[Dict[str, Any]] = []
        self.status: str = "OK"
        self._token = None

    def set_attribute(self, key: str, value: Any) -> "Span":
        self.attributes[key] = value
        return self

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> "Span":
        self.events.append({
            "name": name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attributes": attributes or {},
        })
        return self

    def set_status_error(self, message: str) -> "Span":
        self.status = "ERROR"
        self.set_attribute("error.message", message)
        return self

    def end(self) -> None:
        if self.end_time is None:
            self.end_time = time.time()
            self.duration_ms = (self.end_time - self.start_time) * 1000.0

    def to_w3c_traceparent(self) -> str:
        """Returns standard W3C traceparent header: 00-{trace_id}-{span_id}-01."""
        return f"00-{self.trace_id.zfill(32)}-{self.span_id.zfill(16)}-01"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "duration_ms": round(self.duration_ms, 3),
            "status": self.status,
            "attributes": self.attributes,
            "events_count": len(self.events),
        }

    def __enter__(self) -> "Span":
        self._token = _current_span.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_val is not None:
            self.set_status_error(str(exc_val))
        self.end()
        if self._token:
            _current_span.reset(self._token)


class Tracer:
    """Manages distributed traces and span contexts."""

    def __init__(self, service_name: str = "sentinelapi-backend"):
        self.service_name = service_name
        self._spans_buffer: List[Dict[str, Any]] = []
        self._max_buffer = 1000

    def start_span(
        self,
        name: str,
        traceparent: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """Starts a new span, extracting parent context from W3C traceparent if present."""
        trace_id = None
        parent_span_id = None

        if traceparent and traceparent.startswith("00-"):
            parts = traceparent.split("-")
            if len(parts) >= 3:
                trace_id = parts[1]
                parent_span_id = parts[2]

        # Check active ambient context if no explicit parent provided
        if not trace_id:
            active = _current_span.get()
            if active:
                trace_id = active.trace_id
                parent_span_id = active.span_id

        span = Span(name=name, trace_id=trace_id, parent_span_id=parent_span_id, attributes=attributes)
        span.set_attribute("service.name", self.service_name)
        return span

    def get_current_span(self) -> Optional[Span]:
        return _current_span.get()


# Global tracer singleton
tracer = Tracer()
