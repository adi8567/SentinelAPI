"""SentinelAPI Real-Time WebSocket Streaming Endpoints.

Provides WebSocket channels for streaming live API traffic, anomaly alerts,
and system telemetry to frontend dashboards.
"""

import asyncio
from datetime import datetime, timezone
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.app.services.streaming.websocket_manager import ws_manager

logger = logging.getLogger("sentinelapi.api.ws")
router = APIRouter(prefix="/ws", tags=["Real-Time WebSockets"])


@router.websocket("/live-traffic")
async def websocket_live_traffic(websocket: WebSocket):
    """Streams live ingested API traffic events in real time."""
    await ws_manager.connect(websocket, topic="traffic")
    try:
        # Send initial connection greeting
        await websocket.send_json({
            "type": "connection_established",
            "topic": "traffic",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        while True:
            # Keep-alive ping / client message handling
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, topic="traffic")
    except Exception as e:
        logger.debug(f"Live traffic websocket closed: {e}")
        await ws_manager.disconnect(websocket, topic="traffic")


@router.websocket("/alerts")
async def websocket_live_alerts(websocket: WebSocket):
    """Streams live anomaly detection events and automated protection decisions."""
    await ws_manager.connect(websocket, topic="alerts")
    try:
        await websocket.send_json({
            "type": "connection_established",
            "topic": "alerts",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, topic="alerts")
    except Exception as e:
        logger.debug(f"Alerts websocket closed: {e}")
        await ws_manager.disconnect(websocket, topic="alerts")


@router.websocket("/metrics")
async def websocket_live_metrics(websocket: WebSocket):
    """Streams periodically refreshed live metrics (EPS, latency, active bans)."""
    await ws_manager.connect(websocket, topic="metrics")
    try:
        await websocket.send_json({
            "type": "connection_established",
            "topic": "metrics",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, topic="metrics")
    except Exception as e:
        logger.debug(f"Metrics websocket closed: {e}")
        await ws_manager.disconnect(websocket, topic="metrics")
