"""
WebSocket API for real-time updates.

Provides real-time meter data, channel updates, and device status.
"""

import asyncio
import json
import logging
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._meter_task = None

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return

        message_json = json.dumps(message)
        dead_connections = set()

        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception:
                dead_connections.add(connection)

        # Clean up dead connections
        self.active_connections -= dead_connections

    async def send_personal(self, websocket: WebSocket, message: dict):
        """Send a message to a specific client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")


manager = ConnectionManager()


@router.websocket("/live")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for real-time updates.

    Message types received:
    - subscribe: Subscribe to specific data (meters, channels, devices)
    - unsubscribe: Unsubscribe from data
    - get_state: Request current state

    Message types sent:
    - meters: Meter level data
    - channel_update: Channel parameter changed
    - device_status: Device online/offline
    - scene_recalled: Scene was recalled
    """
    await manager.connect(websocket)
    app = websocket.app

    # Track subscriptions for this connection
    subscriptions = set()

    try:
        # Send initial state
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connected to TF Showbuilder"
        })

        while True:
            # Receive and process messages
            data = await websocket.receive_json()

            msg_type = data.get("type")

            if msg_type == "subscribe":
                topic = data.get("topic")
                if topic:
                    subscriptions.add(topic)
                    await websocket.send_json({
                        "type": "subscribed",
                        "topic": topic
                    })

                    # If subscribing to meters, start meter updates
                    if topic == "meters" and hasattr(app.state, 'tf_rack'):
                        asyncio.create_task(
                            send_meter_updates(websocket, app.state.tf_rack)
                        )

            elif msg_type == "unsubscribe":
                topic = data.get("topic")
                subscriptions.discard(topic)
                await websocket.send_json({
                    "type": "unsubscribed",
                    "topic": topic
                })

            elif msg_type == "get_state":
                # Send current state
                state = await get_current_state(app)
                await websocket.send_json({
                    "type": "state",
                    "data": state
                })

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


async def send_meter_updates(websocket: WebSocket, tf_rack):
    """Send periodic meter updates to a WebSocket client."""
    try:
        while websocket in manager.active_connections:
            if tf_rack and tf_rack.is_connected:
                # Get meter data (this would come from TF-Rack callbacks)
                # For now, send placeholder data
                meters = {
                    "type": "meters",
                    "inputs": [0] * 32,  # Would be actual meter levels
                    "outputs": [0] * 20
                }
                await websocket.send_json(meters)

            await asyncio.sleep(0.1)  # 10Hz update rate
    except Exception:
        pass  # Connection closed


async def get_current_state(app):
    """Get current application state."""
    state = {
        "tf_rack": {
            "connected": False
        },
        "dante": {
            "devices": []
        },
        "eink": {
            "displays": []
        }
    }

    if hasattr(app.state, 'tf_rack'):
        state["tf_rack"]["connected"] = app.state.tf_rack.is_connected

    if hasattr(app.state, 'dante'):
        devices = app.state.dante.get_devices()
        state["dante"]["devices"] = [
            {"name": d.name, "online": d.is_online}
            for d in devices
        ]

    if hasattr(app.state, 'eink'):
        state["eink"]["displays"] = app.state.eink.get_display_status()

    return state


# ========== Broadcast helpers for other modules ==========

async def broadcast_channel_update(channel_number: int, param: str, value):
    """Broadcast a channel parameter update."""
    await manager.broadcast({
        "type": "channel_update",
        "channel": channel_number,
        "param": param,
        "value": value
    })


async def broadcast_device_status(device_name: str, online: bool):
    """Broadcast a device status change."""
    await manager.broadcast({
        "type": "device_status",
        "device": device_name,
        "online": online
    })


async def broadcast_scene_recalled(scene_number: int, scene_name: str):
    """Broadcast a scene recall event."""
    await manager.broadcast({
        "type": "scene_recalled",
        "scene_number": scene_number,
        "scene_name": scene_name
    })
