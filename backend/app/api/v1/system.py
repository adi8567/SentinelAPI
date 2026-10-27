"""SentinelAPI System Telemetry and Component Observability Endpoints.

Provides deep component status, memory usage, streaming buffer health, and runtime metrics.
"""

from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter
from backend.app.api.deps import CurrentPrincipal
from backend.app.core.config import settings
from backend.app.services.auth.auth_service import auth_service
from backend.app.services.baseline.batch_learner import batch_baseline_learner
from backend.app.services.detection.engine import anomaly_engine
from backend.app.services.ingestion.pipeline import ingestion_pipeline
from backend.app.services.inventory.inventory_service import inventory_service
from backend.app.services.policy.engine import policy_engine
from backend.app.services.storage.factory import get_storage
from backend.app.services.streaming.websocket_manager import ws_manager

router = APIRouter(prefix="/system", tags=["System & Telemetry"])


@router.get("/status", response_model=Dict[str, Any])
async def get_system_status(
    principal: CurrentPrincipal,
) -> Dict[str, Any]:
    """Retrieves deep component health and operational diagnostics across all platform services."""
    storage = await get_storage()
    db_health = await storage.health_check()
    pipeline_stats = ingestion_pipeline.get_stats()
    inv_summary = inventory_service.get_summary()
    anom_stats = anomaly_engine.get_stats()
    pol_stats = await policy_engine.get_stats()
    ws_stats = ws_manager.get_stats()

    return {
        "status": "operational",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "storage": db_health,
        "pipeline": pipeline_stats,
        "inventory": inv_summary.model_dump(mode="json"),
        "detection_engine": {
            "model_version": anomaly_engine.version,
            "anomaly_threshold": anomaly_engine.anomaly_threshold,
            "total_anomalies_flagged": anom_stats["total_anomalies"],
            "severity_breakdown": anom_stats["severity_breakdown"],
        },
        "policy_engine": pol_stats.model_dump(mode="json"),
        "baselines": {
            "endpoints_with_baselines": len(batch_baseline_learner._endpoint_baselines),
        },
        "websockets": ws_stats,
    }
