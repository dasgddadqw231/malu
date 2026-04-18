from __future__ import annotations

from fastapi import APIRouter, Request

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


@router.post("/kill-switch/reset")
async def reset_kill_switch(request: Request):
    manager = request.app.state.bot_manager
    manager.kill_switch.reset()
    return {"kill_switch_active": manager.kill_switch.is_active}
