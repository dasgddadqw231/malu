from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from math import sqrt

from malu.backtest.data import FundingRecord, HistoricalCandle, HistoricalDataFetcher
from malu.exchange.bybit_client import BybitClient
from malu.strategy.base import JudgmentModule, Signal
from malu.utils.logger import get_logger

log = get_logger("backtest.simulator")

# Lazy import to avoid circular dependency
def _get_judgment_class(module_name: str) -> type[JudgmentModule]:
    from malu.strategy.judgment import (
        BBRSIJudgment, BBSqueezeJudgment, EMACrossJudgment,
        MACDCrossJudgment, RSIDivergenceJudgment,
    )
    registry: dict[str, type[JudgmentModule]] = {
        "bb_rsi": BBRSIJudgment,
        "bb_reversal": BBRSIJudgment,
        "bb_squeeze": BBSqueezeJudgment,
        "ema_cross": EMACrossJudgment,
        "macd_cross": MACDCrossJudgment,
        "rsi_divergence": RSIDivergenceJudgment,
    }
    return registry.get(module_name, BBRSIJudgment)

# Bybit funding timestamps: 00:00, 08:00, 16:00 UTC (every 8 hours)
_FUNDING_INTERVAL_MS = 8 * 60 * 60 * 1000


@dataclass
class BacktestConfig:
    symbol: str
    interval: str = "15"
    start_date: str = ""  # YYYY-MM-DD
    end_date: str = ""    # YYYY-MM-DD
    initial_capital: Decimal = Decimal("10000")
    strategy_config: dict = field(default_factory=dict)
    slippage_bps: int = 5        # basis points
    fee_rate: Decimal = Decimal("0.00055")  # Bybit taker 0.055%


@dataclass
class SimulatedTrade:
    entry_time: int
    exit_time: int
    side: str  # "Long" / "Short"
    entry_price: Decimal
    exit_price: Decimal
    qty: Decimal
    pnl: Decimal
    fee: Decimal
    funding_paid: Decimal
    exit_reason: str


@dataclass
class BacktestResult:
    config: BacktestConfig
    trades: list[SimulatedTrade]
    total_pnl: Decimal = Decimal("0")
    total_fees: Decimal = Decimal("0")
    total_funding: Decimal = Decimal("0")
    net_pnl: Decimal = Decimal("0")
    win_rate: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    total_trades: int = 0
    equity_curve: list[dict] = field(default_factory=list)


@dataclass
class _OpenPosition:
    side: str
    entry_price: Decimal
    qty: Decimal
    entry_time: int
    accumulated_funding: Decimal = Decimal("0")


class BacktestSimulator:
    """Bar-by-bar backtesting engine supporting all judgment modules."""

    def __init__(self, config: BacktestConfig):
        self.config = config

        # Extract strategy params (same format as BotConfig.strategy_config)
        judgment_cfg = config.strategy_config.get("judgment", {})
        module_name = judgment_cfg.get("module", "bb_rsi")
        judgment_cls = _get_judgment_class(module_name)
        self.judgment = judgment_cls(judgment_cfg.get("params", {}))

        defense_cfg = config.strategy_config.get("defense", {})
        defense_params = defense_cfg.get("params", {})
        self.defense_module = defense_cfg.get("module", "fixed_pct")

        # Fixed pct defense params
        self.max_loss_pct = Decimal(str(defense_params.get("max_loss_pct",
                                        defense_params.get("stop_loss_pct", 5.0))))
        self.take_profit_pct = Decimal(str(defense_params.get("take_profit_pct", 3.0)))

        # ATR defense params
        self.atr_period = defense_params.get("atr_period", 14)
        self.stop_atr_multiple = Decimal(str(defense_params.get("stop_atr_multiple", 2.0)))
        self.tp_atr_multiple = Decimal(str(defense_params.get("tp_atr_multiple", 3.0)))
        # Trailing ATR params
        self.trailing_activate_pct = Decimal(str(defense_params.get("activate_after_pct", 1.0)))

        action_cfg = config.strategy_config.get("action", {})
        action_params = action_cfg.get("params", {})
        self.position_size_pct = Decimal(str(action_params.get("position_size_pct", 95)))

        # --- Filter support: trend filter ---
        self.trend_filter_enabled = False
        self.trend_ema_period = 200
        self.trend_interval = "D"
        filters_cfg = config.strategy_config.get("filters", [])
        for f_cfg in filters_cfg:
            if f_cfg.get("module") == "trend_filter":
                self.trend_filter_enabled = True
                self.trend_ema_period = f_cfg.get("params", {}).get("ema_period", 200)
                self.trend_interval = f_cfg.get("params", {}).get("interval", "D")

        # --- Consecutive loss cooldown ---
        self.max_consecutive_losses = config.strategy_config.get(
            "max_consecutive_losses", 3
        )
        self.cooldown_bars = config.strategy_config.get("cooldown_bars", 48)  # 48 bars = 12h on 15m

    def run_from_candles(
        self,
        candles: list[HistoricalCandle],
        funding_rates: list[FundingRecord],
    ) -> BacktestResult:
        """Run backtest using pre-fetched data (no API calls). Used by optimizer."""
        return self._simulate(candles, funding_rates)

    async def run(self, client: BybitClient) -> BacktestResult:
        start_ms = self._date_to_ms(self.config.start_date)
        end_ms = self._date_to_ms(self.config.end_date)

        fetcher = HistoricalDataFetcher(client)
        candles = await fetcher.fetch_klines(
            self.config.symbol, self.config.interval, start_ms, end_ms
        )
        funding_rates = await fetcher.fetch_funding_rates(
            self.config.symbol, start_ms, end_ms
        )

        # Fetch daily candles for trend filter (with lookback warmup)
        daily_candles: list[HistoricalCandle] | None = None
        if self.trend_filter_enabled:
            warmup_days = self.trend_ema_period + 30  # extra buffer
            warmup_ms = warmup_days * 86_400_000
            daily_candles = await fetcher.fetch_klines(
                self.config.symbol, "D", start_ms - warmup_ms, end_ms
            )
            log.info("trend_filter_data", daily_bars=len(daily_candles),
                     ema_period=self.trend_ema_period)

        return self._simulate(candles, funding_rates, daily_candles=daily_candles)

    def _simulate(
        self,
        candles: list[HistoricalCandle],
        funding_rates: list[FundingRecord],
        daily_candles: list[HistoricalCandle] | None = None,
    ) -> BacktestResult:
        if len(candles) < 25:
            log.warning("insufficient_candles", count=len(candles))
            return BacktestResult(config=self.config, trades=[])

        # Build funding rate lookup: sorted list of (timestamp, rate)
        funding_lookup = [(f.timestamp, f.funding_rate) for f in funding_rates]

        # Build daily EMA for trend filter
        daily_ema_cache: dict[int, Decimal] = {}
        if self.trend_filter_enabled:
            # Prefer dedicated daily candles (with proper warmup) over aggregation
            source = daily_candles if daily_candles else candles
            daily_ema_cache = self._build_daily_ema(source)
            log.info("trend_filter_ema", days_available=len(daily_ema_cache),
                     required=self.trend_ema_period)

        lookback = self._calc_lookback()
        equity = self.config.initial_capital
        peak_equity = equity
        max_dd = Decimal("0")

        position: _OpenPosition | None = None
        trades: list[SimulatedTrade] = []
        equity_curve: list[dict] = []
        consecutive_losses = 0
        cooldown_remaining = 0

        # ATR/trailing state
        atr_stop_price: Decimal | None = None
        atr_tp_price: Decimal | None = None
        trailing_high: Decimal | None = None
        trailing_low: Decimal | None = None
        trailing_active = False

        for i in range(lookback, len(candles)):
            bar = candles[i]
            window_closes = [c.close for c in candles[i - lookback : i + 1]]

            # --- Defense check ---
            if position is not None:
                should_close = False
                reason = ""

                if self.defense_module == "fixed_pct":
                    pnl_pct = self._calc_pnl_pct(position, bar.close)
                    if pnl_pct <= -self.max_loss_pct:
                        should_close = True
                        reason = f"stop_loss: {pnl_pct:.2f}%"
                    elif pnl_pct >= self.take_profit_pct:
                        should_close = True
                        reason = f"take_profit: {pnl_pct:.2f}%"

                elif self.defense_module == "atr_stop":
                    if position.side == "Long":
                        if bar.close <= atr_stop_price:
                            pnl_pct = self._calc_pnl_pct(position, bar.close)
                            should_close = True
                            reason = f"atr_stop_loss: {pnl_pct:.2f}% (stop={float(atr_stop_price):.0f})"
                        elif bar.close >= atr_tp_price:
                            pnl_pct = self._calc_pnl_pct(position, bar.close)
                            should_close = True
                            reason = f"atr_take_profit: {pnl_pct:.2f}% (tp={float(atr_tp_price):.0f})"
                    else:
                        if bar.close >= atr_stop_price:
                            pnl_pct = self._calc_pnl_pct(position, bar.close)
                            should_close = True
                            reason = f"atr_stop_loss: {pnl_pct:.2f}% (stop={float(atr_stop_price):.0f})"
                        elif bar.close <= atr_tp_price:
                            pnl_pct = self._calc_pnl_pct(position, bar.close)
                            should_close = True
                            reason = f"atr_take_profit: {pnl_pct:.2f}% (tp={float(atr_tp_price):.0f})"

                elif self.defense_module == "trailing_atr":
                    pnl_pct = self._calc_pnl_pct(position, bar.close)
                    # First check fixed SL (always active)
                    if pnl_pct <= -self.max_loss_pct:
                        should_close = True
                        reason = f"trailing_stop_loss: {pnl_pct:.2f}%"
                    elif trailing_active:
                        # Update high/low water mark
                        if position.side == "Long":
                            if bar.close > trailing_high:
                                trailing_high = bar.close
                            trail_stop = trailing_high - atr_stop_price  # atr_stop_price stores ATR distance
                            if bar.close <= trail_stop:
                                should_close = True
                                reason = f"trailing_stop: price {float(bar.close):.0f} <= trail {float(trail_stop):.0f}"
                        else:
                            if bar.close < trailing_low:
                                trailing_low = bar.close
                            trail_stop = trailing_low + atr_stop_price
                            if bar.close >= trail_stop:
                                should_close = True
                                reason = f"trailing_stop: price {float(bar.close):.0f} >= trail {float(trail_stop):.0f}"
                    elif pnl_pct >= self.trailing_activate_pct:
                        trailing_active = True
                        trailing_high = bar.close
                        trailing_low = bar.close

                if should_close:
                    trade = self._close_position(position, bar, reason)
                    trades.append(trade)
                    equity += trade.pnl - trade.fee - trade.funding_paid
                    if trade.pnl <= 0:
                        consecutive_losses += 1
                        if consecutive_losses >= self.max_consecutive_losses:
                            cooldown_remaining = self.cooldown_bars
                    else:
                        consecutive_losses = 0
                    position = None
                    atr_stop_price = None
                    atr_tp_price = None
                    trailing_active = False

            # --- Apply funding ---
            if position is not None:
                funding_cost = self._calc_funding(
                    position, candles[i - 1].timestamp, bar.timestamp, funding_lookup
                )
                if funding_cost != 0:
                    position.accumulated_funding += funding_cost
                    equity -= funding_cost

            # --- Judgment (only if flat) ---
            if position is None:
                # Cooldown after consecutive losses
                if cooldown_remaining > 0:
                    cooldown_remaining -= 1
                else:
                    result = self.judgment.evaluate_from_candles(window_closes)

                    if result.signal in (Signal.LONG, Signal.SHORT):
                        # Trend filter: check daily EMA direction
                        if self.trend_filter_enabled and not self._check_trend_filter(
                            bar, result.signal, daily_ema_cache
                        ):
                            pass  # blocked by trend filter
                        else:
                            side = "Long" if result.signal == Signal.LONG else "Short"
                            entry_price = self._apply_slippage(bar.close, side, entry=True)
                            budget = equity * self.position_size_pct / 100
                            qty = budget / entry_price
                            entry_fee = qty * entry_price * self.config.fee_rate
                            equity -= entry_fee

                            position = _OpenPosition(
                                side=side,
                                entry_price=entry_price,
                                qty=qty,
                                entry_time=bar.timestamp,
                            )

                            # Set ATR-based SL/TP levels at entry
                            if self.defense_module in ("atr_stop", "trailing_atr"):
                                atr = self._calc_atr_from_candles(candles, i)
                                if self.defense_module == "atr_stop":
                                    if side == "Long":
                                        atr_stop_price = entry_price - self.stop_atr_multiple * atr
                                        atr_tp_price = entry_price + self.tp_atr_multiple * atr
                                    else:
                                        atr_stop_price = entry_price + self.stop_atr_multiple * atr
                                        atr_tp_price = entry_price - self.tp_atr_multiple * atr
                                else:  # trailing_atr
                                    atr_stop_price = self.stop_atr_multiple * atr  # store distance
                                    trailing_high = entry_price
                                    trailing_low = entry_price
                                    trailing_active = False

            # --- Track equity ---
            mark_equity = equity
            if position is not None:
                mark_equity += self._unrealised_pnl(position, bar.close)

            if mark_equity > peak_equity:
                peak_equity = mark_equity
            dd = (peak_equity - mark_equity) / peak_equity * 100 if peak_equity > 0 else Decimal("0")
            if dd > max_dd:
                max_dd = dd

            equity_curve.append({
                "timestamp": bar.timestamp,
                "equity": float(mark_equity),
            })

        # Force-close any open position at end
        if position is not None:
            trade = self._close_position(position, candles[-1], "end_of_backtest")
            trades.append(trade)
            equity += trade.pnl - trade.fee - trade.funding_paid

        # Calculate summary
        total_pnl = sum(t.pnl for t in trades)
        total_fees = sum(t.fee for t in trades)
        total_funding = sum(t.funding_paid for t in trades)
        net_pnl = total_pnl - total_fees - total_funding
        wins = sum(1 for t in trades if t.pnl > 0)
        win_rate = (wins / len(trades) * 100) if trades else 0.0

        # Sharpe ratio (from trade returns)
        sharpe = 0.0
        if len(trades) >= 2:
            returns = [float(t.pnl - t.fee - t.funding_paid) for t in trades]
            avg_ret = sum(returns) / len(returns)
            std_ret = sqrt(sum((r - avg_ret) ** 2 for r in returns) / (len(returns) - 1))
            if std_ret > 0:
                sharpe = avg_ret / std_ret * sqrt(len(returns))

        return BacktestResult(
            config=self.config,
            trades=trades,
            total_pnl=total_pnl,
            total_fees=total_fees,
            total_funding=total_funding,
            net_pnl=net_pnl,
            win_rate=win_rate,
            max_drawdown=float(max_dd),
            sharpe_ratio=sharpe,
            total_trades=len(trades),
            equity_curve=equity_curve,
        )

    # --- Helpers ---

    def _calc_lookback(self) -> int:
        """Calculate required lookback period based on judgment module params."""
        p = self.judgment.params
        # Cover all judgment modules
        periods = [
            p.get("bb_period", 20),
            p.get("slow_period", 21),
            p.get("slow_ema", 26) + p.get("signal_period", 9),
            p.get("rsi_period", 14),
            p.get("lookback", 20),
            p.get("trend_ema", 0),
        ]
        return max(periods) + 10

    def _build_daily_ema(
        self, candles: list[HistoricalCandle]
    ) -> dict[int, Decimal]:
        """Aggregate candles into daily closes and compute EMA.

        Returns a dict mapping each day's start timestamp (00:00 UTC ms)
        to that day's EMA value.
        """
        from malu.strategy import indicators as ind

        day_ms = 86_400_000
        daily_closes: dict[int, Decimal] = {}
        for c in candles:
            day_start = (c.timestamp // day_ms) * day_ms
            daily_closes[day_start] = c.close

        sorted_days = sorted(daily_closes.keys())
        closes_list = [daily_closes[d] for d in sorted_days]

        if len(closes_list) < self.trend_ema_period:
            log.warning("trend_filter_insufficient_data",
                        days=len(closes_list), required=self.trend_ema_period)
            return {}

        ema_values = ind.calc_ema(closes_list, self.trend_ema_period)
        result: dict[int, Decimal] = {}
        for day_ts, ema_val in zip(sorted_days, ema_values):
            result[day_ts] = ema_val
        return result

    def _check_trend_filter(
        self,
        bar: HistoricalCandle,
        signal: Signal,
        daily_ema_cache: dict[int, Decimal],
    ) -> bool:
        """Return True if signal is aligned with daily trend."""
        if not daily_ema_cache:
            return True  # no data → allow

        day_ms = 86_400_000
        # Use previous day's EMA (current day not yet complete)
        bar_day = (bar.timestamp // day_ms) * day_ms
        prev_day = bar_day - day_ms

        ema_val = daily_ema_cache.get(prev_day)
        if ema_val is None:
            # Try current day if previous not available
            ema_val = daily_ema_cache.get(bar_day)
        if ema_val is None:
            return True

        if signal == Signal.LONG and bar.close < ema_val:
            return False  # price below EMA, long blocked
        if signal == Signal.SHORT and bar.close > ema_val:
            return False  # price above EMA, short blocked
        return True

    def _calc_atr_from_candles(self, candles: list[HistoricalCandle], bar_idx: int) -> Decimal:
        """Calculate ATR at bar_idx using recent candle data."""
        from malu.strategy import indicators as ind
        period = self.atr_period
        start = max(0, bar_idx - period - 1)
        window = candles[start:bar_idx + 1]
        if len(window) < period:
            # Fallback: 2% of close price
            return candles[bar_idx].close * Decimal("0.02")
        highs = [c.high for c in window]
        lows = [c.low for c in window]
        closes = [c.close for c in window]
        atr = ind.calc_atr(highs, lows, closes, period)
        return atr if atr > 0 else candles[bar_idx].close * Decimal("0.02")

    def _calc_pnl_pct(self, pos: _OpenPosition, current_price: Decimal) -> Decimal:
        if pos.side == "Long":
            return (current_price - pos.entry_price) / pos.entry_price * 100
        else:
            return (pos.entry_price - current_price) / pos.entry_price * 100

    def _unrealised_pnl(self, pos: _OpenPosition, current_price: Decimal) -> Decimal:
        if pos.side == "Long":
            return (current_price - pos.entry_price) * pos.qty
        else:
            return (pos.entry_price - current_price) * pos.qty

    def _apply_slippage(self, price: Decimal, side: str, entry: bool) -> Decimal:
        slip = Decimal(self.config.slippage_bps) / Decimal("10000")
        if (side == "Long" and entry) or (side == "Short" and not entry):
            return price * (1 + slip)
        else:
            return price * (1 - slip)

    def _close_position(
        self, pos: _OpenPosition, bar: HistoricalCandle, reason: str
    ) -> SimulatedTrade:
        exit_price = self._apply_slippage(bar.close, pos.side, entry=False)
        pnl = self._unrealised_pnl(pos, exit_price)
        exit_fee = pos.qty * exit_price * self.config.fee_rate
        # entry fee was already deducted from equity; only record exit fee here
        # But for trade record, include total round-trip fee
        entry_fee = pos.qty * pos.entry_price * self.config.fee_rate
        total_fee = entry_fee + exit_fee

        return SimulatedTrade(
            entry_time=pos.entry_time,
            exit_time=bar.timestamp,
            side=pos.side,
            entry_price=pos.entry_price,
            exit_price=exit_price,
            qty=pos.qty,
            pnl=pnl,
            fee=total_fee,
            funding_paid=pos.accumulated_funding,
            exit_reason=reason,
        )

    def _calc_funding(
        self,
        pos: _OpenPosition,
        prev_ts: int,
        curr_ts: int,
        funding_lookup: list[tuple[int, Decimal]],
    ) -> Decimal:
        """Calculate total funding cost for any funding events between prev_ts and curr_ts."""
        total = Decimal("0")
        for f_ts, f_rate in funding_lookup:
            if prev_ts < f_ts <= curr_ts:
                position_value = pos.qty * pos.entry_price
                # Long pays positive rate, short receives positive rate
                if pos.side == "Long":
                    total += position_value * f_rate
                else:
                    total -= position_value * f_rate
        return total

    @staticmethod
    def _date_to_ms(date_str: str) -> int:
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
