from __future__ import annotations

from decimal import Decimal

from malu.exchange.bybit_client import BybitClient
from malu.exchange.models import PositionInfo, Side
from malu.strategy.base import DefenseModule, DefenseResult
from malu.utils.logger import get_logger

log = get_logger("defense")


class TrailingStopDefense(DefenseModule):
    """Trailing stop-loss defense module.

    Params:
        max_loss_pct: float - maximum loss % before forced close (default 5.0)
        take_profit_pct: float - take profit % (default 3.0)
    """

    async def check(self, position: PositionInfo | None, client: BybitClient, market_data=None) -> DefenseResult:
        if position is None or position.size == 0:
            return DefenseResult(should_close=False)

        max_loss_pct = Decimal(str(self.params.get("max_loss_pct", 5.0)))
        take_profit_pct = Decimal(str(self.params.get("take_profit_pct", 3.0)))

        # Use real-time mark price from WebSocket for more accurate PnL
        unrealised_pnl = position.unrealised_pnl
        if market_data:
            ticker = market_data.get_ticker(position.symbol)
            if ticker and ticker.mark_price > 0:
                if position.side == Side.BUY:
                    unrealised_pnl = (ticker.mark_price - position.entry_price) * position.size
                else:
                    unrealised_pnl = (position.entry_price - ticker.mark_price) * position.size

        pnl_pct = (unrealised_pnl / (position.entry_price * position.size)) * 100

        if pnl_pct <= -max_loss_pct:
            log.warning(
                "stop_loss_triggered",
                symbol=position.symbol,
                pnl_pct=str(pnl_pct),
            )
            return DefenseResult(
                should_close=True,
                reason=f"stop loss: PnL {pnl_pct:.2f}% <= -{max_loss_pct}%",
            )

        if pnl_pct >= take_profit_pct:
            log.info(
                "take_profit_triggered",
                symbol=position.symbol,
                pnl_pct=str(pnl_pct),
            )
            return DefenseResult(
                should_close=True,
                reason=f"take profit: PnL {pnl_pct:.2f}% >= {take_profit_pct}%",
            )

        return DefenseResult(should_close=False)
