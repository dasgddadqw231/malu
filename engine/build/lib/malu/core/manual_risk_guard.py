"""ManualRiskGuard: post-trade monitor for manual (non-bot) positions.

Polls Bybit positions periodically and enforces manual_risk_settings rules:
- Max leverage → auto-close
- Max position % of equity → auto-close
- Max daily loss → close all manual positions
- Auto SL/TP injection on positions without them
"""

from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timezone
from decimal import Decimal

from malu.core.bot import BotStatus
from malu.core.bot_manager import BotManager
from malu.core.rate_limiter import APIRateLimiter
from malu.db.repositories import ManualRiskRepository
from malu.db.schemas import ManualRiskSettings
from malu.exchange.bybit_client import BybitClient
from malu.exchange.models import Category, PositionInfo, Side
from malu.utils.logger import get_logger

log = get_logger("manual_risk_guard")


class ManualRiskGuard:
    """Background task that monitors manual positions and enforces risk rules."""

    def __init__(
        self,
        client: BybitClient,
        risk_repo: ManualRiskRepository,
        bot_manager: BotManager,
        rate_limiter: APIRateLimiter,
        poll_interval: float = 15.0,
    ):
        self.client = client
        self.risk_repo = risk_repo
        self.bot_manager = bot_manager
        self.rate_limiter = rate_limiter
        self.poll_interval = poll_interval
        self._task: asyncio.Task | None = None
        self.recent_actions: deque[dict] = deque(maxlen=50)

    async def start(self) -> None:
        self._task = asyncio.create_task(self._poll_loop(), name="manual_risk_guard")
        log.info("manual_risk_guard_started", poll_interval=self.poll_interval)

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        log.info("manual_risk_guard_stopped")

    async def _poll_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(self.poll_interval)
                await self._check_positions()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.error("manual_risk_guard_error", error=str(e))

    async def _check_positions(self) -> None:
        settings = self.risk_repo.get()
        if not settings.enabled:
            return

        positions = await self.client.get_positions(Category.LINEAR)

        # Filter out bot-managed symbols
        bot_symbols = self._get_bot_symbols()
        manual_positions = [p for p in positions if p.symbol not in bot_symbols]

        if not manual_positions:
            return

        wallet = await self.client.get_wallet_balance()
        equity = wallet.total_equity

        # Daily loss check — close ALL manual positions if breached
        if settings.max_daily_loss_usd > 0:
            daily_pnl = await self._get_today_realized_pnl()
            if daily_pnl < -Decimal(str(settings.max_daily_loss_usd)):
                await self._close_all(manual_positions, "daily_loss_limit", daily_pnl)
                return

        for pos in manual_positions:
            await self._check_position(pos, settings, equity)

    async def _check_position(
        self, pos: PositionInfo, settings: ManualRiskSettings, equity: Decimal
    ) -> None:
        violations: list[str] = []

        # Max leverage
        if settings.max_leverage > 0:
            pos_leverage = int(Decimal(pos.leverage))
            if pos_leverage > settings.max_leverage:
                violations.append(
                    f"leverage {pos_leverage}x > max {settings.max_leverage}x"
                )

        # Max position % of equity
        if settings.max_position_pct > 0 and equity > 0:
            position_value = pos.size * pos.entry_price
            position_pct = (position_value / equity) * 100
            if position_pct > Decimal(str(settings.max_position_pct)):
                violations.append(
                    f"position {position_pct:.1f}% > max {settings.max_position_pct}%"
                )

        # Hard violations → close immediately
        if violations:
            log.warning("manual_risk_violation", symbol=pos.symbol, violations=violations)
            await self.rate_limiter.acquire("order")
            await self.client.close_position(
                Category.LINEAR, pos.symbol, pos.side, pos.size
            )
            action = {
                "time": datetime.now(timezone.utc).isoformat(),
                "action": "close",
                "symbol": pos.symbol,
                "reasons": violations,
            }
            self.recent_actions.append(action)
            log.info("manual_risk_closed", **action)
            return

        # Soft rules → inject SL/TP if missing
        await self._ensure_sl_tp(pos, settings)

    async def _ensure_sl_tp(
        self, pos: PositionInfo, settings: ManualRiskSettings
    ) -> None:
        tp_price: Decimal | None = None
        sl_price: Decimal | None = None

        # Auto SL from max_loss_pct
        if settings.max_loss_pct > 0 and pos.stop_loss == 0:
            loss_pct = Decimal(str(settings.max_loss_pct)) / 100
            if pos.side == Side.BUY:
                sl_price = pos.entry_price * (1 - loss_pct)
            else:
                sl_price = pos.entry_price * (1 + loss_pct)

        # Auto TP from max_profit_pct
        if settings.max_profit_pct > 0 and pos.take_profit == 0:
            profit_pct = Decimal(str(settings.max_profit_pct)) / 100
            if pos.side == Side.BUY:
                tp_price = pos.entry_price * (1 + profit_pct)
            else:
                tp_price = pos.entry_price * (1 - profit_pct)

        if tp_price is None and sl_price is None:
            return

        await self.rate_limiter.acquire("order")
        await self.client.set_trading_stop(
            Category.LINEAR,
            pos.symbol,
            take_profit=tp_price,
            stop_loss=sl_price,
        )
        action = {
            "time": datetime.now(timezone.utc).isoformat(),
            "action": "set_sl_tp",
            "symbol": pos.symbol,
            "sl": str(sl_price),
            "tp": str(tp_price),
        }
        self.recent_actions.append(action)
        log.info("sl_tp_injected", **action)

    async def _get_today_realized_pnl(self) -> Decimal:
        """Sum today's closed PnL from Bybit."""
        records, _ = await self.client.get_closed_pnl(Category.LINEAR, limit=50)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        total = Decimal("0")
        for r in records:
            ts = int(r.get("updatedTime", "0"))
            if ts == 0:
                continue
            dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
            if dt.strftime("%Y-%m-%d") == today:
                total += Decimal(r.get("closedPnl", "0"))
        return total

    async def _close_all(
        self, positions: list[PositionInfo], reason: str, daily_pnl: Decimal
    ) -> None:
        """Close all manual positions due to aggregate rule violation."""
        for pos in positions:
            await self.rate_limiter.acquire("order")
            await self.client.close_position(
                Category.LINEAR, pos.symbol, pos.side, pos.size
            )
            action = {
                "time": datetime.now(timezone.utc).isoformat(),
                "action": "close_all",
                "symbol": pos.symbol,
                "reason": reason,
                "daily_pnl": str(daily_pnl),
            }
            self.recent_actions.append(action)
            log.warning("manual_risk_close_all", **action)

    def _get_bot_symbols(self) -> set[str]:
        """Get symbols currently managed by active bots."""
        active_statuses = {BotStatus.RUNNING, BotStatus.WAITING, BotStatus.IN_POSITION,
                          BotStatus.JUDGING, BotStatus.ACTING, BotStatus.DEFENDING}
        return {
            bot.config.symbol
            for bot in self.bot_manager.bots.values()
            if bot.status in active_statuses
        }
