"""SentinelAPI Real-Time WebSocket Streaming Hub.

Manages persistent client WebSocket connections, channel subscriptions (traffic, alerts, metrics),
heartbeats, and low-latency broadcast distribution.
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Set
from fastapi import WebSocket

logger = logging.getLogger("sentinelapi.ws")


class WebSocketConnectionManager:
    """Manages active WebSockets and topic-based broadcast distribution."""

    def __init__(self):
        # topic -> set of WebSockets
        self._subscriptions: Dict[str, Set[WebSocket]] = {
            "traffic": set(),
            "alerts": set(),
            "metrics": set(),
        }
        self._lock = asyncio.Lock()
        self._total_messages_broadcast = 0

    async def connect(self, websocket: WebSocket, topic: str = "traffic") -> None:
        """Accepts and registers a new WebSocket client on a topic."""
        await websocket.accept()
        async with self._lock:
            if topic not in self._subscriptions:
                self._subscriptions[topic] = set()
            self._subscriptions[topic].add(websocket)
        logger.info(f"WebSocket client connected to topic '{topic}'. Active: {len(self._subscriptions[topic])}")

    async def disconnect(self, websocket: WebSocket, topic: str = "traffic") -> None:
        """Removes a disconnected client."""
        async with self._lock:
            if topic in self._subscriptions:
                self._subscriptions[topic].discard(websocket)
        logger.info(f"WebSocket client disconnected from topic '{topic}'.")

    async def broadcast(self, topic: str, message: Dict[str, Any]) -> int:
        """Broadcasts a JSON message to all clients subscribed to a topic."""
        if topic not in self._subscriptions or not self._subscriptions[topic]:
            return 0

        async with self._lock:
            clients = list(self._subscriptions[topic])

        data_str = json.dumps(message, default=str)
        delivered = 0
        disconnected = []

        for ws in clients:
            try:
                await ws.send_text(data_str)
                delivered += 1
            except Exception:
                disconnected.append(ws)

        if disconnected:
            async with self._lock:
                for ws in disconnected:
                    self._subscriptions[topic].discard(ws)

        self._total_messages_broadcast += delivered
        return delivered

    def get_stats(self) -> Dict[str, Any]:
        """Returns connection and distribution telemetry."""
        return {
            "active_connections_by_topic": {k: len(v) for k, v in self._subscriptions.items()},
            "total_messages_broadcast": self._total_messages_broadcast,
        }


# Global singleton instance
ws_manager = WebSocketConnectionManager()
