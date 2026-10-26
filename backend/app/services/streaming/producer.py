"""Streaming Producer Interface."""

import abc
from typing import Any, Dict, List
from backend.app.schemas.events import ApiEvent


class IStreamingProducer(abc.ABC):
    """Abstract interface for event streaming brokers (Kafka, Redpanda, memory buffer)."""

    @abc.abstractmethod
    async def start(self) -> None:
        """Initializes connection to streaming cluster or starts worker."""
        pass

    @abc.abstractmethod
    async def stop(self) -> None:
        """Flushes buffers and closes connections."""
        pass

    @abc.abstractmethod
    async def produce_event(self, event: ApiEvent, topic: str = "") -> bool:
        """Publishes a single normalized ApiEvent to the stream."""
        pass

    @abc.abstractmethod
    async def produce_batch(self, events: List[ApiEvent], topic: str = "") -> int:
        """Publishes a batch of ApiEvents. Returns count of published events."""
        pass

    @abc.abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Returns streaming engine metrics (events produced, errors, buffer size)."""
        pass
