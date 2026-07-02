from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from typing import Awaitable, Callable

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from malu.db.schemas import TradeHistoryDB
from malu.utils.logger import get_logger

log = get_logger("websocket")

# Bot events that represent a position close (carry realized pnl)
_CLOSE_EVENTS = {"defense_triggered", "liquidation_guard", "kill_close"}

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


def _trade_row_from_event(bot_id: str, event: str, data: dict) -> TradeHistoryDB | None:
    """Map a bot event to a trades-table row, or None if not a trade event."""
    if event == "trade":
        return TradeHistoryDB(
            bot_id=bot_id,
            order_link_id=data.get("order_link_id") or "",
            symbol=data.get("symbol", ""),
            side=data.get("side", ""),
            order_type="Market",
            qty=Decimal(data.get("qty", "0")),
            status="Filled",
            reason=data.get("reason"),
        )
    if event in _CLOSE_EVENTS:
        return TradeHistoryDB(
            bot_id=bot_id,
            order_link_id=data.get("order_link_id") or "",
            symbol=data.get("symbol", ""),
            side=data.get("side", ""),
            order_type="Market",
            qty=Decimal(data.get("qty", "0")),
            status="Filled",
            pnl=Decimal(data["pnl"]) if data.get("pnl") is not None else None,
            reason=data.get("reason"),
        )
    return None


def make_persisting_event_handler(
    trade_repo,
) -> Callable[[str, str, dict], Awaitable[None]]:
    """Wrap the broadcast handler with trade persistence.

    Entry fills and position closes are written to the trades table so
    per-bot history and total PnL reflect real activity. Persistence errors
    never block the broadcast.
    """

    async def handle(bot_id: str, event: str, data: dict) -> None:
        try:
            row = _trade_row_from_event(bot_id, event, data)
            if row is not None:
                await asyncio.to_thread(trade_repo.insert, row)
        except Exception as e:
            log.error("trade_persist_failed", bot_id=bot_id, bot_event=event, error=str(e))
        await bot_event_handler(bot_id, event, data)

    return handle


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
