from __future__ import annotations

import asyncio
from decimal import Decimal
from functools import partial

from pybit.unified_trading import HTTP

from malu.exchange.models import (
    Category,
    OrderRequest,
    OrderResponse,
    OrderStatus,
    OrderType,
    PositionInfo,
    Side,
    WalletBalance,
)
from malu.utils.logger import get_logger

log = get_logger("bybit_client")


class BybitClient:
    """Thin async wrapper around pybit's synchronous HTTP client."""

    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self._client = HTTP(
            api_key=api_key,
            api_secret=api_secret,
            testnet=testnet,
        )

    async def _run_sync(self, func, *args, **kwargs):
        """Run a synchronous pybit call in a thread to avoid blocking the event loop."""
        return await asyncio.to_thread(partial(func, *args, **kwargs))

    async def place_order(self, req: OrderRequest) -> OrderResponse:
        params = {
            "category": req.category.value,
            "symbol": req.symbol,
            "side": req.side.value,
            "orderType": req.order_type.value,
            "qty": str(req.qty),
        }
        if req.price is not None:
            params["price"] = str(req.price)
        if req.order_link_id:
            params["orderLinkId"] = req.order_link_id

        result = await self._run_sync(self._client.place_order, **params)
        info = result["result"]
        log.info("order_placed", order_id=info["orderId"], link_id=info.get("orderLinkId"))
        return OrderResponse(
            order_id=info["orderId"],
            order_link_id=info.get("orderLinkId", req.order_link_id),
        )

    async def cancel_order(
        self, category: Category, symbol: str, order_id: str | None = None, order_link_id: str | None = None
    ) -> dict:
        params: dict = {"category": category.value, "symbol": symbol}
        if order_id:
            params["orderId"] = order_id
        if order_link_id:
            params["orderLinkId"] = order_link_id
        return await self._run_sync(self._client.cancel_order, **params)

    async def cancel_all_orders(self, category: Category, symbol: str | None = None) -> dict:
        params: dict = {"category": category.value}
        if symbol:
            params["symbol"] = symbol
        return await self._run_sync(self._client.cancel_all_orders, **params)

    async def get_open_orders(self, category: Category, symbol: str | None = None) -> list[dict]:
        params: dict = {"category": category.value}
        if symbol:
            params["symbol"] = symbol
        result = await self._run_sync(self._client.get_open_orders, **params)
        return result["result"]["list"]

    async def get_positions(self, category: Category, symbol: str | None = None) -> list[PositionInfo]:
        params: dict = {"category": category.value}
        if symbol:
            params["symbol"] = symbol
        result = await self._run_sync(self._client.get_positions, **params)
        positions = []
        for p in result["result"]["list"]:
            size = Decimal(p["size"])
            if size == 0:
                continue
            positions.append(
                PositionInfo(
                    symbol=p["symbol"],
                    side=Side(p["side"]),
                    size=size,
                    entry_price=Decimal(p["avgPrice"]),
                    unrealised_pnl=Decimal(p["unrealisedPnl"]),
                    leverage=p.get("leverage", "1"),
                )
            )
        return positions

    async def get_wallet_balance(self, account_type: str = "UNIFIED") -> WalletBalance:
        result = await self._run_sync(
            self._client.get_wallet_balance, accountType=account_type
        )
        accounts = result["result"]["list"]
        if not accounts:
            return WalletBalance(total_equity=Decimal("0"), available_balance=Decimal("0"))
        coins = accounts[0]["coin"]
        if not coins:
            # No coin balances - return total from account level
            acct = accounts[0]
            return WalletBalance(
                total_equity=Decimal(acct.get("totalEquity", "0")),
                available_balance=Decimal(acct.get("totalAvailableBalance", "0")),
            )
        usdt = next((c for c in coins if c["coin"] == "USDT"), coins[0])
        return WalletBalance(
            total_equity=Decimal(usdt["equity"]),
            available_balance=Decimal(usdt["availableToWithdraw"]),
            coin=usdt["coin"],
        )

    async def close_position(self, category: Category, symbol: str, side: Side, qty: Decimal) -> OrderResponse:
        """Close a position by placing an opposite market order."""
        close_side = Side.SELL if side == Side.BUY else Side.BUY
        return await self.place_order(
            OrderRequest(
                category=category,
                symbol=symbol,
                side=close_side,
                order_type=OrderType.MARKET,
                qty=qty,
            )
        )

    async def get_order_history(
        self,
        category: Category,
        symbol: str | None = None,
        limit: int = 50,
        cursor: str = "",
    ) -> tuple[list[dict], str]:
        """Fetch closed/filled order history. Returns (orders, next_cursor)."""
        params: dict = {"category": category.value, "limit": limit}
        if symbol:
            params["symbol"] = symbol
        if cursor:
            params["cursor"] = cursor
        result = await self._run_sync(self._client.get_order_history, **params)
        orders = result["result"]["list"]
        next_cursor = result["result"].get("nextPageCursor", "")
        return orders, next_cursor

    async def get_kline(
        self,
        category: Category,
        symbol: str,
        interval: str,
        limit: int = 200,
        start: int | None = None,
        end: int | None = None,
    ) -> list[list]:
        """Fetch OHLCV kline data. Returns list of [timestamp, open, high, low, close, volume, turnover]."""
        params: dict = {
            "category": category.value,
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        }
        if start is not None:
            params["start"] = start
        if end is not None:
            params["end"] = end
        result = await self._run_sync(self._client.get_kline, **params)
        return result["result"]["list"]

    async def get_funding_rate_history(
        self,
        category: Category,
        symbol: str,
        limit: int = 200,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[dict]:
        """Fetch historical funding rates."""
        params: dict = {
            "category": category.value,
            "symbol": symbol,
            "limit": limit,
        }
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time
        result = await self._run_sync(self._client.get_funding_rate_history, **params)
        return result["result"]["list"]

    async def get_closed_pnl(
        self,
        category: Category,
        symbol: str | None = None,
        limit: int = 50,
        cursor: str = "",
    ) -> tuple[list[dict], str]:
        """Fetch closed PnL records. Returns (records, next_cursor)."""
        params: dict = {"category": category.value, "limit": limit}
        if symbol:
            params["symbol"] = symbol
        if cursor:
            params["cursor"] = cursor
        result = await self._run_sync(self._client.get_closed_pnl, **params)
        records = result["result"]["list"]
        next_cursor = result["result"].get("nextPageCursor", "")
        return records, next_cursor
