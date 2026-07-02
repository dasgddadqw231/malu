"""Position sizing modules."""

from __future__ import annotations

from decimal import Decimal

from malu.exchange.bybit_client import BybitClient
from malu.strategy.base import SizingModule, SizingResult, Signal
from malu.strategy import indicators as ind
from malu.utils.logger import get_logger

log = get_logger("sizing")


class FixedFractionSizing(SizingModule):
    """Fixed percentage of available budget (fixed_fraction).

    Params:
        size_pct: float (default 50, percent of budget)
        leverage: int (default 1) — injected by Bot at init
    """

    async def calculate(self, symbol: str, available_budget: Decimal, signal: Signal, client: BybitClient, market_data=None) -> SizingResult:
        pct = Decimal(str(self.params.get("size_pct", 50))) / Decimal("100")
        leverage = int(self.params.get("leverage", 1))
        # Margin to allocate (budget portion). Leverage amplifies notional on exchange side.
        amount = available_budget * pct
        return SizingResult(trade_amount=amount, reason=f"fixed {float(pct*100):.0f}% x{leverage}lev = {amount} margin")


class RiskBasedSizing(SizingModule):
    """Risk-based: max loss per trade = N% of capital (risk_based).

    With leverage, a price move of stop_loss_pct results in an actual loss of
    stop_loss_pct * leverage on your margin. So we must shrink position size
    accordingly: amount = max_loss / (stop_pct * leverage).

    Params:
        risk_per_trade: float (default 1.0, %)
        stop_loss_pct: float (default 2.0, % - estimated stop distance)
        leverage: int (default 1) — injected by Bot at init
    """

    async def calculate(self, symbol: str, available_budget: Decimal, signal: Signal, client: BybitClient, market_data=None) -> SizingResult:
        risk_pct = Decimal(str(self.params.get("risk_per_trade", 1.0))) / Decimal("100")
        stop_pct = Decimal(str(self.params.get("stop_loss_pct", 2.0))) / Decimal("100")
        leverage = int(self.params.get("leverage", 1))

        if stop_pct <= 0:
            stop_pct = Decimal("0.02")

        max_loss = available_budget * risk_pct
        # With leverage, loss on margin = price_change% * leverage
        # So: amount = max_loss / (stop_pct * leverage)
        effective_stop = stop_pct * Decimal(str(leverage))
        amount = max_loss / effective_stop
        # Cap at available budget
        amount = min(amount, available_budget)

        return SizingResult(
            trade_amount=amount,
            reason=f"risk {float(risk_pct*100):.1f}%, stop {float(stop_pct*100):.1f}% x{leverage}lev -> {amount} margin",
        )


class VolatilityAdjustedSizing(SizingModule):
    """ATR-based volatility-adjusted sizing (volatility_adjusted).

    With leverage, the effective stop distance on margin is amplified,
    so position size is reduced proportionally.

    Params:
        risk_per_trade: float (default 1.0, %)
        atr_period: int (default 14)
        atr_multiple: float (default 2.0, stop distance in ATR units)
        interval: str (default "15")
        leverage: int (default 1) — injected by Bot at init
    """

    async def calculate(self, symbol: str, available_budget: Decimal, signal: Signal, client: BybitClient, market_data=None) -> SizingResult:
        risk_pct = Decimal(str(self.params.get("risk_per_trade", 1.0))) / Decimal("100")
        atr_period = self.params.get("atr_period", 14)
        atr_mult = Decimal(str(self.params.get("atr_multiple", 2.0)))
        interval = self.params.get("interval", "15")
        leverage = int(self.params.get("leverage", 1))

        from malu.strategy.judgment import _get_ohlcv
        _, highs, lows, closes, _ = await _get_ohlcv(symbol, client, market_data, interval, atr_period + 5)

        atr = ind.calc_atr(highs, lows, closes, atr_period)
        price = closes[-1] if closes else Decimal("1")

        if atr <= 0 or price <= 0:
            stop_dist = price * Decimal("0.02")
        else:
            stop_dist = atr * atr_mult

        stop_pct = stop_dist / price if price > 0 else Decimal("0.02")
        # With leverage, effective loss on margin = stop_pct * leverage
        effective_stop = stop_pct * Decimal(str(leverage))
        max_loss = available_budget * risk_pct
        amount = max_loss / effective_stop if effective_stop > 0 else available_budget * Decimal("0.1")
        amount = min(amount, available_budget)

        atr_ratio = float(atr / price * 100) if price > 0 else 0
        return SizingResult(
            trade_amount=amount,
            reason=f"vol-adj: ATR/Price={atr_ratio:.2f}%, stop={float(stop_pct*100):.2f}% x{leverage}lev -> {amount} margin",
        )
