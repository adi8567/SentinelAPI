"""FastAPI Dependency Injection Providers."""

from typing import Annotated
from fastapi import Depends
from backend.app.core.security import AuthenticatedPrincipal, get_current_principal
from backend.app.services.ingestion.pipeline import IngestionPipeline, ingestion_pipeline
from backend.app.services.storage.factory import get_storage
from backend.app.services.storage.repository import IStorageRepository
from backend.app.services.streaming.kafka_client import KafkaStreamProducer, stream_producer


def get_pipeline() -> IngestionPipeline:
    return ingestion_pipeline


def get_stream_producer() -> KafkaStreamProducer:
    return stream_producer


async def get_storage_repo() -> IStorageRepository:
    return await get_storage()


# Type annotations for clean route signatures
CurrentPrincipal = Annotated[AuthenticatedPrincipal, Depends(get_current_principal)]
PipelineDep = Annotated[IngestionPipeline, Depends(get_pipeline)]
StorageDep = Annotated[IStorageRepository, Depends(get_storage_repo)]
ProducerDep = Annotated[KafkaStreamProducer, Depends(get_stream_producer)]
