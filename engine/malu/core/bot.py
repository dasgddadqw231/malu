from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any, Callable, Coroutine

from malu.core.bot_guard import BotControls, BotGuard
from malu.core.budget import BudgetLedger, BudgetOverflowError
from malu.core.order_tagger import OrderTagger
from malu.core.rate_limiter import APIRateLimiter
from malu.exchange.bybit_client import BybitClient
from malu.exchange.models import Category, Side
from malu.strategy.base import (
    ActionModule,
    DefenseModule,
    DefenseResult,
    FilterModule,
    FilterResult,
    JudgmentModule,
    JudgmentResult,
    Signal,
    SizingModule,
    SizingResult,
)
from malu.utils.logger import get_logger

log = get_logger("bot")


class BotStatus(StrEnum):
    STOPPED = "stopped"
    RUNNING = "running"
    WAITING = "waiting"  # waiting for signal
    IN_POSITION = "in_position"
    JUDGING = "judging"
    ACTING = "acting"
    DEFENDING = "defending"
    KILLED = "killed"
    ERROR = "error"


# Strategy module registry
JUDGMENT_REGISTRY: dict[str, type[JudgmentModule]] = {}
ACTION_REGISTRY: dict[str, type[ActionModule]] = {}
DEFENSE_REGISTRY: dict[str, type[DefenseModule]] = {}
FILTER_REGISTRY: dict[str, type[FilterModule]] = {}
SIZING_REGISTRY: dict[str, type[SizingModule]] = {}


def _populate_registries():
    from malu.strategy.judgment import BBRSIJudgment, BBSqueezeJudgment, EMACrossJudgment, MACDCrossJudgment, RSIDivergenceJudgment
    from malu.strategy.action import MarketOrderAction
    from malu.strategy.defense import FixedPctDefense, TrailingStopDefense, ATRStopDefense, TrailingATRDefense, TimeStopDefense
    from malu.strategy.filters import TrendFilter, RegimeFilter, VolatilityFilter
    from malu.strategy.sizing import FixedFractionSizing, RiskBasedSizing, VolatilityAdjustedSizing

    JUDGMENT_REGISTRY["bb_rsi"] = BBRSIJudgment
    JUDGMENT_REGISTRY["bb_reversal"] = BBRSIJudgment  # alias
    JUDGMENT_REGISTRY["bb_squeeze"] = BBSqueezeJudgment
    JUDGMENT_REGISTRY["ema_cross"] = EMACrossJudgment
    JUDGMENT_REGISTRY["macd_cross"] = MACDCrossJudgment
    JUDGMENT_REGISTRY["rsi_divergence"] = RSIDivergenceJudgment

    ACTION_REGISTRY["market_order"] = MarketOrderAction

    DEFENSE_REGISTRY["trailing_stop"] = FixedPctDefense  # backward compat
    DEFENSE_REGISTRY["fixed_pct"] = FixedPctDefense
    DEFENSE_REGISTRY["atr_stop"] = ATRStopDefense
    DEFENSE_REGISTRY["trailing_atr"] = TrailingATRDefense
    DEFENSE_REGISTRY["time_stop"] = TimeStopDefense

    FILTER_REGISTRY["trend_filter"] = TrendFilter
    FILTER_REGISTRY["regime_filter"] = RegimeFilter
    FILTER_REGISTRY["volatility_filter"] = VolatilityFilter

    SIZING_REGISTRY["fixed_fraction"] = FixedFractionSizing
    SIZING_REGISTRY["risk_based"] = RiskBasedSizing
    SIZING_REGISTRY["volatility_adjusted"] = VolatilityAdjustedSizing


_populate_registries()


@dataclass
class BotConfig:
    bot_id: str
    bot_tag: str
    name: str
    symbol: str
    category: Category = Category.LINEAR
    seed_budget: Decimal = Decimal("0")
    leverage: int = 1
    strategy_config: dict = field(default_factory=dict)
    cycle_interval: float = 5.0
    bot_controls: dict = field(default_factory=dict)


# Type for event callbacks
EventCallback = Callable[[str, str, dict], Coroutine[Any, Any, None]]


class Bot:
    """A single trading bot instance with independent strategy and budget."""

    def __init__(
        self,
        config: BotConfig,
        client: BybitClient,
        rate_limiter: APIRateLimiter,
        budget_ledger: BudgetLedger,
        kill_event: asyncio.Event,
        on_event: EventCallback | None = None,
        market_data: object | None = None,
    ):
        self.config = config
        self.client = client
        self.rate_limiter = rate_limiter
        self.budget_ledger = budget_ledger
        self.kill_event = kill_event
        self.on_event = on_event
        self.market_data = market_data

        self.status = BotStatus.STOPPED
        self.order_tagger = OrderTagger(config.bot_tag)
        self._task: asyncio.Task | None = None

        # Bot-level operational controls (risk, schedule, sizing)
        controls = BotControls.from_dict(config.bot_controls)
        self.guard = BotGuard(controls, config.seed_budget)

        # Load strategy modules from config
        sc = config.strategy_config
        j_cfg = sc.get("judgment", {"module": "bb_rsi", "params": {}})
        a_cfg = sc.get("action", {"module": "market_order", "params": {}})
        d_cfg = sc.get("defense", {"module": "trailing_stop", "params": {}})

        self.judgment = JUDGMENT_REGISTRY[j_cfg["module"]](j_cfg.get("params", {}))
        self.action = ACTION_REGISTRY[a_cfg["module"]](a_cfg.get("params", {}))
        self.defense = DEFENSE_REGISTRY[d_cfg["module"]](d_cfg.get("params", {}))

        # Load filter modules (optional, can be a list)
        filters_cfg = sc.get("filters", [])
        self.filters: list[FilterModule] = []
        for f_cfg in filters_cfg:
            module_name = f_cfg.get("module", "")
            if module_name in FILTER_REGISTRY:
                self.filters.append(FILTER_REGISTRY[module_name](f_cfg.get("params", {})))

        # Load sizing module (optional, defaults to using action's size_pct)
        s_cfg = sc.get("sizing")
        self.sizing: SizingModule | None = None
        if s_cfg and s_cfg.get("module") in SIZING_REGISTRY:
            sizing_params = {**s_cfg.get("params", {}), "leverage": config.leverage}
            self.sizing = SIZING_REGISTRY[s_cfg["module"]](sizing_params)

    @property
    def bot_id(self) -> str:
        return self.config.bot_id

    @property
    def name(self) -> str:
        return self.config.name

    async def start(self) -> None:
        if self._task and not self._task.done():
            log.warning("bot_already_running", bot_id=self.bot_id)
            return

        await self.budget_ledger.register_bot(self.bot_id, self.config.seed_budget)

        # Set leverage on exchange before trading
        if self.config.leverage >= 1:
            try:
                await self.rate_limiter.acquire("order")
                await self.client.set_leverage(
                    Category(self.config.category),
                    self.config.symbol,
                    self.config.leverage,
                )
            except Exception as e:
                log.error("set_leverage_failed", bot_id=self.bot_id, error=str(e))

        self.status = BotStatus.RUNNING
        self._task = asyncio.create_task(self._run_loop(), name=f"bot-{self.bot_id}")
        await self._emit("started", {"leverage": self.config.leverage})
        log.info("bot_started", bot_id=self.bot_id, name=self.name, leverage=self.config.leverage)

    async def stop(self) -> None:
        """Graceful stop: finish current cycle, then stop."""
        self.status = BotStatus.STOPPED
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._emit("stopped", {})
        log.info("bot_stopped", bot_id=self.bot_id)

    async def kill(self) -> None:
        """Emergency: cancel all orders, close positions, stop."""
        self.status = BotStatus.KILLED
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        try:
            await self.rate_limiter.acquire("order")
            await self.client.cancel_all_orders(
                Category(self.config.category), self.config.symbol
            )

            await self.rate_limiter.acquire("position")
            positions = await self.client.get_positions(
                Category(self.config.category), self.config.symbol
            )
            for pos in positions:
                await self.rate_limiter.acquire("order")
                await self.client.close_position(
                    Category(self.config.category),
                    pos.symbol,
                    pos.side,
                    pos.size,
                )
        except Exception as e:
            log.error("kill_cleanup_error", bot_id=self.bot_id, error=str(e))

        await self.budget_ledger.unregister_bot(self.bot_id)
        await self._emit("killed", {})
        log.info("bot_killed", bot_id=self.bot_id)

    async def _run_loop(self) -> None:
        """Main bot loop: judgment -> action -> defense, repeating."""
        while self.status == BotStatus.RUNNING and not self.kill_event.is_set():
            try:
                await self._run_cycle()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.status = BotStatus.ERROR
                log.error("bot_cycle_error", bot_id=self.bot_id, error=str(e))
                await self._emit("error", {"error": str(e)})
                await asyncio.sleep(self.config.cycle_interval * 2)
                if not self.kill_event.is_set():
                    self.status = BotStatus.RUNNING

            await asyncio.sleep(self.config.cycle_interval)

    async def _run_cycle(self) -> None:
        """Single cycle: guard -> judge -> act -> defend."""
        # 1. Check for existing position
        await self.rate_limiter.acquire("position")
        positions = await self.client.get_positions(
            Category(self.config.category), self.config.symbol
        )
        current_position = positions[0] if positions else None

        # 2. Defense check (if holding position)
        if current_position:
            self.status = BotStatus.DEFENDING
            await self._emit("status", {"phase": "defending"})

            # 2.0 Liquidation proximity guard (non-optional safety)
            if current_position.liq_price > 0 and self.config.leverage > 1:
                current_price = current_position.entry_price
                if self.market_data:
                    ticker = self.market_data.get_ticker(current_position.symbol)
                    if ticker and ticker.mark_price > 0:
                        current_price = ticker.mark_price

                if current_position.side == Side.BUY:
                    liq_dist_pct = (current_price - current_position.liq_price) / current_price * 100
                else:
                    liq_dist_pct = (current_position.liq_price - current_price) / current_price * 100

                if liq_dist_pct < Decimal("2"):
                    log.warning("liquidation_close", bot_id=self.bot_id,
                                liq_price=str(current_position.liq_price),
                                current_price=str(current_price),
                                distance_pct=str(liq_dist_pct))
                    await self.rate_limiter.acquire("order")
                    await self.client.close_position(
                        Category(self.config.category),
                        current_position.symbol,
                        current_position.side,
                        current_position.size,
                    )
                    pnl = current_position.unrealised_pnl or Decimal("0")
                    self.guard.record_close(pnl)
                    await self._emit("liquidation_guard", {
                        "reason": f"liquidation proximity: {liq_dist_pct:.2f}% from liq price",
                        "liq_price": str(current_position.liq_price),
                        "pnl": str(pnl),
                    })
                    return

            defense_result: DefenseResult = await self.defense.check(
                current_position, self.client, market_data=self.market_data
            )
            if defense_result.should_close:
                log.info("defense_closing", bot_id=self.bot_id, reason=defense_result.reason)
                await self.rate_limiter.acquire("order")
                await self.client.close_position(
                    Category(self.config.category),
                    current_position.symbol,
                    current_position.side,
                    current_position.size,
                )
                # Record PnL in guard for risk tracking
                pnl = current_position.unrealised_pnl or Decimal("0")
                self.guard.record_close(pnl)
                await self._emit("defense_triggered", {
                    "reason": defense_result.reason,
                    "pnl": str(pnl),
                })
                return

            self.status = BotStatus.IN_POSITION
            await self._emit("status", {"phase": "in_position"})
            return  # holding, no new entry

        # 3. Guard check (before new entry)
        allowed, guard_reason = self.guard.can_trade()
        if not allowed:
            self.status = BotStatus.WAITING
            await self._emit("status", {"phase": "guard_blocked", "reason": guard_reason})
            log.info("guard_blocked", bot_id=self.bot_id, reason=guard_reason)
            return

        # 4. Judgment
        self.status = BotStatus.JUDGING
        await self._emit("status", {"phase": "judging"})

        judgment: JudgmentResult = await self.judgment.evaluate(
            self.config.symbol, self.client, market_data=self.market_data
        )

        if judgment.signal == Signal.HOLD:
            self.status = BotStatus.WAITING
            await self._emit("status", {"phase": "waiting", "reason": judgment.reason})
            return

        # 4.5 Filter checks
        for f in self.filters:
            try:
                filter_result: FilterResult = await f.check(
                    self.config.symbol, judgment.signal, self.client, market_data=self.market_data
                )
                if not filter_result.allowed:
                    self.status = BotStatus.WAITING
                    await self._emit("status", {"phase": "filtered", "reason": filter_result.reason})
                    log.info("filter_blocked", bot_id=self.bot_id, reason=filter_result.reason)
                    return
            except Exception as e:
                log.warning("filter_error", bot_id=self.bot_id, error=str(e))

        # 5. Action (with sizing override from guard)
        self.status = BotStatus.ACTING
        await self._emit("status", {"phase": "acting", "signal": judgment.signal})

        available = await self.budget_ledger.get_available(self.bot_id)
        if available <= 0:
            log.warning("no_budget", bot_id=self.bot_id)
            return

        # Apply sizing controls
        if self.sizing:
            sizing_result: SizingResult = await self.sizing.calculate(
                self.config.symbol, available, judgment.signal, self.client, market_data=self.market_data
            )
            trade_amount = min(sizing_result.trade_amount, available)
        else:
            strategy_size_pct = self.action.params.get("size_pct", 0.5)
            trade_amount = self.guard.compute_trade_size(available, strategy_size_pct)
        if trade_amount <= 0:
            log.warning("guard_zero_size", bot_id=self.bot_id)
            return

        try:
            rid = await self.budget_ledger.reserve(self.bot_id, trade_amount)
        except BudgetOverflowError as e:
            log.warning("budget_overflow", bot_id=self.bot_id, error=str(e))
            return

        try:
            result = await self.action.execute(
                judgment.signal,
                self.config.symbol,
                trade_amount,
                self.client,
                self.rate_limiter,
                self.order_tagger,
            )
            if result.executed:
                await self.budget_ledger.commit(self.bot_id, rid)
                self.guard.record_trade()
                await self._emit("trade", {
                    "signal": judgment.signal,
                    "side": result.side,
                    "qty": str(result.qty),
                    "order_link_id": result.order_link_id,
                })
            else:
                await self.budget_ledger.release(self.bot_id, rid)
        except Exception:
            await self.budget_ledger.release(self.bot_id, rid)
            raise

        self.status = BotStatus.RUNNING

    async def _emit(self, event: str, data: dict) -> None:
        if self.on_event:
            try:
                await self.on_event(self.bot_id, event, data)
            except Exception as e:
                log.error("event_emit_error", error=str(e))
