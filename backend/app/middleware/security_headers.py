"""SentinelAPI Security Headers & Defense Middleware.

Injects enterprise-grade security headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options)
and enforces backend API abuse throttling.
"""

import time
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse
from backend.app.services.policy.actions.throttler import adaptive_throttler


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforces enterprise HTTP security headers on all responses."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        # 1. Prevent MIME-sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # 2. Prevent clickjacking / frame embedding
        response.headers["X-Frame-Options"] = "DENY"

        # 3. Enable legacy browser XSS filters
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # 4. Enforce HTTPS Strict Transport Security
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # 5. Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 6. Basic Content Security Policy
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"

        return response


class ApiRateLimitMiddleware(BaseHTTPMiddleware):
    """Protects backend APIs against brute-force abuse and DoS."""

    def __init__(self, app, max_rpm: int = 300):
        super().__init__(app)
        self.max_rpm = max_rpm

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # Exempt high-throughput ingestion and docs from strict rate limit
        if path.startswith("/api/v1/ingest") or path.startswith("/api/v1/docs") or path.startswith("/api/v1/openapi.json"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "127.0.0.1"
        is_throttled, retry_after, count = await adaptive_throttler.record_and_check(
            key=f"api_mw_{client_ip}",
            limit_rpm=self.max_rpm,
            window_seconds=60,
        )

        if is_throttled:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "type": "https://errors.sentinelapi.local/rate-limit-exceeded",
                    "title": "API Rate Limit Exceeded",
                    "status": 429,
                    "detail": f"Too many requests from IP {client_ip}. Please retry after {retry_after} seconds.",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
