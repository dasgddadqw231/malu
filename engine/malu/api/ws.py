from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from malu.utils.logger import get_logger

log = get_logger("websocket")

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for live dashboard updates."""

    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)
        log.info("ws_connected", total=len(self.connections))

    def disconnect(self, ws: WebSocket):
        self.connections.remove(ws)
        log.info("ws_disconnected", total=len(self.connections))

    async def broadcast(self, event: str, data: dict):
        message = json.dumps({"event": event, **data})
        dead = []
        for ws in self.connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.connections.remove(ws)


ws_manager = ConnectionManager()


async def bot_event_handler(bot_id: str, event: str, data: dict):
    """Callback passed to BotManager to broadcast events to WebSocket clients."""
    await ws_manager.broadcast(event, {"bot_id": bot_id, **data})


@router.websocket("/ws/live")
async def websocket_live(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            # Keep connection alive, receive any client messages
            data = await ws.receive_text()
            # Client can send ping or commands
            if data == "ping":
                await ws.send_text(json.dumps({"event": "pong"}))
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)
