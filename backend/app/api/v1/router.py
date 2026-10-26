"""API v1 Main Router."""

from fastapi import APIRouter
from backend.app.api.v1.baselines import router as baselines_router
from backend.app.api.v1.events import router as events_router
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.ingestion import router as ingestion_router
from backend.app.api.v1.inventory import router as inventory_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(ingestion_router)
api_router.include_router(events_router)
api_router.include_router(inventory_router)
api_router.include_router(baselines_router)
