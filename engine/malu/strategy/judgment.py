from __future__ import annotations

from decimal import Decimal

from malu.exchange.bybit_client import BybitClient
from malu.exchange.models import Category
from malu.strategy.base import JudgmentModule, JudgmentResult, Signal
from malu.utils.logger import get_logger

log = get_logger("judgment")


class BBRSIJudgment(JudgmentModule):
    """Bollinger Band + RSI based judgment.

    Params:
        bb_period: int (default 20)
        bb_std: float (default 2.0)
        rsi_period: int (default 14)
        rsi_oversold: float (default 30)
        rsi_overbought: float (default 70)
    """

    def evaluate_from_candles(self, closes: list[Decimal]) -> JudgmentResult:
        """Run BB+RSI judgment on a list of close prices (oldest-first).

        Pure calculation with no I/O — used by both live evaluate() and backtesting.
        """
        if len(closes) < 14:
            return JudgmentResult(signal=Signal.HOLD, reason="insufficient data")

        rsi_period = self.params.get("rsi_period", 14)
        rsi = self._calc_rsi(closes, rsi_period)

        bb_period = self.params.get("bb_period", 20)
        bb_std = Decimal(str(self.params.get("bb_std", 2.0)))
        upper, lower = self._calc_bb(closes, bb_period, bb_std)

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
        import asyncio

        klines = await asyncio.to_thread(
            client._client.get_kline,
            category="linear",
            symbol=symbol,
            interval="15",
            limit=self.params.get("bb_period", 20) + 5,
        )
        candles = klines["result"]["list"]
        closes = [Decimal(c[4]) for c in reversed(candles)]  # oldest first

        # Use real-time price from WebSocket if available
        if market_data:
            last_price = market_data.get_last_price(symbol)
            if last_price and closes:
                closes[-1] = last_price

        return self.evaluate_from_candles(closes)

    @staticmethod
    def _calc_rsi(closes: list[Decimal], period: int) -> float:
        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [max(d, Decimal("0")) for d in deltas[-period:]]
        losses = [abs(min(d, Decimal("0"))) for d in deltas[-period:]]
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100.0
        rs = float(avg_gain / avg_loss)
        return 100.0 - (100.0 / (1.0 + rs))

    @staticmethod
    def _calc_bb(
        closes: list[Decimal], period: int, num_std: Decimal
    ) -> tuple[Decimal, Decimal]:
        window = closes[-period:]
        mean = sum(window) / period
        variance = sum((x - mean) ** 2 for x in window) / period
        std = variance ** Decimal("0.5")
        return mean + num_std * std, mean - num_std * std
