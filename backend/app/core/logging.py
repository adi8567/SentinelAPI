"""SentinelAPI Structured Logging Configuration.

Provides high-performance structured JSON logging for production
and human-readable colored logging for local development. Includes
context tracking for request IDs and event correlation.
"""

import contextvars
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Context variable for request tracing
request_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id", default=None
)


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects with ISO8601 timestamps."""

    def format(self, record: logging.LogRecord) -> str:
        log_payload: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }

        # Include correlation / request ID if present in context
        req_id = request_id_ctx.get()
        if req_id:
            log_payload["request_id"] = req_id

        # Include extra attributes attached to record
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_payload.update(record.extra)

        # Exception info
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload)


class ConsoleFormatter(logging.Formatter):
    """Colorized console formatter for development."""

    COLORS = {
        logging.DEBUG: "\033[36m",     # Cyan
        logging.INFO: "\033[32m",      # Green
        logging.WARNING: "\033[33m",   # Yellow
        logging.ERROR: "\033[31m",     # Red
        logging.CRITICAL: "\033[41m",  # Red background
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, self.RESET)
        time_str = datetime.fromtimestamp(
            record.created, tz=timezone.utc
        ).strftime("%Y-%m-%d %H:%M:%S")

        req_id = request_id_ctx.get()
        req_prefix = f" [{req_id}]" if req_id else ""

        msg = (
            f"{color}{time_str} | {record.levelname:<8}{self.RESET} | "
            f"\033[35m{record.name}\033[0m{req_prefix} - {record.getMessage()}"
        )
        if record.exc_info:
            msg += f"\n{self.formatException(record.exc_info)}"
        return msg


def setup_logging(
    level: str = "INFO",
    format_type: str = "console",
) -> logging.Logger:
    """Configures root and application loggers."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    if format_type.lower() == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(ConsoleFormatter())

    root_logger.addHandler(handler)

    # Set specific levels for external libraries to prevent noise
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("kafka").setLevel(logging.WARNING)
    logging.getLogger("duckdb").setLevel(logging.WARNING)

    logger = logging.getLogger("sentinelapi")
    logger.setLevel(log_level)
    return logger


logger = setup_logging()
