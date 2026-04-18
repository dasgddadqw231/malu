from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Request, UploadFile, File

from malu.db.schemas import (
    DiyTradeDB,
    ManualDatasetCreateRequest,
    ManualDatasetUpdateRequest,
)
from malu.exchange.models import Category

router = APIRouter(prefix="/diy/datasets", tags=["datasets"])


def _get_dataset_repo(request: Request):
    return request.app.state.dataset_repo


def _get_diy_trade_repo(request: Request):
    return request.app.state.diy_trade_repo


def _get_client(request: Request):
    return request.app.state.bot_manager.client


def _get_bot_tags(request: Request) -> set[str]:
    manager = request.app.state.bot_manager
    tags = set()
    for bot in manager.bots.values():
        tags.add(bot.config.bot_tag)
    bot_repo = request.app.state.bot_repo
    for db_bot in bot_repo.list_all():
        tags.add(db_bot.bot_tag)
    return tags


# ── CRUD ──


@router.get("")
async def list_datasets(request: Request):
    repo = _get_dataset_repo(request)
    datasets = repo.list_all()
    return [ds.model_dump() for ds in datasets]


@router.get("/{ds_id}")
async def get_dataset(request: Request, ds_id: str):
    repo = _get_dataset_repo(request)
    ds = repo.get(ds_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Resolve trades
    diy_repo = _get_diy_trade_repo(request)
    trades = diy_repo.get_by_ids(ds.trade_ids) if ds.trade_ids else []

    result = ds.model_dump()
    result["trades"] = [t.model_dump() for t in trades]
    return result


@router.post("")
async def create_dataset(request: Request, data: ManualDatasetCreateRequest):
    repo = _get_dataset_repo(request)
    ds = repo.create(data)
    return ds.model_dump()


@router.patch("/{ds_id}")
async def update_dataset(request: Request, ds_id: str, data: ManualDatasetUpdateRequest):
    repo = _get_dataset_repo(request)
    ds = repo.update(ds_id, data)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return ds.model_dump()


@router.delete("/{ds_id}")
async def delete_dataset(request: Request, ds_id: str):
    repo = _get_dataset_repo(request)
    repo.delete(ds_id)
    return {"deleted": True}


# ── Sync live trades into dataset ──


@router.post("/{ds_id}/sync")
async def sync_dataset(request: Request, ds_id: str, pages: int = 3):
    """Pull latest manual trades from Bybit and add them to this dataset."""
    ds_repo = _get_dataset_repo(request)
    ds = ds_repo.get(ds_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")

    client = _get_client(request)
    diy_repo = _get_diy_trade_repo(request)
    bot_tags = _get_bot_tags(request)
    cat = Category(ds.sync_category or "linear")

    all_orders: list[dict] = []
    cursor = ""
    for _ in range(pages):
        orders, cursor = await client.get_order_history(
            category=cat, symbol=ds.sync_symbol or None, limit=50, cursor=cursor
        )
        all_orders.extend(orders)
        if not cursor:
            break

    human_orders = [
        o for o in all_orders
        if _is_human_order(o, bot_tags) and o.get("orderStatus") == "Filled"
    ]

    trades = []
    for o in human_orders:
        filled_at = None
        updated_time = o.get("updatedTime")
        if updated_time:
            try:
                filled_at = datetime.fromtimestamp(int(updated_time) / 1000, tz=timezone.utc)
            except (ValueError, TypeError):
                pass

        trades.append(
            DiyTradeDB(
                bybit_order_id=o["orderId"],
                symbol=o["symbol"],
                side=o["side"],
                order_type=o.get("orderType", "Market"),
                qty=Decimal(o.get("cumExecQty", o.get("qty", "0"))),
                avg_price=Decimal(o["avgPrice"]) if o.get("avgPrice") and o["avgPrice"] != "0" else None,
                pnl=Decimal(o["cumExecFee"]) * -1 if o.get("cumExecFee") else None,
                fee=Decimal(o["cumExecFee"]) if o.get("cumExecFee") else None,
                leverage=o.get("leverage", "1"),
                filled_at=filled_at,
            )
        )

    if not trades:
        return {"synced": 0, "added_to_dataset": 0}

    saved = diy_repo.upsert_many(trades)
    new_ids = [t.id for t in saved if t.id and t.id not in ds.trade_ids]

    if new_ids:
        ds_repo.update(ds_id, ManualDatasetUpdateRequest(add_trade_ids=new_ids))

    return {"synced": len(saved), "added_to_dataset": len(new_ids)}


# ── CSV/Excel upload ──


@router.post("/{ds_id}/upload")
async def upload_trades_to_dataset(
    request: Request,
    ds_id: str,
    file: UploadFile = File(...),
):
    """Upload CSV with trade data and add to dataset.

    Expected columns: symbol, side, order_type, qty, avg_price, pnl, fee, filled_at
    """
    ds_repo = _get_dataset_repo(request)
    ds = ds_repo.get(ds_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")

    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    diy_repo = _get_diy_trade_repo(request)
    trades = []
    for row in reader:
        filled_at = None
        if row.get("filled_at"):
            try:
                filled_at = datetime.fromisoformat(row["filled_at"])
            except ValueError:
                pass

        trades.append(
            DiyTradeDB(
                bybit_order_id=f"csv_{uuid.uuid4().hex[:12]}",
                symbol=row.get("symbol", "UNKNOWN"),
                side=row.get("side", "Buy"),
                order_type=row.get("order_type", "Market"),
                qty=Decimal(row.get("qty", "0")),
                avg_price=Decimal(row["avg_price"]) if row.get("avg_price") else None,
                pnl=Decimal(row["pnl"]) if row.get("pnl") else None,
                fee=Decimal(row["fee"]) if row.get("fee") else None,
                leverage=row.get("leverage", "1"),
                filled_at=filled_at,
            )
        )

    if not trades:
        return {"uploaded": 0}

    saved = diy_repo.upsert_many(trades)
    new_ids = [t.id for t in saved if t.id]

    if new_ids:
        ds_repo.update(ds_id, ManualDatasetUpdateRequest(add_trade_ids=new_ids))

    return {"uploaded": len(saved), "added_to_dataset": len(new_ids)}


def _is_human_order(order: dict, bot_tags: set[str]) -> bool:
    link_id = order.get("orderLinkId", "")
    if not link_id:
        return True
    for tag in bot_tags:
        if link_id.startswith(tag):
            return False
    return True
