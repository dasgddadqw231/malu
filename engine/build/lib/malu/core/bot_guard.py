"""BotGuard: enforces bot-level operational controls (risk, schedule, sizing).

These controls are independent of the strategy (signature) and allow the same
signature to behave differently per bot deployment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from decimal import Decimal

from malu.utils.logger import get_logger

log = get_logger("bot_guard")


@dataclass
class RiskControls:
    max_daily_loss_pct: float | None = None       # max % of seed lost today before auto-stop
    max_consecutive_losses: int | None = None      # N consecutive losses -> pause
    max_single_loss_pct: float | None = None       # max % loss on single trade

    @classmethod
    def from_dict(cls, d: dict) -> RiskControls:
        return cls(
            max_daily_loss_pct=d.get("max_daily_loss_pct"),
            max_consecutive_losses=d.get("max_consecutive_losses"),
            max_single_loss_pct=d.get("max_single_loss_pct"),
        )


@dataclass
class TimeWindow:
    start: str  # "HH:MM" UTC
    end: str    # "HH:MM" UTC

    def contains_now(self) -> bool:
        now = datetime.now(timezone.utc).time()
        s = time.fromisoformat(self.start)
        e = time.fromisoformat(self.end)
        if s <= e:
            return s <= now <= e
        # overnight: e.g. 22:00 - 06:00
        return now >= s or now <= e


@dataclass
class ScheduleControls:
    trading_hours: list[TimeWindow] = field(default_factory=list)
    cooldown_seconds: float | None = None     # min seconds between trades
    max_trades_per_day: int | None = None      # max entries per day

    @classmethod
    def from_dict(cls, d: dict) -> ScheduleControls:
        windows = [
            TimeWindow(start=w["start"], end=w["end"])
            for w in d.get("trading_hours", [])
        ]
        return cls(
            trading_hours=windows,
            cooldown_seconds=d.get("cooldown_seconds"),
            max_trades_per_day=d.get("max_trades_per_day"),
        )


@dataclass
class SizingControls:
    mode: str = "pct"                           # "pct" (use strategy default) or "fixed"
    fixed_amount_usd: float | None = None       # override: fixed USD per trade
    compound: bool = False                      # reinvest profits into seed

    @classmethod
    def from_dict(cls, d: dict) -> SizingControls:
        return cls(
            mode=d.get("mode", "pct"),
            fixed_amount_usd=d.get("fixed_amount_usd"),
            compound=d.get("compound", False),
        )


@dataclass
class BotControls:
    risk: RiskControls = field(default_factory=RiskControls)
    schedule: ScheduleControls = field(default_factory=ScheduleControls)
    sizing: SizingControls = field(default_factory=SizingControls)

    @classmethod
    def from_dict(cls, d: dict) -> BotControls:
        return cls(
            risk=RiskControls.from_dict(d.get("risk", {})),
            schedule=ScheduleControls.from_dict(d.get("schedule", {})),
            sizing=SizingControls.from_dict(d.get("sizing", {})),
        )

    def to_dict(self) -> dict:
        result: dict = {}
        # risk
        risk: dict = {}
        if self.risk.max_daily_loss_pct is not None:
            risk["max_daily_loss_pct"] = self.risk.max_daily_loss_pct
        if self.risk.max_consecutive_losses is not None:
            risk["max_consecutive_losses"] = self.risk.max_consecutive_losses
        if self.risk.max_single_loss_pct is not None:
            risk["max_single_loss_pct"] = self.risk.max_single_loss_pct
        if risk:
            result["risk"] = risk

        # schedule
        sched: dict = {}
        if self.schedule.trading_hours:
            sched["trading_hours"] = [
                {"start": w.start, "end": w.end} for w in self.schedule.trading_hours
            ]
        if self.schedule.cooldown_seconds is not None:
            sched["cooldown_seconds"] = self.schedule.cooldown_seconds
        if self.schedule.max_trades_per_day is not None:
            sched["max_trades_per_day"] = self.schedule.max_trades_per_day
        if sched:
            result["schedule"] = sched

        # sizing
        sizing: dict = {}
        if self.sizing.mode != "pct":
            sizing["mode"] = self.sizing.mode
        if self.sizing.fixed_amount_usd is not None:
            sizing["fixed_amount_usd"] = self.sizing.fixed_amount_usd
        if self.sizing.compound:
            sizing["compound"] = True
        if sizing:
            result["sizing"] = sizing

        return result


@dataclass
class GuardState:
    """Mutable per-bot runtime state tracked by the guard."""
    daily_pnl: Decimal = Decimal("0")
    daily_trade_count: int = 0
    consecutive_losses: int = 0
    last_trade_at: datetime | None = None
    current_date: str = ""  # YYYY-MM-DD, to reset daily counters

    def _check_day_reset(self) -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self.current_date:
            self.daily_pnl = Decimal("0")
            self.daily_trade_count = 0
            self.current_date = today


class BotGuard:
    """Evaluates bot controls to decide if the bot should trade this cycle."""

    def __init__(self, controls: BotControls, seed_budget: Decimal):
        self.controls = controls
        self.seed_budget = seed_budget
        self.state = GuardState()

    def can_trade(self) -> tuple[bool, str]:
        """Returns (allowed, reason). If not allowed, reason explains why."""
        self.state._check_day_reset()

        # --- Schedule checks ---
        sched = self.controls.schedule

        # Trading hours
        if sched.trading_hours:
            in_window = any(w.contains_now() for w in sched.trading_hours)
            if not in_window:
                return False, "outside trading hours"

        # Cooldown
        if sched.cooldown_seconds and self.state.last_trade_at:
            elapsed = (datetime.now(timezone.utc) - self.state.last_trade_at).total_seconds()
            if elapsed < sched.cooldown_seconds:
                remaining = int(sched.cooldown_seconds - elapsed)
                return False, f"cooldown: {remaining}s remaining"

        # Max trades per day
        if sched.max_trades_per_day is not None:
            if self.state.daily_trade_count >= sched.max_trades_per_day:
                return False, f"daily trade limit reached ({sched.max_trades_per_day})"

        # --- Risk checks ---
        risk = self.controls.risk

        # Daily loss limit
        if risk.max_daily_loss_pct is not None and self.seed_budget > 0:
            loss_limit = self.seed_budget * Decimal(str(risk.max_daily_loss_pct)) / Decimal("100")
            if self.state.daily_pnl < -loss_limit:
                return False, f"daily loss limit hit ({risk.max_daily_loss_pct}%)"

        # Consecutive losses
        if risk.max_consecutive_losses is not None:
            if self.state.consecutive_losses >= risk.max_consecutive_losses:
                return False, f"consecutive loss limit ({risk.max_consecutive_losses})"

        return True, ""

    def compute_trade_size(self, available_budget: Decimal, strategy_size_pct: float) -> Decimal:
        """Compute actual trade size, applying sizing overrides."""
        sizing = self.controls.sizing

        if sizing.mode == "fixed" and sizing.fixed_amount_usd is not None:
            return min(Decimal(str(sizing.fixed_amount_usd)), available_budget)

        # Default: use strategy's size_pct
        return available_budget * Decimal(str(strategy_size_pct))

    def record_trade(self, pnl: Decimal | None = None) -> None:
        """Call after a trade is placed. pnl is set later when position closes."""
        self.state._check_day_reset()
        self.state.daily_trade_count += 1
        self.state.last_trade_at = datetime.now(timezone.utc)
        log.info(
            "guard_trade_recorded",
            daily_count=self.state.daily_trade_count,
            consecutive_losses=self.state.consecutive_losses,
        )

    def record_close(self, pnl: Decimal) -> None:
        """Call when a position is closed with realized PnL."""
        self.state._check_day_reset()
        self.state.daily_pnl += pnl

        if pnl < 0:
            self.state.consecutive_losses += 1
        else:
            self.state.consecutive_losses = 0

        log.info(
            "guard_close_recorded",
            pnl=str(pnl),
            daily_pnl=str(self.state.daily_pnl),
            consecutive_losses=self.state.consecutive_losses,
        )

    def get_max_single_loss_pct(self) -> float | None:
        """Return max single loss % for defense module to use."""
        return self.controls.risk.max_single_loss_pct
