"""Storage Engine Factory."""

import logging
from typing import Optional
from backend.app.core.config import StorageBackend, settings
from backend.app.services.storage.clickhouse_client import ClickHouseStorageRepository
from backend.app.services.storage.duckdb_client import DuckDBStorageRepository
from backend.app.services.storage.repository import IStorageRepository

logger = logging.getLogger("sentinelapi.storage.factory")


class StorageFactory:
    _instance: Optional[IStorageRepository] = None

    @classmethod
    async def get_repository(cls) -> IStorageRepository:
        if cls._instance is not None:
            return cls._instance

        backend = settings.STORAGE_BACKEND

        if backend == StorageBackend.CLICKHOUSE:
            ch_repo = ClickHouseStorageRepository()
            try:
                await ch_repo.initialize()
                if ch_repo._client is not None:
                    cls._instance = ch_repo
                    return cls._instance
            except Exception as e:
                logger.warning(f"ClickHouse initialization failed ({e}), falling back to DuckDB.")

        # Default & resilient analytical engine: DuckDB
        duckdb_repo = DuckDBStorageRepository()
        await duckdb_repo.initialize()
        cls._instance = duckdb_repo
        return cls._instance

    @classmethod
    def set_repository(cls, repo: IStorageRepository) -> None:
        cls._instance = repo


# Convenience accessor
async def get_storage() -> IStorageRepository:
    return await StorageFactory.get_repository()

get_storage_repository = get_storage
