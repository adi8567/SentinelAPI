"""SentinelAPI Main Application Entry Point.

Intelligent API Anomaly Detection & Adaptive Protection Platform.
"""

from contextlib import asynccontextmanager
import time
import uuid
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.app.api.v1.router import api_router
from backend.app.core.config import settings
from backend.app.core.logging import logger, request_id_ctx
from backend.app.core.metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
    export_metrics,
)
from backend.app.core.telemetry import tracer
from backend.app.services.storage.factory import get_storage
from backend.app.services.streaming.kafka_client import stream_producer


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")
    
    # 1. Initialize analytical storage repository & run migrations
    storage = await get_storage()
    await storage.initialize()

    # 2. Start streaming broker / buffer
    await stream_producer.start()

    # 3. Initialize adaptive policy engine
    from backend.app.services.policy.engine import policy_engine
    await policy_engine.initialize()

    # 4. Initialize authentication & user accounts
    from backend.app.services.auth.auth_service import auth_service
    await auth_service.initialize()

    logger.info("SentinelAPI core services initialized successfully.")
    yield

    # Shutdown
    logger.info("Shutting down SentinelAPI services...")
    await stream_producer.stop()
    await storage.close()
    logger.info("SentinelAPI shutdown completed.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "SentinelAPI – Intelligent API Anomaly Detection & Adaptive Protection Platform. "
        "Production-grade real-time API monitoring, behavioral baseline learning, "
        "and adaptive threat mitigation."
    ),
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else ["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_and_timing_middleware(request: Request, call_next):
    """Assigns unique correlation ID, tracks latency, sets security headers, and records telemetry."""
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    token = request_id_ctx.set(req_id)
    start_time = time.perf_counter()

    traceparent = request.headers.get("traceparent")
    span = tracer.start_span(
        f"HTTP {request.method} {request.url.path}",
        traceparent=traceparent,
        attributes={"http.method": request.method, "http.url": str(request.url.path), "request.id": req_id},
    )

    with span:
        try:
            response: Response = await call_next(request)
            duration_sec = time.perf_counter() - start_time
            elapsed_ms = round(duration_sec * 1000.0, 2)

            # Record Prometheus Metrics (skip metrics endpoint itself to avoid noise)
            if request.url.path != "/metrics":
                endpoint_label = request.url.path
                HTTP_REQUESTS_TOTAL.labels(
                    method=request.method,
                    endpoint=endpoint_label,
                    status_code=str(response.status_code),
                ).inc()
                HTTP_REQUEST_DURATION_SECONDS.labels(
                    method=request.method,
                    endpoint=endpoint_label,
                ).observe(duration_sec)

            # Security Headers & Distributed Tracing
            response.headers["X-Request-ID"] = req_id
            response.headers["X-Response-Time-Ms"] = str(elapsed_ms)
            response.headers["traceparent"] = span.to_w3c_traceparent()
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"

            return response
        finally:
            request_id_ctx.reset(token)


# Mount API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/metrics", tags=["Observability"])
async def get_prometheus_metrics():
    """Exposes real-time Prometheus text exposition metrics for scraping."""
    return Response(
        content=export_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "docs_url": f"{settings.API_V1_STR}/docs",
        "health_url": f"{settings.API_V1_STR}/health",
    }
