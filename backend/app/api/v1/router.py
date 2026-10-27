"""API v1 Main Router."""

from fastapi import APIRouter
from backend.app.api.v1.alerts import router as alerts_router
from backend.app.api.v1.anomalies import router as anomalies_router
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.baselines import router as baselines_router
from backend.app.api.v1.dashboard import router as dashboard_router
from backend.app.api.v1.events import router as events_router
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.ingestion import router as ingestion_router
from backend.app.api.v1.inventory import router as inventory_router
from backend.app.api.v1.investigation import router as investigation_router
from backend.app.api.v1.policies import router as policies_router
from backend.app.api.v1.system import router as system_router
from backend.app.api.v1.websocket import router as ws_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(ingestion_router)
api_router.include_router(events_router)
api_router.include_router(inventory_router)
api_router.include_router(baselines_router)
api_router.include_router(anomalies_router)
api_router.include_router(policies_router)
api_router.include_router(alerts_router)
api_router.include_router(dashboard_router)
api_router.include_router(investigation_router)
api_router.include_router(system_router)
api_router.include_router(ws_router)
