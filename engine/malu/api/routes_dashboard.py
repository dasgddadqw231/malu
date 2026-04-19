from __future__ import annotations

from fastapi import APIRouter, Request

from malu.exchange.models import Category

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def get_summary(request: Request):
    manager = request.app.state.bot_manager
    budget_ledger = manager.budget_ledger
    trade_repo = request.app.state.trade_repo

    bot_statuses = manager.get_bot_statuses()
    budget_summary = await budget_ledger.get_summary()
    available = await manager.get_available_budget()
    total_pnl = trade_repo.get_total_pnl()

    return {
        "bots": bot_statuses,
        "budget": budget_summary,
        "available_budget": str(available),
        "total_bots": len(bot_statuses),
        "active_bots": sum(1 for b in bot_statuses if b["status"] not in ("stopped", "killed")),
        "kill_switch_active": manager.kill_switch.is_active,
        "total_pnl": str(total_pnl),
    }


@router.get("/trades")
async def get_all_trades(request: Request, limit: int = 200):
    trade_repo = request.app.state.trade_repo
    trades = trade_repo.list_recent(limit=limit)
    return [t.model_dump() for t in trades]


@router.post("/kill-all")
async def kill_all(request: Request):
    manager = request.app.state.bot_manager
    result = await manager.kill_all()
    return result


@router.get("/positions")
async def get_positions(request: Request):
    """Get all open positions from Bybit, tagged as bot or manual."""
    manager = request.app.state.bot_manager
    client = manager.client

    # Fetch all linear positions from Bybit
    all_positions = await client.get_positions(Category.LINEAR)

    # Build a map of symbol -> bot for identification
    bot_symbols: dict[str, dict] = {}
    for bot in manager.bots.values():
        bot_symbols[bot.config.symbol] = {
            "bot_id": bot.bot_id,
            "name": bot.name,
            "status": bot.status.value,
        }

    results = []
    for pos in all_positions:
        bot_info = bot_symbols.get(pos.symbol)
        results.append({
            "symbol": pos.symbol,
            "side": pos.side.value,
            "size": str(pos.size),
            "entry_price": str(pos.entry_price),
            "unrealised_pnl": str(pos.unrealised_pnl),
            "leverage": pos.leverage,
            "liq_price": str(pos.liq_price),
            "source": "bot" if bot_info else "manual",
            "bot": bot_info,
        })

    return results


@router.post("/kill-switch/reset")
async def reset_kill_switch(request: Request):
    manager = request.app.state.bot_manager
    manager.kill_switch.reset()
    return {"kill_switch_active": manager.kill_switch.is_active}
