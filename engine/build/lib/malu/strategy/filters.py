"""Market condition filter modules."""

from __future__ import annotations

from decimal import Decimal

from malu.exchange.bybit_client import BybitClient
from malu.strategy.base import FilterModule, FilterResult, Signal
from malu.strategy import indicators as ind
from malu.utils.logger import get_logger

log = get_logger("filter")


class TrendFilter(FilterModule):
    """Only allow trades in direction of long-term trend (trend_filter).

    Params:
        ema_period: int (default 200)
        interval: str (default "D")
    """

    async def check(self, symbol: str, signal: Signal, client: BybitClient, market_data=None) -> FilterResult:
        interval = self.params.get("interval", "D")
        ema_period = self.params.get("ema_period", 200)

        from malu.strategy.judgment import _get_ohlcv
        _, _, _, closes, _ = await _get_ohlcv(symbol, client, market_data, interval, ema_period + 5)

        if len(closes) < ema_period:
            return FilterResult(allowed=True, reason="insufficient data for trend filter")

        ema = ind.calc_ema(closes, ema_period)
        price = closes[-1]

        if signal == Signal.LONG and price < ema[-1]:
            return FilterResult(allowed=False, reason=f"price below {ema_period} EMA on {interval}, long blocked")
        elif signal == Signal.SHORT and price > ema[-1]:
            return FilterResult(allowed=False, reason=f"price above {ema_period} EMA on {interval}, short blocked")

        return FilterResult(allowed=True, reason="trend aligned")


class RegimeFilter(FilterModule):
    """Block trades that don't match current market regime (regime_filter).

    Params:
        adx_period: int (default 14)
        trending_threshold: float (default 25)
        ranging_threshold: float (default 20)
        interval: str (default "15")
        trend_entries: list[str] (default ["ema_cross","macd_cross","bb_squeeze"])
        range_entries: list[str] (default ["bb_rsi","rsi_divergence"])
    """

    async def check(self, symbol: str, signal: Signal, client: BybitClient, market_data=None) -> FilterResult:
        interval = self.params.get("interval", "15")
        adx_period = self.params.get("adx_period", 14)

        from malu.strategy.judgment import _get_ohlcv
        _, highs, lows, closes, _ = await _get_ohlcv(symbol, client, market_data, interval, adx_period * 3)

        adx = ind.calc_adx(highs, lows, closes, adx_period)
        trending = self.params.get("trending_threshold", 25)
        ranging = self.params.get("ranging_threshold", 20)

        if adx > trending:
            regime = "trending"
        elif adx < ranging:
            regime = "ranging"
        else:
            regime = "transitional"

        # This filter doesn't block by itself — it provides regime info
        # The bot can use this with entry module name matching
        return FilterResult(allowed=True, reason=f"regime={regime}, ADX={adx:.1f}")


class VolatilityFilter(FilterModule):
    """Block trades during extreme volatility (volatility_filter).

    Params:
        atr_period: int (default 14)
        max_atr_ratio: float (default 5.0, % - block above this)
        reduce_at: float (default 3.0, % - reduce size above this)
        interval: str (default "15")
    """

    async def check(self, symbol: str, signal: Signal, client: BybitClient, market_data=None) -> FilterResult:
        interval = self.params.get("interval", "15")
        atr_period = self.params.get("atr_period", 14)

        from malu.strategy.judgment import _get_ohlcv
        _, highs, lows, closes, _ = await _get_ohlcv(symbol, client, market_data, interval, atr_period + 5)

        atr = ind.calc_atr(highs, lows, closes, atr_period)
        price = closes[-1] if closes else Decimal("1")
        atr_ratio = float(atr / price * 100) if price > 0 else 0

        max_ratio = self.params.get("max_atr_ratio", 5.0)
        if atr_ratio > max_ratio:
            return FilterResult(allowed=False, reason=f"extreme volatility: ATR/Price={atr_ratio:.2f}% > {max_ratio}%")

        return FilterResult(allowed=True, reason=f"volatility OK: ATR/Price={atr_ratio:.2f}%")
