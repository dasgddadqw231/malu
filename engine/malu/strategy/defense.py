from __future__ import annotations

import asyncio
import time
from decimal import Decimal

from malu.exchange.bybit_client import BybitClient
from malu.exchange.models import PositionInfo, Side
from malu.strategy.base import DefenseModule, DefenseResult
from malu.strategy import indicators as ind
from malu.utils.logger import get_logger

log = get_logger("defense")


def _calc_pnl_pct(position: PositionInfo, market_data=None) -> Decimal:
    """Calculate unrealised PnL % using real-time mark price if available."""
    unrealised_pnl = position.unrealised_pnl
    if market_data:
        ticker = market_data.get_ticker(position.symbol)
        if ticker and ticker.mark_price > 0:
            if position.side == Side.BUY:
                unrealised_pnl = (ticker.mark_price - position.entry_price) * position.size
            else:
                unrealised_pnl = (position.entry_price - ticker.mark_price) * position.size
    return (unrealised_pnl / (position.entry_price * position.size)) * 100


class FixedPctDefense(DefenseModule):
    """Fixed percentage stop-loss and take-profit (fixed_pct).

    Params:
        stop_loss_pct: float (default 5.0)
        take_profit_pct: float (default 10.0)
    """

    async def check(self, position: PositionInfo | None, client: BybitClient, market_data=None) -> DefenseResult:
        if position is None or position.size == 0:
            return DefenseResult(should_close=False)

        max_loss_pct = Decimal(str(self.params.get("stop_loss_pct", self.params.get("max_loss_pct", 5.0))))
        take_profit_pct = Decimal(str(self.params.get("take_profit_pct", 10.0)))
        pnl_pct = _calc_pnl_pct(position, market_data)

        if pnl_pct <= -max_loss_pct:
            log.warning("stop_loss_triggered", symbol=position.symbol, pnl_pct=str(pnl_pct))
            return DefenseResult(should_close=True, reason=f"stop loss: PnL {pnl_pct:.2f}% <= -{max_loss_pct}%")

        if pnl_pct >= take_profit_pct:
            log.info("take_profit_triggered", symbol=position.symbol, pnl_pct=str(pnl_pct))
            return DefenseResult(should_close=True, reason=f"take profit: PnL {pnl_pct:.2f}% >= {take_profit_pct}%")

        return DefenseResult(should_close=False)


# Keep backward compatibility alias
TrailingStopDefense = FixedPctDefense


class ATRStopDefense(DefenseModule):
    """ATR-based dynamic stop-loss and take-profit (atr_stop).

    Stop and TP levels are calculated at first check based on ATR at entry time.

    Params:
        atr_period: int (default 14)
        stop_atr_multiple: float (default 2.0)
        tp_atr_multiple: float (default 3.0)
        interval: str (default "15")
    """

    def __init__(self, params: dict):
        super().__init__(params)
        self._stop_price: Decimal | None = None
        self._tp_price: Decimal | None = None
        self._entry_symbol: str | None = None

    async def check(self, position: PositionInfo | None, client: BybitClient, market_data=None) -> DefenseResult:
        if position is None or position.size == 0:
            self._stop_price = None
            self._tp_price = None
            self._entry_symbol = None
            return DefenseResult(should_close=False)

        # Calculate levels on first check for this position
        if self._stop_price is None or self._entry_symbol != position.symbol:
            await self._calc_levels(position, client, market_data)
            self._entry_symbol = position.symbol

        # Get current price
        current_price = position.entry_price  # fallback
        if market_data:
            ticker = market_data.get_ticker(position.symbol)
            if ticker and ticker.mark_price > 0:
                current_price = ticker.mark_price

        if position.side == Side.BUY:
            if current_price <= self._stop_price:
                pnl_pct = (current_price - position.entry_price) / position.entry_price * 100
                return DefenseResult(should_close=True, reason=f"ATR stop loss hit at {current_price}, PnL {pnl_pct:.2f}%")
            if current_price >= self._tp_price:
                pnl_pct = (current_price - position.entry_price) / position.entry_price * 100
                return DefenseResult(should_close=True, reason=f"ATR take profit hit at {current_price}, PnL {pnl_pct:.2f}%")
        else:
            if current_price >= self._stop_price:
                pnl_pct = (position.entry_price - current_price) / position.entry_price * 100
                return DefenseResult(should_close=True, reason=f"ATR stop loss hit at {current_price}, PnL {pnl_pct:.2f}%")
            if current_price <= self._tp_price:
                pnl_pct = (position.entry_price - current_price) / position.entry_price * 100
                return DefenseResult(should_close=True, reason=f"ATR take profit hit at {current_price}, PnL {pnl_pct:.2f}%")

        return DefenseResult(should_close=False)

    async def _calc_levels(self, position: PositionInfo, client: BybitClient, market_data):
        interval = self.params.get("interval", "15")
        atr_period = self.params.get("atr_period", 14)
        stop_mult = Decimal(str(self.params.get("stop_atr_multiple", 2.0)))
        tp_mult = Decimal(str(self.params.get("tp_atr_multiple", 3.0)))

        from malu.strategy.judgment import _get_ohlcv
        _, highs, lows, closes, _ = await _get_ohlcv(position.symbol, client, market_data, interval, atr_period + 5)

        atr = ind.calc_atr(highs, lows, closes, atr_period)
        if atr == 0:
            atr = position.entry_price * Decimal("0.02")  # fallback 2%

        entry = position.entry_price
        if position.side == Side.BUY:
            self._stop_price = entry - stop_mult * atr
            self._tp_price = entry + tp_mult * atr
        else:
            self._stop_price = entry + stop_mult * atr
            self._tp_price = entry - tp_mult * atr

        log.info("atr_levels_set", symbol=position.symbol, atr=str(atr),
                 stop=str(self._stop_price), tp=str(self._tp_price))


class TrailingATRDefense(DefenseModule):
    """True trailing stop using ATR (trailing_stop).

    Tracks the high-water mark and trails the stop behind it.

    Params:
        method: str ("atr" | "pct", default "atr")
        atr_multiple: float (default 2.0)
        trail_pct: float (default 3.0, used if method="pct")
        activate_after_pct: float (default 1.0, min profit before trailing starts)
        atr_period: int (default 14)
        interval: str (default "15")
    """

    def __init__(self, params: dict):
        super().__init__(params)
        self._high_water: Decimal | None = None
        self._low_water: Decimal | None = None
        self._trailing_active: bool = False
        self._atr_value: Decimal | None = None

    async def check(self, position: PositionInfo | None, client: BybitClient, market_data=None) -> DefenseResult:
        if position is None or position.size == 0:
            self._high_water = None
            self._low_water = None
            self._trailing_active = False
            self._atr_value = None
            return DefenseResult(should_close=False)

        current_price = position.entry_price
        if market_data:
            ticker = market_data.get_ticker(position.symbol)
            if ticker and ticker.mark_price > 0:
                current_price = ticker.mark_price

        pnl_pct = _calc_pnl_pct(position, market_data)
        activate_pct = Decimal(str(self.params.get("activate_after_pct", 1.0)))

        # Activate trailing after minimum profit
        if not self._trailing_active:
            if pnl_pct >= activate_pct:
                self._trailing_active = True
                self._high_water = current_price if position.side == Side.BUY else None
                self._low_water = current_price if position.side == Side.SELL else None
                # Calculate ATR once
                if self._atr_value is None and self.params.get("method", "atr") == "atr":
                    await self._calc_atr(position.symbol, client, market_data)
            return DefenseResult(should_close=False)

        # Update high/low water mark
        if position.side == Side.BUY:
            if self._high_water is None or current_price > self._high_water:
                self._high_water = current_price
            trail_dist = self._get_trail_distance()
            stop_level = self._high_water - trail_dist
            if current_price <= stop_level:
                return DefenseResult(should_close=True, reason=f"trailing stop: price {current_price} <= {stop_level} (high={self._high_water})")
        else:
            if self._low_water is None or current_price < self._low_water:
                self._low_water = current_price
            trail_dist = self._get_trail_distance()
            stop_level = self._low_water + trail_dist
            if current_price >= stop_level:
                return DefenseResult(should_close=True, reason=f"trailing stop: price {current_price} >= {stop_level} (low={self._low_water})")

        return DefenseResult(should_close=False)

    def _get_trail_distance(self) -> Decimal:
        method = self.params.get("method", "atr")
        if method == "atr" and self._atr_value:
            mult = Decimal(str(self.params.get("atr_multiple", 2.0)))
            return self._atr_value * mult
        else:
            pct = Decimal(str(self.params.get("trail_pct", 3.0)))
            ref = self._high_water or self._low_water or Decimal("1")
            return ref * pct / Decimal("100")

    async def _calc_atr(self, symbol: str, client: BybitClient, market_data):
        interval = self.params.get("interval", "15")
        atr_period = self.params.get("atr_period", 14)
        from malu.strategy.judgment import _get_ohlcv
        _, highs, lows, closes, _ = await _get_ohlcv(symbol, client, market_data, interval, atr_period + 5)
        self._atr_value = ind.calc_atr(highs, lows, closes, atr_period)


class TimeStopDefense(DefenseModule):
    """Time-based exit (time_stop).

    Exits if position has been held too long without reaching minimum profit.

    Params:
        max_seconds: int (default 3600, max hold time in seconds)
        min_profit_pct: float (default 0.5)
    """

    def __init__(self, params: dict):
        super().__init__(params)
        self._entry_time: float | None = None

    async def check(self, position: PositionInfo | None, client: BybitClient, market_data=None) -> DefenseResult:
        if position is None or position.size == 0:
            self._entry_time = None
            return DefenseResult(should_close=False)

        if self._entry_time is None:
            self._entry_time = time.time()
            return DefenseResult(should_close=False)

        elapsed = time.time() - self._entry_time
        max_seconds = self.params.get("max_seconds", 3600)
        min_profit = Decimal(str(self.params.get("min_profit_pct", 0.5)))

        if elapsed >= max_seconds:
            pnl_pct = _calc_pnl_pct(position, market_data)
            if pnl_pct < min_profit:
                return DefenseResult(
                    should_close=True,
                    reason=f"time stop: {elapsed:.0f}s elapsed, PnL {pnl_pct:.2f}% < {min_profit}%",
                )

        return DefenseResult(should_close=False)
