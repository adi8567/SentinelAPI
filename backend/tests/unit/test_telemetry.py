"""Unit tests for SentinelAPI OpenTelemetry Tracing & Context Propagation."""

import pytest
from backend.app.core.telemetry import tracer


def test_tracer_span_creation_and_w3c_traceparent():
    span = tracer.start_span("test-operation")
    with span:
        span.set_attribute("http.method", "POST")
        span.add_event("validation_passed")

    assert span.status == "OK"
    assert span.duration_ms > 0
    assert span.attributes.get("http.method") == "POST"
    assert len(span.events) == 1

    # Verify standard W3C traceparent formatting
    tp = span.to_w3c_traceparent()
    assert tp.startswith("00-")
    parts = tp.split("-")
    assert len(parts) == 4
    assert len(parts[1]) == 32  # 32-hex trace_id
    assert len(parts[2]) == 16  # 16-hex span_id
    assert parts[3] == "01"


def test_tracer_child_span_correlation():
    parent_span = tracer.start_span("parent-request")
    with parent_span:
        child_span = tracer.start_span("child-db-query")
        with child_span:
            assert child_span.trace_id == parent_span.trace_id
            assert child_span.parent_span_id == parent_span.span_id
