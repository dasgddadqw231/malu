from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass
class TickerData:
    """Snapshot of ticker data from Bybit tickers topic."""

    symbol: str = ""
    last_price: Decimal = Decimal("0")
    mark_price: Decimal = Decimal("0")
    index_price: Decimal = Decimal("0")
    bid1_price: Decimal = Decimal("0")
    ask1_price: Decimal = Decimal("0")
    open_interest: Decimal = Decimal("0")
    open_interest_value: Decimal = Decimal("0")
    funding_rate: Decimal = Decimal("0")
    next_funding_time: int = 0
    high_price_24h: Decimal = Decimal("0")
    low_price_24h: Decimal = Decimal("0")
    volume_24h: Decimal = Decimal("0")
    turnover_24h: Decimal = Decimal("0")
    price_change_pct_24h: str = ""
    updated_at: float = 0.0


@dataclass
class OrderbookData:
    """Orderbook snapshot."""

    symbol: str = ""
    bids: list[list[str]] = field(default_factory=list)  # [[price, qty], ...]
    asks: list[list[str]] = field(default_factory=list)
    update_id: int = 0
    seq: int = 0
    updated_at: float = 0.0


@dataclass
class KlineBar:
    """Single kline bar."""

    timestamp: int = 0
    open: Decimal = Decimal("0")
    high: Decimal = Decimal("0")
    low: Decimal = Decimal("0")
    close: Decimal = Decimal("0")
    volume: Decimal = Decimal("0")
    turnover: Decimal = Decimal("0")
    confirmed: bool = False


class MarketDataStore:
    """Thread-safe in-memory cache for real-time market data.

    Writes come from pybit's daemon thread (via BybitWSClient callbacks).
    Reads come from asyncio tasks (bot cycles, strategies).
    """

    def __init__(self, trade_buffer_size: int = 200):
        self._lock = threading.Lock()
        self._trade_buffer_size = trade_buffer_size

        self._tickers: dict[str, TickerData] = {}
        self._orderbooks: dict[str, OrderbookData] = {}
        self._trades: dict[str, deque] = {}
        self._klines: dict[str, dict[str, KlineBar]] = {}  # {symbol: {interval: bar}}

    # ── Write methods (called from pybit thread) ──

    def update_ticker(self, symbol: str, data: dict) -> None:
        with self._lock:
            ticker = self._tickers.get(symbol) or TickerData(symbol=symbol)
            if "lastPrice" in data:
                ticker.last_price = Decimal(data["lastPrice"])
            if "markPrice" in data:
                ticker.mark_price = Decimal(data["markPrice"])
            if "indexPrice" in data:
                ticker.index_price = Decimal(data["indexPrice"])
            if "bid1Price" in data:
                ticker.bid1_price = Decimal(data["bid1Price"])
            if "ask1Price" in data:
                ticker.ask1_price = Decimal(data["ask1Price"])
            if "openInterest" in data:
                ticker.open_interest = Decimal(data["openInterest"])
            if "openInterestValue" in data:
                ticker.open_interest_value = Decimal(data["openInterestValue"])
            if "fundingRate" in data:
                ticker.funding_rate = Decimal(data["fundingRate"])
            if "nextFundingTime" in data:
                ticker.next_funding_time = int(data["nextFundingTime"])
            if "highPrice24h" in data:
                ticker.high_price_24h = Decimal(data["highPrice24h"])
            if "lowPrice24h" in data:
                ticker.low_price_24h = Decimal(data["lowPrice24h"])
            if "volume24h" in data:
                ticker.volume_24h = Decimal(data["volume24h"])
            if "turnover24h" in data:
                ticker.turnover_24h = Decimal(data["turnover24h"])
            if "price24hPcnt" in data:
                ticker.price_change_pct_24h = data["price24hPcnt"]
            ticker.updated_at = time.time()
            self._tickers[symbol] = ticker

    def update_orderbook(self, symbol: str, data: dict) -> None:
        with self._lock:
            ob = self._orderbooks.get(symbol) or OrderbookData(symbol=symbol)
            ob.bids = data.get("b", ob.bids)
            ob.asks = data.get("a", ob.asks)
            ob.update_id = data.get("u", ob.update_id)
            ob.seq = data.get("seq", ob.seq)
            ob.updated_at = time.time()
            self._orderbooks[symbol] = ob

    def update_trades(self, symbol: str, data: list[dict]) -> None:
        with self._lock:
            if symbol not in self._trades:
                self._trades[symbol] = deque(maxlen=self._trade_buffer_size)
            for trade in data:
                self._trades[symbol].append(trade)

    def update_kline(self, symbol: str, interval: str, data: list[dict]) -> None:
        with self._lock:
            if symbol not in self._klines:
                self._klines[symbol] = {}
            for bar_data in data:
                bar = KlineBar(
                    timestamp=int(bar_data["start"]),
                    open=Decimal(bar_data["open"]),
                    high=Decimal(bar_data["high"]),
                    low=Decimal(bar_data["low"]),
                    close=Decimal(bar_data["close"]),
                    volume=Decimal(bar_data["volume"]),
                    turnover=Decimal(bar_data["turnover"]),
                    confirmed=bar_data.get("confirm", False),
                )
                self._klines[symbol][interval] = bar

    # ── Read methods (called from asyncio tasks) ──

    def get_ticker(self, symbol: str) -> TickerData | None:
        with self._lock:
            t = self._tickers.get(symbol)
            if t:
                return TickerData(**t.__dict__)
            return None

    def get_orderbook(self, symbol: str) -> OrderbookData | None:
        with self._lock:
            ob = self._orderbooks.get(symbol)
            if ob:
                return OrderbookData(
                    symbol=ob.symbol,
                    bids=list(ob.bids),
                    asks=list(ob.asks),
                    update_id=ob.update_id,
                    seq=ob.seq,
                    updated_at=ob.updated_at,
                )
            return None

    def get_recent_trades(self, symbol: str, limit: int = 50) -> list[dict]:
        with self._lock:
            trades = self._trades.get(symbol)
            if not trades:
                return []
            return list(trades)[-limit:]

    def get_latest_kline(self, symbol: str, interval: str) -> KlineBar | None:
        with self._lock:
            klines = self._klines.get(symbol, {})
            bar = klines.get(interval)
            if bar:
                return KlineBar(**bar.__dict__)
            return None

    def get_last_price(self, symbol: str) -> Decimal | None:
        with self._lock:
            t = self._tickers.get(symbol)
            return t.last_price if t and t.last_price > 0 else None

    def has_data(self, symbol: str) -> bool:
        """Check if we have received any data for this symbol."""
        with self._lock:
            return symbol in self._tickers

    def get_symbols(self) -> list[str]:
        with self._lock:
            return list(self._tickers.keys())
