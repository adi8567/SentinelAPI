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


@pytest.fixture(autouse=True)
def setup_test_storage():
    """Configures an in-memory DuckDB repository for testing."""
    repo = DuckDBStorageRepository(db_path=":memory:")
    # Initialize synchronously for compatibility with all tests
    asyncio.run(repo.initialize())
    StorageFactory.set_repository(repo)
    yield repo
    asyncio.run(repo.close())


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
