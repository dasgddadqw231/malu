from __future__ import annotations

import asyncio

from malu.exchange.market_data_store import MarketDataStore
from malu.exchange.ws_client import BybitWSClient
from malu.utils.logger import get_logger

log = get_logger("market_data_feed")


class MarketDataFeed:
    """Manages the WebSocket connection lifecycle and symbol subscriptions.

    One instance per engine. BotManager owns this and passes
    the store reference to bots/strategies.
    """

    def __init__(self, testnet: bool, kline_intervals: list[str] | None = None):
        self.store = MarketDataStore()
        self._ws_client = BybitWSClient(testnet=testnet, store=self.store)
        self._kline_intervals = kline_intervals or ["1", "5", "15"]
        self._started = False

    async def start(self) -> None:
        """Start WebSocket connection (pybit manages its own thread)."""
        if self._started:
            return
        await asyncio.to_thread(self._ws_client.connect)
        self._started = True
        log.info("market_data_feed_started")

    async def subscribe(self, symbol: str) -> None:
        """Subscribe to market data for a symbol. Safe to call multiple times."""
        if not self._started:
            await self.start()
        await asyncio.to_thread(
            self._ws_client.subscribe, symbol, self._kline_intervals
        )

    async def stop(self) -> None:
        """Shut down the WebSocket connection."""
        if self._started:
            await asyncio.to_thread(self._ws_client.close)
            self._started = False
            log.info("market_data_feed_stopped")

    @property
    def is_running(self) -> bool:
        return self._started
