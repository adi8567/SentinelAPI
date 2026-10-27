"""Pytest Fixtures and Test Environment Setup."""

import asyncio
from pathlib import Path
import sys
import pytest
from httpx import ASGITransport, AsyncClient

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.app.core.config import settings
from backend.app.main import app
from backend.app.services.storage.duckdb_client import DuckDBStorageRepository
from backend.app.services.storage.factory import StorageFactory
from backend.app.services.detection.engine import anomaly_engine
from backend.app.services.policy.engine import policy_engine
from backend.app.services.inventory.inventory_service import inventory_service
from backend.app.services.baseline.batch_learner import batch_baseline_learner
from backend.app.services.baseline.online_updater import online_baseline_updater


@pytest.fixture(autouse=True)
def setup_test_storage():
    """Configures an in-memory DuckDB repository and resets singletons for testing."""
    # Reset in-memory states to prevent cross-test contamination
    anomaly_engine._recent_anomalies.clear()
    inventory_service._endpoints_cache.clear()
    inventory_service._clients_cache.clear()
    inventory_service._active_sessions.clear()
    batch_baseline_learner._endpoint_baselines.clear()
    batch_baseline_learner._client_baselines.clear()
    online_baseline_updater._trackers.clear()
    asyncio.run(policy_engine.reset())

    repo = DuckDBStorageRepository(db_path=":memory:")
    # Initialize synchronously for compatibility with all tests
    asyncio.run(repo.initialize())
    StorageFactory.set_repository(repo)
    yield repo
    asyncio.run(repo.close())

    # Post-test cleanup
    anomaly_engine._recent_anomalies.clear()
    asyncio.run(policy_engine.reset())


@pytest.fixture
async def async_client():
    """Provides an authenticated AsyncClient for API testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"X-API-Key": settings.ADMIN_API_KEY},
    ) as client:
        yield client


@pytest.fixture
def auth_headers():
    return {"X-API-Key": settings.ADMIN_API_KEY}


@pytest.fixture
def agent_headers():
    return {"X-API-Key": settings.INGESTION_API_KEYS[0]}
