from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any, Callable, Coroutine

from malu.core.bot import Bot, BotConfig, BotStatus
from malu.core.budget import BudgetLedger
from malu.core.kill_switch import KillSwitch
from malu.core.order_tagger import OrderTagger
from malu.core.rate_limiter import APIRateLimiter
from malu.exchange.bybit_client import BybitClient
from malu.exchange.market_data_feed import MarketDataFeed
from malu.exchange.models import Category
from malu.utils.logger import get_logger

log = get_logger("bot_manager")

EventCallback = Callable[[str, str, dict], Coroutine[Any, Any, None]]


class BotManager:
    """Top-level orchestrator for all bot instances.

    Manages bot lifecycle, budget validation, and periodic reconciliation.
    All bots share one BybitClient and APIRateLimiter.
    """

    def __init__(
        self,
        client: BybitClient,
        rate_limiter: APIRateLimiter,
        budget_ledger: BudgetLedger,
        kill_switch: KillSwitch,
        reconcile_interval: float = 30.0,
        on_event: EventCallback | None = None,
        market_data_feed: MarketDataFeed | None = None,
    ):
        self.client = client
        self.rate_limiter = rate_limiter
        self.budget_ledger = budget_ledger
        self.kill_switch = kill_switch
        self.reconcile_interval = reconcile_interval
        self.on_event = on_event
        self.market_data_feed = market_data_feed

        self.bots: dict[str, Bot] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._reconcile_task: asyncio.Task | None = None

        kill_switch.bind(self)

    async def start(self) -> None:
        """Start the manager and its reconciliation loop."""
        self._reconcile_task = asyncio.create_task(
            self._reconcile_loop(), name="reconcile"
        )
        log.info("bot_manager_started")

    async def shutdown(self) -> None:
        """Graceful shutdown of all bots and tasks."""
        if self._reconcile_task:
            self._reconcile_task.cancel()
            try:
                await self._reconcile_task
            except asyncio.CancelledError:
                pass

        for bot_id in list(self.bots.keys()):
            await self.stop_bot(bot_id)

        log.info("bot_manager_shutdown")

    async def add_bot(self, config: BotConfig) -> Bot:
        """Register and create a new bot (does not start it)."""
        # Validate budget
        wallet = await self.client.get_wallet_balance()
        total_allocated = sum(
            (b.config.seed_budget for b in self.bots.values()), Decimal("0")
        )
        remaining = wallet.available_balance - total_allocated

        if config.seed_budget > remaining:
            raise ValueError(
                f"Insufficient balance. Requested: {config.seed_budget}, "
                f"Available: {remaining} (wallet: {wallet.available_balance}, "
                f"allocated: {total_allocated})"
            )

        # Subscribe to real-time data for this symbol
        market_data_store = None
        if self.market_data_feed:
            await self.market_data_feed.subscribe(config.symbol)
            market_data_store = self.market_data_feed.store

        bot = Bot(
            config=config,
            client=self.client,
            rate_limiter=self.rate_limiter,
            budget_ledger=self.budget_ledger,
            kill_event=self.kill_switch.kill_event,
            on_event=self.on_event,
            market_data=market_data_store,
        )
        self.bots[config.bot_id] = bot
        log.info("bot_added", bot_id=config.bot_id, name=config.name)
        return bot

    async def remove_bot(self, bot_id: str) -> None:
        """Stop and remove a bot."""
        bot = self.bots.get(bot_id)
        if not bot:
            raise KeyError(f"Bot {bot_id} not found")

        if bot.status in (BotStatus.RUNNING, BotStatus.WAITING, BotStatus.IN_POSITION):
            await bot.stop()

        await self.budget_ledger.unregister_bot(bot_id)
        del self.bots[bot_id]
        self._tasks.pop(bot_id, None)
        log.info("bot_removed", bot_id=bot_id)

    async def start_bot(self, bot_id: str) -> None:
        """Start a registered bot."""
        bot = self.bots.get(bot_id)
        if not bot:
            raise KeyError(f"Bot {bot_id} not found")

        if self.kill_switch.is_active:
            raise RuntimeError("Cannot start bot: master kill switch is active")

        await bot.start()

    async def stop_bot(self, bot_id: str) -> None:
        """Gracefully stop a bot."""
        bot = self.bots.get(bot_id)
        if not bot:
            raise KeyError(f"Bot {bot_id} not found")
        await bot.stop()

    async def kill_all(self) -> dict:
        """Activate master kill switch."""
        report = await self.kill_switch.activate_master()
        return {"bots_stopped": report.bots_stopped, "errors": report.errors}

    def get_bot_statuses(self) -> list[dict]:
        """Get status summary for all bots."""
        return [
            {
                "bot_id": bot.bot_id,
                "name": bot.name,
                "status": bot.status.value,
                "symbol": bot.config.symbol,
                "seed_budget": str(bot.config.seed_budget),
                "strategy_config": bot.config.strategy_config,
                "bot_controls": bot.config.bot_controls,
            }
            for bot in self.bots.values()
        ]

    async def get_available_budget(self) -> Decimal:
        """Calculate remaining allocatable budget."""
        wallet = await self.client.get_wallet_balance()
        total_allocated = sum(
            (b.config.seed_budget for b in self.bots.values()), Decimal("0")
        )
        return wallet.available_balance - total_allocated

    async def _reconcile_loop(self) -> None:
        """Periodically reconcile budget ledger with exchange state."""
        while True:
            try:
                await asyncio.sleep(self.reconcile_interval)
                await self._reconcile()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.error("reconcile_error", error=str(e))

    async def _reconcile(self) -> None:
        """Sync budget ledger state with actual exchange positions/orders."""
        try:
            wallet = await self.client.get_wallet_balance()
            valid = await self.budget_ledger.validate_total_allocation(
                wallet.available_balance
            )
            if not valid:
                log.warning("budget_over_allocated", balance=str(wallet.available_balance))

            # Reconcile open orders: check they belong to known bots
            for bot in self.bots.values():
                if bot.status == BotStatus.STOPPED:
                    continue
                await self.rate_limiter.acquire("order")
                open_orders = await self.client.get_open_orders(
                    Category(bot.config.category), bot.config.symbol
                )
                for order in open_orders:
                    link_id = order.get("orderLinkId", "")
                    tag = OrderTagger.extract_bot_tag(link_id)
                    if tag and tag != bot.config.bot_tag:
                        log.warning(
                            "orphan_order_detected",
                            order_link_id=link_id,
                            expected_tag=bot.config.bot_tag,
                            actual_tag=tag,
                        )
        except Exception as e:
            log.error("reconcile_failed", error=str(e))
