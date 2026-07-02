from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from malu.utils.logger import get_logger

log = get_logger("kill_switch")


@dataclass
class KillReport:
    bots_stopped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    success: bool = True


class KillSwitch:
    """Master and per-bot emergency stop mechanism."""

    def __init__(self):
        self.kill_event = asyncio.Event()
        self._bot_manager = None

    def bind(self, bot_manager) -> None:
        self._bot_manager = bot_manager

    @property
    def is_active(self) -> bool:
        return self.kill_event.is_set()

    async def activate_master(self) -> KillReport:
        """Stop ALL bots, cancel all orders, close all positions."""
        log.warning("MASTER_KILL_SWITCH_ACTIVATED")
        self.kill_event.set()

        report = KillReport()
        if not self._bot_manager:
            return report

        for bot_id, bot in list(self._bot_manager.bots.items()):
            try:
                await bot.kill()
                report.bots_stopped.append(bot_id)
            except Exception as e:
                report.errors.append(f"{bot_id}: {e}")
                report.success = False

        log.info("master_kill_complete", report=report)
        return report

    async def activate_bot(self, bot_id: str) -> KillReport:
        """Kill a single bot."""
        log.warning("bot_kill_switch", bot_id=bot_id)
        report = KillReport()

        if not self._bot_manager:
            report.errors.append("no bot manager")
            report.success = False
            return report

        bot = self._bot_manager.bots.get(bot_id)
        if not bot:
            report.errors.append(f"bot {bot_id} not found")
            report.success = False
            return report

        try:
            await bot.kill()
            report.bots_stopped.append(bot_id)
        except Exception as e:
            report.errors.append(f"{bot_id}: {e}")
            report.success = False

        return report

    def reset(self) -> None:
        """Reset kill switch after master activation."""
        self.kill_event.clear()
        log.info("kill_switch_reset")
