from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from malu.utils.logger import get_logger

log = get_logger("budget")


@dataclass
class Reservation:
    reservation_id: str
    amount: Decimal


@dataclass
class BotBudget:
    seed: Decimal
    used: Decimal = Decimal("0")
    reservations: dict[str, Reservation] = field(default_factory=dict)

    @property
    def reserved_total(self) -> Decimal:
        return sum((r.amount for r in self.reservations.values()), Decimal("0"))

    @property
    def available(self) -> Decimal:
        return self.seed - self.used - self.reserved_total

    @property
    def pnl(self) -> Decimal:
        return self.used  # positive = profit used, will be refined with actual P&L tracking


class BudgetOverflowError(Exception):
    pass


class BudgetLedger:
    """Tracks per-bot budget allocation with reserve/commit/release pattern.

    Ensures:
    - No bot exceeds its seed_budget
    - Sum of all seed_budgets <= exchange wallet balance
    - Concurrent order attempts don't race past budget limits
    """

    def __init__(self):
        self._budgets: dict[str, BotBudget] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    async def register_bot(self, bot_id: str, seed: Decimal) -> None:
        async with self._global_lock:
            self._budgets[bot_id] = BotBudget(seed=seed)
            self._locks[bot_id] = asyncio.Lock()
            log.info("bot_budget_registered", bot_id=bot_id, seed=str(seed))

    async def unregister_bot(self, bot_id: str) -> None:
        async with self._global_lock:
            self._budgets.pop(bot_id, None)
            self._locks.pop(bot_id, None)

    async def validate_total_allocation(self, exchange_balance: Decimal) -> bool:
        """Check that sum of all bot seeds <= exchange available balance."""
        async with self._global_lock:
            total = sum((b.seed for b in self._budgets.values()), Decimal("0"))
            valid = total <= exchange_balance
            if not valid:
                log.error(
                    "budget_overflow",
                    total_allocated=str(total),
                    exchange_balance=str(exchange_balance),
                )
            return valid

    async def reserve(self, bot_id: str, amount: Decimal) -> str:
        """Reserve budget before placing an order. Returns a reservation_id."""
        lock = self._locks.get(bot_id)
        if not lock:
            raise KeyError(f"Bot {bot_id} not registered in budget ledger")

        async with lock:
            budget = self._budgets[bot_id]
            if amount > budget.available:
                raise BudgetOverflowError(
                    f"Bot {bot_id}: requested {amount}, available {budget.available}"
                )
            rid = uuid.uuid4().hex[:8]
            budget.reservations[rid] = Reservation(reservation_id=rid, amount=amount)
            log.info("budget_reserved", bot_id=bot_id, amount=str(amount), rid=rid)
            return rid

    async def commit(self, bot_id: str, reservation_id: str) -> None:
        """Commit a reservation after order is filled."""
        lock = self._locks.get(bot_id)
        if not lock:
            return
        async with lock:
            budget = self._budgets[bot_id]
            reservation = budget.reservations.pop(reservation_id, None)
            if reservation:
                budget.used += reservation.amount
                log.info("budget_committed", bot_id=bot_id, amount=str(reservation.amount))

    async def release(self, bot_id: str, reservation_id: str) -> None:
        """Release a reservation (order cancelled/rejected)."""
        lock = self._locks.get(bot_id)
        if not lock:
            return
        async with lock:
            budget = self._budgets[bot_id]
            reservation = budget.reservations.pop(reservation_id, None)
            if reservation:
                log.info("budget_released", bot_id=bot_id, amount=str(reservation.amount))

    async def get_available(self, bot_id: str) -> Decimal:
        lock = self._locks.get(bot_id)
        if not lock:
            return Decimal("0")
        async with lock:
            return self._budgets[bot_id].available

    async def get_summary(self) -> dict[str, dict]:
        async with self._global_lock:
            return {
                bot_id: {
                    "seed": str(b.seed),
                    "used": str(b.used),
                    "reserved": str(b.reserved_total),
                    "available": str(b.available),
                }
                for bot_id, b in self._budgets.items()
            }

    async def adjust_used(self, bot_id: str, actual_used: Decimal) -> None:
        """Reconcile used budget with actual exchange data."""
        lock = self._locks.get(bot_id)
        if not lock:
            return
        async with lock:
            old = self._budgets[bot_id].used
            self._budgets[bot_id].used = actual_used
            if old != actual_used:
                log.info("budget_reconciled", bot_id=bot_id, old=str(old), new=str(actual_used))
