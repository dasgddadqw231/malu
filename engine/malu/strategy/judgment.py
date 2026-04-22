from __future__ import annotations

import asyncio
from decimal import Decimal

from malu.exchange.bybit_client import BybitClient
from malu.exchange.models import Category
from malu.strategy.base import JudgmentModule, JudgmentResult, Signal
from malu.strategy import indicators as ind
from malu.utils.logger import get_logger

log = get_logger("judgment")


def _get_candles_from_store(market_data, symbol: str, interval: str, limit: int) -> list | None:
    """Try to get kline history from MarketDataStore ring buffer."""
    if market_data is None:
        return None
    get_history = getattr(market_data, "get_kline_history", None)
    if get_history is None:
        return None
    bars = get_history(symbol, interval, limit)
    if not bars or len(bars) < limit:
        return None
    return bars


async def _fetch_candles_rest(client: BybitClient, symbol: str, interval: str, limit: int):
    """Fallback: fetch candles via REST API."""
    klines = await asyncio.to_thread(
        client._client.get_kline,
        category="linear",
        symbol=symbol,
        interval=interval,
        limit=limit,
    )
    candles = klines["result"]["list"]
    return list(reversed(candles))  # oldest first


def _extract_ohlcv(candles, from_store: bool):
    """Extract OHLCV lists from candles (either KlineBar objects or raw API lists)."""
    if from_store:
        opens = [c.open for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        closes = [c.close for c in candles]
        volumes = [c.volume for c in candles]
    else:
        opens = [Decimal(c[1]) for c in candles]
        highs = [Decimal(c[2]) for c in candles]
        lows = [Decimal(c[3]) for c in candles]
        closes = [Decimal(c[4]) for c in candles]
        volumes = [Decimal(c[5]) for c in candles]
    return opens, highs, lows, closes, volumes


async def _get_ohlcv(symbol: str, client: BybitClient, market_data, interval: str, limit: int):
    """Get OHLCV data, preferring store, falling back to REST."""
    bars = _get_candles_from_store(market_data, symbol, interval, limit)
    if bars:
        o, h, l, c, v = _extract_ohlcv(bars, from_store=True)
        # Override last close with real-time price
        if market_data:
            last_price = market_data.get_last_price(symbol)
            if last_price and c:
                c[-1] = last_price
        return o, h, l, c, v

    candles = await _fetch_candles_rest(client, symbol, interval, limit)
    o, h, l, c, v = _extract_ohlcv(candles, from_store=False)
    if market_data:
        last_price = market_data.get_last_price(symbol)
        if last_price and c:
            c[-1] = last_price
    return o, h, l, c, v


class BBRSIJudgment(JudgmentModule):
    """Bollinger Band + RSI mean reversion (bb_reversal).

    Params:
        bb_period: int (default 20)
        bb_std: float (default 2.0)
        rsi_period: int (default 14)
        rsi_oversold: float (default 30)
        rsi_overbought: float (default 70)
        interval: str (default "15")
    """

    def evaluate_from_candles(self, closes: list[Decimal]) -> JudgmentResult:
        if len(closes) < 14:
            return JudgmentResult(signal=Signal.HOLD, reason="insufficient data")

        rsi_period = self.params.get("rsi_period", 14)
        rsi = ind.calc_rsi(closes, rsi_period)

        bb_period = self.params.get("bb_period", 20)
        bb_std = self.params.get("bb_std", 2.0)
        upper, middle, lower = ind.calc_bb(closes, bb_period, bb_std)

        current_price = closes[-1]
        oversold = self.params.get("rsi_oversold", 30)
        overbought = self.params.get("rsi_overbought", 70)

        if current_price <= lower and rsi < oversold:
            return JudgmentResult(
                signal=Signal.LONG,
                confidence=min(1.0, (oversold - rsi) / oversold),
                reason=f"price at lower BB, RSI={rsi:.1f}",
            )
        elif current_price >= upper and rsi > overbought:
            return JudgmentResult(
                signal=Signal.SHORT,
                confidence=min(1.0, (rsi - overbought) / (100 - overbought)),
                reason=f"price at upper BB, RSI={rsi:.1f}",
            )

        return JudgmentResult(signal=Signal.HOLD, reason=f"RSI={rsi:.1f}, no signal")

    async def evaluate(self, symbol: str, client: BybitClient, market_data=None) -> JudgmentResult:
        interval = self.params.get("interval", "15")
        limit = self.params.get("bb_period", 20) + 5
        _, _, _, closes, _ = await _get_ohlcv(symbol, client, market_data, interval, limit)
        return self.evaluate_from_candles(closes)


class BBSqueezeJudgment(JudgmentModule):
    """Bollinger Band Squeeze Breakout (bb_squeeze).

    Enters when BB width contracts to extreme low, then price breaks out with volume.

    Params:
        bb_period: int (default 20)
        bb_std: float (default 2.0)
        squeeze_lookback: int (default 48)
        squeeze_percentile: float (default 20, bottom N%)
        volume_multiple: float (default 1.5)
        interval: str (default "15")
    """

    async def evaluate(self, symbol: str, client: BybitClient, market_data=None) -> JudgmentResult:
        interval = self.params.get("interval", "15")
        lookback = self.params.get("squeeze_lookback", 48)
        bb_period = self.params.get("bb_period", 20)
        limit = max(lookback, bb_period) + 10

        _, _, _, closes, volumes = await _get_ohlcv(symbol, client, market_data, interval, limit)

        if len(closes) < lookback:
            return JudgmentResult(signal=Signal.HOLD, reason="insufficient data")

        bb_std = self.params.get("bb_std", 2.0)
        vol_mult = self.params.get("volume_multiple", 1.5)
        sq_pct = self.params.get("squeeze_percentile", 20)

        # Calculate BandWidth history
        widths = []
        for i in range(bb_period, len(closes) + 1):
            w = ind.calc_bb_width(closes[:i], bb_period, bb_std)
            widths.append(w)

        if len(widths) < 2:
            return JudgmentResult(signal=Signal.HOLD, reason="not enough width data")

        # Check squeeze: current width in bottom N% of recent history
        recent_widths = sorted(widths[-lookback:])
        threshold_idx = max(1, int(len(recent_widths) * sq_pct / 100))
        squeeze_threshold = recent_widths[threshold_idx - 1]

        prev_width = widths[-2]
        curr_width = widths[-1]

        # Was in squeeze, now expanding
        in_squeeze = prev_width <= squeeze_threshold
        expanding = curr_width > prev_width

        if not (in_squeeze and expanding):
            return JudgmentResult(signal=Signal.HOLD, reason=f"no squeeze breakout, width={float(curr_width):.4f}")

        # Volume confirmation
        avg_vol = ind.calc_sma(volumes, 20)
        vol_ok = volumes[-1] >= avg_vol * Decimal(str(vol_mult)) if avg_vol > 0 else False

        if not vol_ok:
            return JudgmentResult(signal=Signal.HOLD, reason="squeeze breakout but low volume")

        # Direction: which band did price break?
        upper, middle, lower = ind.calc_bb(closes, bb_period, bb_std)
        price = closes[-1]

        if price > upper:
            return JudgmentResult(signal=Signal.LONG, confidence=0.7, reason=f"BB squeeze breakout UP, width={float(curr_width):.4f}")
        elif price < lower:
            return JudgmentResult(signal=Signal.SHORT, confidence=0.7, reason=f"BB squeeze breakout DOWN, width={float(curr_width):.4f}")

        return JudgmentResult(signal=Signal.HOLD, reason="squeeze expanding but price inside bands")


class EMACrossJudgment(JudgmentModule):
    """EMA Crossover trend following (ema_cross).

    Params:
        fast_period: int (default 9)
        slow_period: int (default 21)
        trend_ema: int (default 200, 0 to disable)
        require_trend: bool (default True)
        interval: str (default "15")
    """

    def evaluate_from_candles(self, closes: list[Decimal]) -> JudgmentResult:
        fast = self.params.get("fast_period", 9)
        slow = self.params.get("slow_period", 21)

        if len(closes) < slow + 2:
            return JudgmentResult(signal=Signal.HOLD, reason="insufficient data")

        require_trend = self.params.get("require_trend", True)
        trend_ema_period = self.params.get("trend_ema", 200)

        direction, just_crossed = ind.detect_ema_cross(closes, fast, slow)

        if not just_crossed:
            return JudgmentResult(signal=Signal.HOLD, reason=f"EMA {fast}/{slow} no cross, trend={direction}")

        if require_trend and trend_ema_period and len(closes) >= trend_ema_period + 1:
            trend_ema = ind.calc_ema(closes, trend_ema_period)
            price = closes[-1]
            if direction == "long" and price < trend_ema[-1]:
                return JudgmentResult(signal=Signal.HOLD, reason=f"EMA cross long but below {trend_ema_period} EMA")
            elif direction == "short" and price > trend_ema[-1]:
                return JudgmentResult(signal=Signal.HOLD, reason=f"EMA cross short but above {trend_ema_period} EMA")

        signal = Signal.LONG if direction == "long" else Signal.SHORT
        return JudgmentResult(signal=signal, confidence=0.6, reason=f"EMA {fast}/{slow} cross {direction}")

    async def evaluate(self, symbol: str, client: BybitClient, market_data=None) -> JudgmentResult:
        interval = self.params.get("interval", "15")
        trend_ema_period = self.params.get("trend_ema", 200)
        slow = self.params.get("slow_period", 21)
        limit = max(slow, trend_ema_period if trend_ema_period else slow) + 10

        _, _, _, closes, _ = await _get_ohlcv(symbol, client, market_data, interval, limit)
        return self.evaluate_from_candles(closes)


class MACDCrossJudgment(JudgmentModule):
    """MACD Crossover (macd_cross).

    Params:
        fast_ema: int (default 12)
        slow_ema: int (default 26)
        signal_period: int (default 9)
        require_zero_cross: bool (default False)
        interval: str (default "15")
    """

    def evaluate_from_candles(self, closes: list[Decimal]) -> JudgmentResult:
        fast = self.params.get("fast_ema", 12)
        slow = self.params.get("slow_ema", 26)
        sig = self.params.get("signal_period", 9)
        require_zero = self.params.get("require_zero_cross", False)

        if len(closes) < slow + sig:
            return JudgmentResult(signal=Signal.HOLD, reason="insufficient data for MACD")

        macd_val, signal_val, hist = ind.calc_macd(closes, fast, slow, sig)
        prev_macd, prev_signal, prev_hist = ind.calc_macd(closes[:-1], fast, slow, sig)

        curr_diff = macd_val - signal_val
        prev_diff = prev_macd - prev_signal

        if curr_diff > 0 and prev_diff <= 0:
            if require_zero and macd_val > 0:
                return JudgmentResult(signal=Signal.HOLD, reason="MACD bullish cross but above zero line")
            strength = "strong" if macd_val < 0 else "normal"
            return JudgmentResult(signal=Signal.LONG, confidence=0.6, reason=f"MACD bullish cross ({strength})")
        elif curr_diff < 0 and prev_diff >= 0:
            if require_zero and macd_val < 0:
                return JudgmentResult(signal=Signal.HOLD, reason="MACD bearish cross but below zero line")
            strength = "strong" if macd_val > 0 else "normal"
            return JudgmentResult(signal=Signal.SHORT, confidence=0.6, reason=f"MACD bearish cross ({strength})")

        return JudgmentResult(signal=Signal.HOLD, reason=f"MACD no cross, hist={float(hist):.4f}")

    async def evaluate(self, symbol: str, client: BybitClient, market_data=None) -> JudgmentResult:
        interval = self.params.get("interval", "15")
        slow = self.params.get("slow_ema", 26)
        sig = self.params.get("signal_period", 9)
        limit = slow + sig + 15

        _, _, _, closes, _ = await _get_ohlcv(symbol, client, market_data, interval, limit)
        return self.evaluate_from_candles(closes)


class RSIDivergenceJudgment(JudgmentModule):
    """RSI Divergence reversal detection (rsi_divergence).

    Params:
        rsi_period: int (default 14)
        lookback: int (default 20)
        min_bars_between: int (default 5)
        confirmation: bool (default True)
        interval: str (default "15")
    """

    async def evaluate(self, symbol: str, client: BybitClient, market_data=None) -> JudgmentResult:
        interval = self.params.get("interval", "15")
        lookback = self.params.get("lookback", 20)
        rsi_period = self.params.get("rsi_period", 14)
        limit = lookback + rsi_period + 10

        _, _, _, closes, _ = await _get_ohlcv(symbol, client, market_data, interval, limit)

        if len(closes) < lookback + rsi_period:
            return JudgmentResult(signal=Signal.HOLD, reason="insufficient data")

        min_bars = self.params.get("min_bars_between", 5)
        confirmation = self.params.get("confirmation", True)

        # Calculate RSI for each point in lookback window
        rsi_values = []
        for i in range(lookback):
            end_idx = len(closes) - lookback + i + 1
            rsi_val = ind.calc_rsi(closes[:end_idx], rsi_period)
            rsi_values.append(rsi_val)

        price_window = closes[-lookback:]

        # Find local minima/maxima in price
        def find_pivots(series, find_min=True):
            pivots = []
            for i in range(1, len(series) - 1):
                if find_min and series[i] <= series[i - 1] and series[i] <= series[i + 1]:
                    pivots.append(i)
                elif not find_min and series[i] >= series[i - 1] and series[i] >= series[i + 1]:
                    pivots.append(i)
            return pivots

        # Bullish divergence: price lower low, RSI higher low
        lows = find_pivots(price_window, find_min=True)
        if len(lows) >= 2:
            for i in range(len(lows) - 1):
                idx1, idx2 = lows[i], lows[-1]
                if idx2 - idx1 >= min_bars:
                    if price_window[idx2] < price_window[idx1] and rsi_values[idx2] > rsi_values[idx1]:
                        current_rsi = rsi_values[-1]
                        if confirmation and current_rsi < 30:
                            return JudgmentResult(signal=Signal.HOLD, reason="bullish div but RSI not confirmed above 30")
                        return JudgmentResult(signal=Signal.LONG, confidence=0.65, reason=f"bullish RSI divergence, RSI={current_rsi:.1f}")

        # Bearish divergence: price higher high, RSI lower high
        highs = find_pivots(price_window, find_min=False)
        if len(highs) >= 2:
            for i in range(len(highs) - 1):
                idx1, idx2 = highs[i], highs[-1]
                if idx2 - idx1 >= min_bars:
                    if price_window[idx2] > price_window[idx1] and rsi_values[idx2] < rsi_values[idx1]:
                        current_rsi = rsi_values[-1]
                        if confirmation and current_rsi > 70:
                            return JudgmentResult(signal=Signal.HOLD, reason="bearish div but RSI not confirmed below 70")
                        return JudgmentResult(signal=Signal.SHORT, confidence=0.65, reason=f"bearish RSI divergence, RSI={current_rsi:.1f}")

        return JudgmentResult(signal=Signal.HOLD, reason="no divergence detected")


class BNFDipBuyJudgment(JudgmentModule):
    """BNF-style dip buying: enter long after deep drawdown with reversal confirmation.

    Strategy (inspired by BNF / 小手川隆):
      1. Price has dropped significantly from recent high (drawdown threshold)
      2. Volume surges at the bounce zone (selling climax → buying interest)
      3. Price stops making new lows (support formation)
      4. MACD histogram turns positive (momentum shift)

    Best used on daily (D) or 4-hour (240) timeframes.

    Params:
        drawdown_pct: float (default 30.0) — min % drop from high to consider
        drawdown_max_pct: float (default 45.0) — max % drop (avoid falling knives)
        high_lookback: int (default 120) — bars to find the recent high
        no_new_low_bars: int (default 5) — consecutive bars without new low
        volume_multiple: float (default 1.5) — volume vs 20-bar avg
        macd_fast: int (default 12)
        macd_slow: int (default 26)
        macd_signal: int (default 9)
        interval: str (default "D")
    """

    async def evaluate(self, symbol: str, client: BybitClient, market_data=None) -> JudgmentResult:
        interval = self.params.get("interval", "D")
        high_lookback = self.params.get("high_lookback", 120)
        macd_slow = self.params.get("macd_slow", 26)
        macd_signal = self.params.get("macd_signal", 9)
        limit = max(high_lookback, macd_slow + macd_signal + 15) + 10

        _, highs, lows, closes, volumes = await _get_ohlcv(
            symbol, client, market_data, interval, limit,
        )

        if len(closes) < macd_slow + macd_signal + 2:
            return JudgmentResult(signal=Signal.HOLD, reason="insufficient data for BNF")

        # --- Condition 1: Deep drawdown from recent high ---
        drawdown_pct = Decimal(str(self.params.get("drawdown_pct", 30.0)))
        drawdown_max_pct = Decimal(str(self.params.get("drawdown_max_pct", 45.0)))
        recent_high = max(highs[-high_lookback:])
        current_price = closes[-1]

        if recent_high == 0:
            return JudgmentResult(signal=Signal.HOLD, reason="no price data")

        drop_pct = (recent_high - current_price) / recent_high * 100

        if drop_pct < drawdown_pct:
            return JudgmentResult(
                signal=Signal.HOLD,
                reason=f"drawdown {float(drop_pct):.1f}% < {float(drawdown_pct)}% threshold",
            )
        if drop_pct > drawdown_max_pct:
            return JudgmentResult(
                signal=Signal.HOLD,
                reason=f"drawdown {float(drop_pct):.1f}% exceeds {float(drawdown_max_pct)}% max — falling knife",
            )

        # --- Condition 2: Volume surge ---
        vol_mult = Decimal(str(self.params.get("volume_multiple", 1.5)))
        avg_vol = ind.calc_sma(volumes, 20)
        vol_ok = avg_vol > 0 and volumes[-1] >= avg_vol * vol_mult

        if not vol_ok:
            return JudgmentResult(
                signal=Signal.HOLD,
                reason=f"drawdown OK ({float(drop_pct):.1f}%) but volume not surging",
            )

        # --- Condition 3: No new low for N bars ---
        no_new_low_bars = self.params.get("no_new_low_bars", 5)
        if len(lows) >= no_new_low_bars + 1:
            recent_bottom = min(lows[-(no_new_low_bars + 1):-1])  # low before current window
            has_new_low = any(l < recent_bottom for l in lows[-no_new_low_bars:])
        else:
            has_new_low = False

        if has_new_low:
            return JudgmentResult(
                signal=Signal.HOLD,
                reason=f"drawdown + volume OK but still making new lows",
            )

        # --- Condition 4: MACD histogram turns positive ---
        macd_fast = self.params.get("macd_fast", 12)
        _, _, hist = ind.calc_macd(closes, macd_fast, macd_slow, macd_signal)
        _, _, prev_hist = ind.calc_macd(closes[:-1], macd_fast, macd_slow, macd_signal)

        if not (hist > 0 and prev_hist <= 0):
            return JudgmentResult(
                signal=Signal.HOLD,
                reason=f"drawdown + volume + support OK, but MACD histogram not flipping positive (hist={float(hist):.4f})",
            )

        # --- All 4 conditions met → LONG ---
        confidence = min(1.0, float(drop_pct / 50))  # deeper dip → higher confidence
        return JudgmentResult(
            signal=Signal.LONG,
            confidence=confidence,
            reason=(
                f"BNF dip buy: {float(drop_pct):.1f}% drawdown, "
                f"vol {float(volumes[-1] / avg_vol):.1f}x avg, "
                f"no new low {no_new_low_bars} bars, MACD flipped positive"
            ),
        )
