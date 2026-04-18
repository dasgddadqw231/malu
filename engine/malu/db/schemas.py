from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class BotInstanceDB(BaseModel):
    id: str
    api_key_id: str | None = None
    name: str
    bot_tag: str
    status: str = "stopped"
    symbol: str
    category: str = "linear"
    seed_budget: Decimal
    strategy_config: dict = {}
    bot_controls: dict = {}
    cycle_interval: float = 5.0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TradeHistoryDB(BaseModel):
    id: str | None = None
    bot_id: str
    order_link_id: str
    bybit_order_id: str | None = None
    symbol: str
    side: str
    order_type: str
    qty: Decimal
    price: Decimal | None = None
    status: str = "New"
    pnl: Decimal | None = None
    fee: Decimal | None = None
    raw_response: dict | None = None
    created_at: datetime | None = None
    filled_at: datetime | None = None


class BotCreateRequest(BaseModel):
    name: str
    bot_tag: str
    symbol: str
    category: str = "linear"
    seed_budget: Decimal
    strategy_config: dict = {}
    bot_controls: dict = {}
    cycle_interval: float = 5.0
    api_key_id: str | None = None


class BotUpdateRequest(BaseModel):
    name: str | None = None
    seed_budget: Decimal | None = None
    strategy_config: dict | None = None
    bot_controls: dict | None = None
    cycle_interval: float | None = None


# --- DIY Trading / Signature ---


class DiyTradeDB(BaseModel):
    id: str | None = None
    api_key_id: str | None = None
    bybit_order_id: str
    symbol: str
    side: str
    order_type: str
    qty: Decimal
    avg_price: Decimal | None = None
    pnl: Decimal | None = None
    fee: Decimal | None = None
    leverage: str = "1"
    trade_pair_id: str | None = None
    pair_role: str | None = None
    rationale: str | None = None
    tags: list[str] = []
    filled_at: datetime | None = None
    created_at: datetime | None = None


class DiyTradeUpdateRequest(BaseModel):
    rationale: str | None = None
    tags: list[str] | None = None
    trade_pair_id: str | None = None
    pair_role: str | None = None


class SignatureDB(BaseModel):
    id: str | None = None
    name: str
    description: str | None = None
    source_trade_ids: list[str] = []
    dataset_id: str | None = None
    strategy_config: dict = {}
    rules: list[dict] = []
    stats: dict = {}
    messages: list[dict] = []
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SignatureCreateRequest(BaseModel):
    name: str
    description: str | None = None
    source_trade_ids: list[str] = []
    dataset_id: str | None = None
    strategy_config: dict = {}
    rules: list[dict] = []
    stats: dict = {}


class SignatureUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    strategy_config: dict | None = None
    rules: list[dict] | None = None


# --- Manual Datasets ---


class ManualDatasetDB(BaseModel):
    id: str | None = None
    name: str
    description: str | None = None
    trade_ids: list[str] = []
    auto_sync: bool = False
    sync_symbol: str | None = None
    sync_category: str = "linear"
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ManualDatasetCreateRequest(BaseModel):
    name: str
    description: str | None = None
    trade_ids: list[str] = []
    auto_sync: bool = False
    sync_symbol: str | None = None
    sync_category: str = "linear"


class ManualDatasetUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    auto_sync: bool | None = None
    sync_symbol: str | None = None
    sync_category: str | None = None
    add_trade_ids: list[str] | None = None
    remove_trade_ids: list[str] | None = None


# --- Backtest ---


class BacktestRunDB(BaseModel):
    id: str | None = None
    symbol: str
    interval: str = "15"
    start_date: str
    end_date: str
    initial_capital: Decimal
    strategy_config: dict = {}
    slippage_bps: int = 5
    fee_rate: Decimal = Decimal("0.00055")
    total_pnl: Decimal | None = None
    total_fees: Decimal | None = None
    total_funding: Decimal | None = None
    net_pnl: Decimal | None = None
    win_rate: float | None = None
    max_drawdown: float | None = None
    sharpe_ratio: float | None = None
    total_trades: int | None = None
    equity_curve: list[dict] | None = None
    status: str = "running"
    error_message: str | None = None
    created_at: datetime | None = None


class BacktestTradeDB(BaseModel):
    id: str | None = None
    run_id: str
    entry_time: datetime
    exit_time: datetime
    side: str
    entry_price: Decimal
    exit_price: Decimal
    qty: Decimal
    pnl: Decimal
    fee: Decimal
    funding_paid: Decimal = Decimal("0")
    exit_reason: str


class BacktestRunRequest(BaseModel):
    symbol: str
    interval: str = "15"
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    initial_capital: Decimal = Decimal("10000")
    strategy_config: dict = {}
    slippage_bps: int = 5
    fee_rate: Decimal = Decimal("0.00055")
