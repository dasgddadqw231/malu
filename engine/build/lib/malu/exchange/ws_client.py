from __future__ import annotations

import threading

from pybit.unified_trading import WebSocket

from malu.exchange.market_data_store import MarketDataStore
from malu.utils.logger import get_logger

log = get_logger("ws_client")


class BybitWSClient:
    """Wraps pybit WebSocket, bridging threaded callbacks into MarketDataStore.

    pybit manages its own daemon thread for the WebSocket connection,
    including auto-reconnection and delta-to-snapshot processing for
    orderbook and ticker data.
    """

    def __init__(self, testnet: bool, store: MarketDataStore):
        self._testnet = testnet
        self._store = store
        self._ws: WebSocket | None = None
        self._subscribed_symbols: set[str] = set()
        self._lock = threading.Lock()

    def connect(self) -> None:
        """Connect to Bybit public linear WebSocket."""
        self._ws = WebSocket(
            channel_type="linear",
            testnet=self._testnet,
        )
        log.info("ws_connected", testnet=self._testnet)

    def subscribe(self, symbol: str, kline_intervals: list[str] | None = None) -> None:
        """Subscribe to all standard topics for a symbol.

        Safe to call multiple times for the same symbol (deduped).
        """
        if not self._ws:
            raise RuntimeError("WebSocket not connected")

        with self._lock:
            if symbol in self._subscribed_symbols:
                return
            self._subscribed_symbols.add(symbol)

        # Orderbook depth 50
        self._ws.orderbook_stream(50, symbol, self._on_orderbook)
        # Public trade stream
        self._ws.trade_stream(symbol, self._on_trade)
        # Ticker (price, OI, funding rate, volume, etc.)
        self._ws.ticker_stream(symbol, self._on_ticker)
        # Kline streams for specified intervals
        for interval in (kline_intervals or ["1", "5", "15"]):
            self._ws.kline_stream(interval, symbol, self._on_kline)

        log.info("ws_subscribed", symbol=symbol, intervals=kline_intervals or ["1", "5", "15"])

    def unsubscribe(self, symbol: str) -> None:
        """Remove symbol from tracked set. Note: pybit doesn't support unsubscribe natively."""
        with self._lock:
            self._subscribed_symbols.discard(symbol)

    def _on_orderbook(self, message: dict) -> None:
        try:
            topic = message.get("topic", "")  # e.g. "orderbook.50.BTCUSDT"
            symbol = topic.split(".")[-1]
            self._store.update_orderbook(symbol, message["data"])
        except Exception as e:
            log.error("ws_orderbook_error", error=str(e))

    def _on_trade(self, message: dict) -> None:
        try:
            topic = message.get("topic", "")  # e.g. "publicTrade.BTCUSDT"
            symbol = topic.split(".")[-1]
            self._store.update_trades(symbol, message["data"])
        except Exception as e:
            log.error("ws_trade_error", error=str(e))

    def _on_ticker(self, message: dict) -> None:
        try:
            topic = message.get("topic", "")  # e.g. "tickers.BTCUSDT"
            symbol = topic.split(".")[-1]
            self._store.update_ticker(symbol, message["data"])
        except Exception as e:
            log.error("ws_ticker_error", error=str(e))

    def _on_kline(self, message: dict) -> None:
        try:
            topic = message.get("topic", "")  # e.g. "kline.15.BTCUSDT"
            parts = topic.split(".")
            interval = parts[1]
            symbol = parts[2]
            self._store.update_kline(symbol, interval, message["data"])
        except Exception as e:
            log.error("ws_kline_error", error=str(e))

    def close(self) -> None:
        """Shut down the WebSocket connection."""
        if self._ws:
            try:
                self._ws.exit()
            except Exception as e:
                log.error("ws_close_error", error=str(e))
            self._ws = None
            with self._lock:
                self._subscribed_symbols.clear()
            log.info("ws_closed")
