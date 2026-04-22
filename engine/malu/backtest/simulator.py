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
        self.max_loss_pct = Decimal(str(defense_params.get("max_loss_pct", 5.0)))
        self.take_profit_pct = Decimal(str(defense_params.get("take_profit_pct", 3.0)))

        action_cfg = config.strategy_config.get("action", {})
        action_params = action_cfg.get("params", {})
        self.position_size_pct = Decimal(str(action_params.get("position_size_pct", 95)))

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
        return self._simulate(candles, funding_rates)

    def _simulate(
        self,
        candles: list[HistoricalCandle],
        funding_rates: list[FundingRecord],
    ) -> BacktestResult:
        if len(candles) < 25:
            log.warning("insufficient_candles", count=len(candles))
            return BacktestResult(config=self.config, trades=[])

        # Build funding rate lookup: sorted list of (timestamp, rate)
        funding_lookup = [(f.timestamp, f.funding_rate) for f in funding_rates]

        lookback = self._calc_lookback()
        equity = self.config.initial_capital
        peak_equity = equity
        max_dd = Decimal("0")

        position: _OpenPosition | None = None
        trades: list[SimulatedTrade] = []
        equity_curve: list[dict] = []

        for i in range(lookback, len(candles)):
            bar = candles[i]
            window_closes = [c.close for c in candles[i - lookback : i + 1]]

            # --- Defense check ---
            if position is not None:
                pnl_pct = self._calc_pnl_pct(position, bar.close)

                should_close = False
                reason = ""

                if pnl_pct <= -self.max_loss_pct:
                    should_close = True
                    reason = f"stop_loss: {pnl_pct:.2f}%"
                elif pnl_pct >= self.take_profit_pct:
                    should_close = True
                    reason = f"take_profit: {pnl_pct:.2f}%"

                if should_close:
                    trade = self._close_position(position, bar, reason)
                    trades.append(trade)
                    equity += trade.pnl - trade.fee - trade.funding_paid
                    position = None

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
                result = self.judgment.evaluate_from_candles(window_closes)

                if result.signal in (Signal.LONG, Signal.SHORT):
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
