from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from supabase import Client

from malu.db.schemas import (
    BacktestRunDB,
    BacktestTradeDB,
    BotCreateRequest,
    BotInstanceDB,
    BotUpdateRequest,
    ManualDatasetCreateRequest,
    ManualDatasetDB,
    ManualDatasetUpdateRequest,
    SignatureCreateRequest,
    SignatureDB,
    DiyTradeDB,
    DiyTradeUpdateRequest,
    TradeHistoryDB,
)
from malu.utils.logger import get_logger

log = get_logger("repository")


class BotRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table = "bot_instances"

    def list_all(self) -> list[BotInstanceDB]:
        result = self.client.table(self.table).select("*").execute()
        return [BotInstanceDB(**row) for row in result.data]

    def get(self, bot_id: str) -> BotInstanceDB | None:
        result = self.client.table(self.table).select("*").eq("id", bot_id).execute()
        if result.data:
            return BotInstanceDB(**result.data[0])
        return None

    def create(self, req: BotCreateRequest) -> BotInstanceDB:
        data = req.model_dump()
        data["seed_budget"] = str(data["seed_budget"])
        result = self.client.table(self.table).insert(data).execute()
        return BotInstanceDB(**result.data[0])

    def update(self, bot_id: str, req: BotUpdateRequest) -> BotInstanceDB | None:
        data = {k: v for k, v in req.model_dump().items() if v is not None}
        if "seed_budget" in data:
            data["seed_budget"] = str(data["seed_budget"])
        result = self.client.table(self.table).update(data).eq("id", bot_id).execute()
        if result.data:
            return BotInstanceDB(**result.data[0])
        return None

    def update_status(self, bot_id: str, status: str) -> None:
        self.client.table(self.table).update({"status": status}).eq("id", bot_id).execute()

    def delete(self, bot_id: str) -> None:
        self.client.table(self.table).delete().eq("id", bot_id).execute()


class TradeRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table = "trade_history"

    def insert(self, trade: TradeHistoryDB) -> TradeHistoryDB:
        data = trade.model_dump(exclude_none=True)
        for key in ("qty", "price", "pnl", "fee"):
            if key in data and isinstance(data[key], Decimal):
                data[key] = str(data[key])
        result = self.client.table(self.table).insert(data).execute()
        return TradeHistoryDB(**result.data[0])

    def list_by_bot(self, bot_id: str, limit: int = 50) -> list[TradeHistoryDB]:
        result = (
            self.client.table(self.table)
            .select("*")
            .eq("bot_id", bot_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return [TradeHistoryDB(**row) for row in result.data]

    def list_recent(self, limit: int = 100) -> list[TradeHistoryDB]:
        result = (
            self.client.table(self.table)
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return [TradeHistoryDB(**row) for row in result.data]

    def get_total_pnl(self) -> Decimal:
        result = (
            self.client.table(self.table)
            .select("pnl")
            .not_.is_("pnl", "null")
            .execute()
        )
        total = sum(Decimal(row["pnl"]) for row in result.data)
        return total


class DiyTradeRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table = "diy_trades"

    def upsert_many(self, trades: list[DiyTradeDB]) -> list[DiyTradeDB]:
        rows = []
        for t in trades:
            data = t.model_dump(exclude_none=True)
            for key in ("qty", "avg_price", "pnl", "fee"):
                if key in data and isinstance(data[key], Decimal):
                    data[key] = str(data[key])
            rows.append(data)
        if not rows:
            return []
        result = self.client.table(self.table).upsert(
            rows, on_conflict="bybit_order_id"
        ).execute()
        return [DiyTradeDB(**row) for row in result.data]

    def list_all(self, symbol: str | None = None, limit: int = 200) -> list[DiyTradeDB]:
        query = self.client.table(self.table).select("*")
        if symbol:
            query = query.eq("symbol", symbol)
        result = query.order("filled_at", desc=True).limit(limit).execute()
        return [DiyTradeDB(**row) for row in result.data]

    def get(self, trade_id: str) -> DiyTradeDB | None:
        result = self.client.table(self.table).select("*").eq("id", trade_id).execute()
        if result.data:
            return DiyTradeDB(**result.data[0])
        return None

    def update(self, trade_id: str, req: DiyTradeUpdateRequest) -> DiyTradeDB | None:
        data = {k: v for k, v in req.model_dump().items() if v is not None}
        result = self.client.table(self.table).update(data).eq("id", trade_id).execute()
        if result.data:
            return DiyTradeDB(**result.data[0])
        return None

    def get_by_ids(self, trade_ids: list[str]) -> list[DiyTradeDB]:
        result = self.client.table(self.table).select("*").in_("id", trade_ids).execute()
        return [DiyTradeDB(**row) for row in result.data]


class SignatureRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table = "signatures"

    def create(self, req: SignatureCreateRequest) -> SignatureDB:
        data = req.model_dump()
        result = self.client.table(self.table).insert(data).execute()
        return SignatureDB(**result.data[0])

    def list_active(self) -> list[SignatureDB]:
        result = (
            self.client.table(self.table)
            .select("*")
            .eq("is_active", True)
            .order("created_at", desc=True)
            .execute()
        )
        return [SignatureDB(**row) for row in result.data]

    def get(self, style_id: str) -> SignatureDB | None:
        result = self.client.table(self.table).select("*").eq("id", style_id).execute()
        if result.data:
            return SignatureDB(**result.data[0])
        return None

    def update(self, style_id: str, data: dict) -> SignatureDB | None:
        updates = {k: v for k, v in data.items() if v is not None}
        if not updates:
            return self.get(style_id)
        result = self.client.table(self.table).update(updates).eq("id", style_id).execute()
        if result.data:
            return SignatureDB(**result.data[0])
        return None

    def delete(self, style_id: str) -> None:
        self.client.table(self.table).update({"is_active": False}).eq("id", style_id).execute()


class ManualDatasetRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table = "manual_datasets"

    def create(self, req: ManualDatasetCreateRequest) -> ManualDatasetDB:
        data = req.model_dump()
        result = self.client.table(self.table).insert(data).execute()
        return ManualDatasetDB(**result.data[0])

    def list_all(self, limit: int = 50) -> list[ManualDatasetDB]:
        result = (
            self.client.table(self.table)
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return [ManualDatasetDB(**row) for row in result.data]

    def get(self, ds_id: str) -> ManualDatasetDB | None:
        result = self.client.table(self.table).select("*").eq("id", ds_id).execute()
        if result.data:
            return ManualDatasetDB(**result.data[0])
        return None

    def update(self, ds_id: str, req: ManualDatasetUpdateRequest) -> ManualDatasetDB | None:
        existing = self.get(ds_id)
        if not existing:
            return None

        data: dict = {}
        if req.name is not None:
            data["name"] = req.name
        if req.description is not None:
            data["description"] = req.description
        if req.auto_sync is not None:
            data["auto_sync"] = req.auto_sync
        if req.sync_symbol is not None:
            data["sync_symbol"] = req.sync_symbol
        if req.sync_category is not None:
            data["sync_category"] = req.sync_category

        # Handle add/remove trade_ids
        current_ids = set(existing.trade_ids)
        if req.add_trade_ids:
            current_ids.update(req.add_trade_ids)
        if req.remove_trade_ids:
            current_ids -= set(req.remove_trade_ids)
        data["trade_ids"] = list(current_ids)

        if not data:
            return existing

        result = self.client.table(self.table).update(data).eq("id", ds_id).execute()
        if result.data:
            return ManualDatasetDB(**result.data[0])
        return None

    def delete(self, ds_id: str) -> None:
        self.client.table(self.table).delete().eq("id", ds_id).execute()

    def list_auto_sync(self) -> list[ManualDatasetDB]:
        result = (
            self.client.table(self.table)
            .select("*")
            .eq("auto_sync", True)
            .execute()
        )
        return [ManualDatasetDB(**row) for row in result.data]


class BacktestRepository:
    def __init__(self, client: Client):
        self.client = client
        self.runs_table = "backtest_runs"
        self.trades_table = "backtest_trades"

    def create_run(self, run: BacktestRunDB) -> BacktestRunDB:
        data = run.model_dump(exclude_none=True)
        for key in ("initial_capital", "fee_rate"):
            if key in data and isinstance(data[key], Decimal):
                data[key] = str(data[key])
        result = self.client.table(self.runs_table).insert(data).execute()
        return BacktestRunDB(**result.data[0])

    def update_run(self, run_id: str, updates: dict) -> BacktestRunDB | None:
        # Convert Decimals to strings for Supabase
        data = {}
        for k, v in updates.items():
            if isinstance(v, Decimal):
                data[k] = str(v)
            else:
                data[k] = v
        result = self.client.table(self.runs_table).update(data).eq("id", run_id).execute()
        if result.data:
            return BacktestRunDB(**result.data[0])
        return None

    def get_run(self, run_id: str) -> BacktestRunDB | None:
        result = self.client.table(self.runs_table).select("*").eq("id", run_id).execute()
        if result.data:
            return BacktestRunDB(**result.data[0])
        return None

    def list_runs(self, limit: int = 20) -> list[BacktestRunDB]:
        result = (
            self.client.table(self.runs_table)
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return [BacktestRunDB(**row) for row in result.data]

    def insert_trades(self, trades: list[BacktestTradeDB]) -> None:
        if not trades:
            return
        rows = []
        for t in trades:
            data = t.model_dump(exclude_none=True)
            for key in ("entry_price", "exit_price", "qty", "pnl", "fee", "funding_paid"):
                if key in data and isinstance(data[key], Decimal):
                    data[key] = str(data[key])
            for key in ("entry_time", "exit_time"):
                if key in data and isinstance(data[key], datetime):
                    data[key] = data[key].isoformat()
            rows.append(data)
        self.client.table(self.trades_table).insert(rows).execute()

    def get_trades(self, run_id: str) -> list[BacktestTradeDB]:
        result = (
            self.client.table(self.trades_table)
            .select("*")
            .eq("run_id", run_id)
            .order("entry_time")
            .execute()
        )
        return [BacktestTradeDB(**row) for row in result.data]

    def delete_run(self, run_id: str) -> None:
        self.client.table(self.runs_table).delete().eq("id", run_id).execute()


class ManualRiskRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table = "manual_risk_settings"

    def get(self) -> "ManualRiskSettings":
        from malu.db.schemas import ManualRiskSettings
        result = self.client.table(self.table).select("*").limit(1).execute()
        if result.data:
            return ManualRiskSettings(**result.data[0])
        return ManualRiskSettings()

    def update(self, data: dict) -> "ManualRiskSettings":
        from malu.db.schemas import ManualRiskSettings
        # Get existing row ID
        existing = self.client.table(self.table).select("id").limit(1).execute()
        if existing.data:
            row_id = existing.data[0]["id"]
            result = self.client.table(self.table).update(data).eq("id", row_id).execute()
        else:
            result = self.client.table(self.table).insert(data).execute()
        return ManualRiskSettings(**result.data[0])
