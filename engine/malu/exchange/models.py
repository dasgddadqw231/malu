from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel


class Side(StrEnum):
    BUY = "Buy"
    SELL = "Sell"


class OrderType(StrEnum):
    MARKET = "Market"
    LIMIT = "Limit"


class OrderStatus(StrEnum):
    NEW = "New"
    FILLED = "Filled"
    PARTIALLY_FILLED = "PartiallyFilled"
    CANCELLED = "Cancelled"
    REJECTED = "Rejected"


class Category(StrEnum):
    LINEAR = "linear"
    SPOT = "spot"
    INVERSE = "inverse"


class OrderRequest(BaseModel):
    category: Category
    symbol: str
    side: Side
    order_type: OrderType
    qty: Decimal
    price: Decimal | None = None
    order_link_id: str = ""


class OrderResponse(BaseModel):
    order_id: str
    order_link_id: str


class PositionInfo(BaseModel):
    symbol: str
    side: Side
    size: Decimal
    entry_price: Decimal
    unrealised_pnl: Decimal
    leverage: str = "1"


class WalletBalance(BaseModel):
    total_equity: Decimal
    available_balance: Decimal
    coin: str = "USDT"
