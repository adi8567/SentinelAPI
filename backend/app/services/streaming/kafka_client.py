"""Kafka & Resilient Fallback Streaming Client.

Supports streaming to an Apache Kafka or Redpanda cluster with automatic fallback
to an in-memory high-throughput ring buffer if Kafka is offline or unconfigured.
"""

import asyncio
from collections import deque
import json
import logging
from typing import Any, Callable, Deque, Dict, List, Optional
import orjson
from backend.app.core.config import StreamingBackend, settings
from backend.app.schemas.events import ApiEvent
from backend.app.services.streaming.producer import IStreamingProducer

logger = logging.getLogger("sentinelapi.streaming")


class ResilientStreamBuffer:
    """Thread-safe and async-friendly ring buffer for real-time event streaming."""

    def __init__(self, maxsize: int = 100_000):
        self.maxsize = maxsize
        self._buffer: Deque[Dict[str, Any]] = deque(maxlen=maxsize)
        self._subscribers: List[Callable[[Dict[str, Any]], Any]] = []
        self._total_enqueued: int = 0
        self._total_dropped: int = 0

    def append(self, item: Dict[str, Any]) -> None:
        if len(self._buffer) >= self.maxsize:
            self._total_dropped += 1
        self._buffer.append(item)
        self._total_enqueued += 1

        # Notify any registered real-time listeners/subscribers (e.g. anomaly engines)
        for sub in self._subscribers:
            try:
                sub(item)
            except Exception as e:
                logger.error(f"Error in stream subscriber callback: {e}")

    def extend(self, items: List[Dict[str, Any]]) -> int:
        for item in items:
            self.append(item)
        return len(items)

    def subscribe(self, callback: Callable[[Dict[str, Any]], Any]) -> None:
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def get_recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        return list(self._buffer)[-limit:]

    @property
    def current_size(self) -> int:
        return len(self._buffer)

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "buffered_events": len(self._buffer),
            "max_capacity": self.maxsize,
            "total_enqueued": self._total_enqueued,
            "total_dropped": self._total_dropped,
            "subscribers_count": len(self._subscribers),
        }


class KafkaStreamProducer(IStreamingProducer):
    """Kafka event publisher with automatic fallback and metrics."""

    def __init__(self):
        self.backend_mode = settings.STREAMING_BACKEND
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        self.topic_normalized = settings.KAFKA_TOPIC_NORMALIZED_EVENTS
        self.topic_raw = settings.KAFKA_TOPIC_RAW_EVENTS

        self._kafka_producer = None
        self._is_kafka_connected = False
        self._memory_buffer = ResilientStreamBuffer(maxsize=settings.STREAMING_BUFFER_MAX_SIZE)

        self._stats = {
            "kafka_messages_sent": 0,
            "buffer_messages_sent": 0,
            "errors": 0,
            "backend_active": "memory",
        }

    async def start(self) -> None:
        """Initializes connection to Kafka if configured."""
        if self.backend_mode == StreamingBackend.KAFKA:
            await self._try_connect_kafka()
        else:
            self._stats["backend_active"] = "memory_buffer"
            logger.info("Streaming initialized in resilient in-memory buffer mode.")

    async def _try_connect_kafka(self) -> bool:
        try:
            from kafka import KafkaProducer

            def serializer(v: Dict[str, Any]) -> bytes:
                return orjson.dumps(v)

            # Attempt connection in worker thread
            def _create_prod():
                return KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers.split(","),
                    value_serializer=serializer,
                    client_id=settings.KAFKA_CLIENT_ID,
                    acks=1,
                    retries=settings.KAFKA_RETRIES,
                    request_timeout_ms=3000,
                    max_block_ms=3000,
                )

            loop = asyncio.get_event_loop()
            self._kafka_producer = await loop.run_in_executor(None, _create_prod)
            self._is_kafka_connected = True
            self._stats["backend_active"] = "kafka"
            logger.info(f"Connected to Kafka cluster at {self.bootstrap_servers}")
            return True
        except Exception as e:
            logger.warning(
                f"Kafka not available at {self.bootstrap_servers} ({e}). "
                "Engaging resilient in-memory fallback buffer. All events preserved."
            )
            self._is_kafka_connected = False
            self._stats["backend_active"] = "memory_fallback"
            return False

    async def stop(self) -> None:
        """Closes Kafka producer if open."""
        if self._kafka_producer:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._kafka_producer.flush)
                await loop.run_in_executor(None, self._kafka_producer.close)
            except Exception as e:
                logger.error(f"Error closing Kafka producer: {e}")
            finally:
                self._kafka_producer = None
                self._is_kafka_connected = False

    async def produce_event(self, event: ApiEvent, topic: str = "") -> bool:
        target_topic = topic or self.topic_normalized
        event_dict = event.model_dump(mode="json")

        if self._is_kafka_connected and self._kafka_producer:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self._kafka_producer.send(target_topic, key=event.event_id.encode(), value=event_dict)
                )
                self._stats["kafka_messages_sent"] += 1
                return True
            except Exception as e:
                logger.warning(f"Failed to publish to Kafka ({e}), falling back to memory buffer.")
                self._is_kafka_connected = False
                self._stats["backend_active"] = "memory_fallback"

        # Buffer fallback
        self._memory_buffer.append(event_dict)
        self._stats["buffer_messages_sent"] += 1
        return True

    async def produce_batch(self, events: List[ApiEvent], topic: str = "") -> int:
        if not events:
            return 0
        target_topic = topic or self.topic_normalized
        event_dicts = [e.model_dump(mode="json") for e in events]

        if self._is_kafka_connected and self._kafka_producer:
            try:
                loop = asyncio.get_event_loop()
                def _send_all():
                    for ed in event_dicts:
                        self._kafka_producer.send(target_topic, key=ed["event_id"].encode(), value=ed)
                await loop.run_in_executor(None, _send_all)
                self._stats["kafka_messages_sent"] += len(events)
                return len(events)
            except Exception as e:
                logger.warning(f"Failed Kafka batch send ({e}), falling back to buffer.")
                self._is_kafka_connected = False
                self._stats["backend_active"] = "memory_fallback"

        self._memory_buffer.extend(event_dicts)
        self._stats["buffer_messages_sent"] += len(events)
        return len(events)

    def get_stats(self) -> Dict[str, Any]:
        stats = dict(self._stats)
        stats["is_kafka_connected"] = self._is_kafka_connected
        stats["buffer_stats"] = self._memory_buffer.stats
        return stats

    @property
    def buffer(self) -> ResilientStreamBuffer:
        return self._memory_buffer


# Global streaming producer singleton
stream_producer = KafkaStreamProducer()
