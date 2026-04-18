from __future__ import annotations

from decimal import Decimal

from malu.core.order_tagger import OrderTagger
from malu.core.rate_limiter import APIRateLimiter
from malu.exchange.bybit_client import BybitClient
from malu.exchange.models import Category, OrderRequest, OrderType, Side
from malu.strategy.base import ActionModule, ActionResult, Signal
from malu.utils.logger import get_logger

log = get_logger("action")


class MarketOrderAction(ActionModule):
    """Places market orders based on signals.

    Params:
        size_pct: float (0.0-1.0) - fraction of available budget to use per trade
        category: str (default "linear")
    """

    async def execute(
        self,
        signal: Signal,
        symbol: str,
        available_budget: Decimal,
        client: BybitClient,
        rate_limiter: APIRateLimiter,
        order_tagger: OrderTagger,
    ) -> ActionResult:
        if signal == Signal.HOLD:
            return ActionResult(executed=False, reason="hold signal")

        size_pct = Decimal(str(self.params.get("size_pct", 0.5)))
        category = Category(self.params.get("category", "linear"))

        trade_amount = available_budget * size_pct
        if trade_amount <= 0:
            return ActionResult(executed=False, reason="no budget available")

        # Determine side
        if signal == Signal.LONG:
            side = Side.BUY
        elif signal == Signal.SHORT:
            side = Side.SELL
        elif signal == Signal.CLOSE:
            side = Side.SELL  # will be adjusted by caller based on position
        else:
            return ActionResult(executed=False, reason=f"unhandled signal: {signal}")

        order_link_id = order_tagger.generate()

        # Rate limit before API call
        await rate_limiter.acquire("order")

        req = OrderRequest(
            category=category,
            symbol=symbol,
            side=side,
            order_type=OrderType.MARKET,
            qty=trade_amount,
            order_link_id=order_link_id,
        )

        resp = await client.place_order(req)
        log.info("action_executed", signal=signal, side=side, qty=str(trade_amount))

        return ActionResult(
            order_link_id=resp.order_link_id,
            side=side,
            qty=trade_amount,
            executed=True,
            reason=f"{signal} market order placed",
        )
