from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, HTTPException, Request

from malu.core.bot import BotConfig
from malu.db.schemas import BotCreateRequest, BotUpdateRequest

router = APIRouter(prefix="/bots", tags=["bots"])


def _get_manager(request: Request):
    return request.app.state.bot_manager


def _get_bot_repo(request: Request):
    return request.app.state.bot_repo


def _get_trade_repo(request: Request):
    return request.app.state.trade_repo


@router.get("")
async def list_bots(request: Request):
    manager = _get_manager(request)
    return manager.get_bot_statuses()


@router.post("")
async def create_bot(req: BotCreateRequest, request: Request):
    manager = _get_manager(request)
    bot_repo = _get_bot_repo(request)

    # Save to DB first
    db_bot = bot_repo.create(req)

    # Create in-memory bot
    config = BotConfig(
        bot_id=db_bot.id,
        bot_tag=db_bot.bot_tag,
        name=db_bot.name,
        symbol=db_bot.symbol,
        category=db_bot.category,
        seed_budget=db_bot.seed_budget,
        leverage=db_bot.leverage,
        strategy_config=db_bot.strategy_config,
        bot_controls=db_bot.bot_controls,
        cycle_interval=db_bot.cycle_interval,
    )

    try:
        bot = await manager.add_bot(config)
    except ValueError as e:
        bot_repo.delete(db_bot.id)
        raise HTTPException(status_code=400, detail=str(e))

    return {"bot_id": db_bot.id, "name": db_bot.name, "status": bot.status.value}


@router.get("/{bot_id}")
async def get_bot(bot_id: str, request: Request):
    manager = _get_manager(request)
    bot = manager.bots.get(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return {
        "bot_id": bot.bot_id,
        "name": bot.name,
        "status": bot.status.value,
        "symbol": bot.config.symbol,
        "seed_budget": str(bot.config.seed_budget),
        "leverage": bot.config.leverage,
        "strategy_config": bot.config.strategy_config,
        "bot_controls": bot.config.bot_controls,
        "guard_state": {
            "daily_pnl": str(bot.guard.state.daily_pnl),
            "daily_trade_count": bot.guard.state.daily_trade_count,
            "consecutive_losses": bot.guard.state.consecutive_losses,
        },
    }


@router.patch("/{bot_id}")
async def update_bot(bot_id: str, req: BotUpdateRequest, request: Request):
    manager = _get_manager(request)
    bot_repo = _get_bot_repo(request)

    # Update DB
    updated = bot_repo.update(bot_id, req)
    if not updated:
        raise HTTPException(status_code=404, detail="Bot not found")

    # Sync in-memory bot config
    bot = manager.bots.get(bot_id)
    if bot:
        if req.name is not None:
            bot.config.name = req.name
        if req.seed_budget is not None:
            bot.config.seed_budget = req.seed_budget
        if req.leverage is not None:
            bot.config.leverage = req.leverage
        if req.strategy_config is not None:
            bot.config.strategy_config = req.strategy_config
        if req.bot_controls is not None:
            bot.config.bot_controls = req.bot_controls
            # Rebuild guard with new controls
            from malu.core.bot_guard import BotControls, BotGuard
            controls = BotControls.from_dict(req.bot_controls)
            bot.guard = BotGuard(controls, bot.config.seed_budget)
        if req.cycle_interval is not None:
            bot.config.cycle_interval = req.cycle_interval

    return {"bot_id": updated.id, "name": updated.name}


@router.post("/{bot_id}/start")
async def start_bot(bot_id: str, request: Request):
    manager = _get_manager(request)
    bot_repo = _get_bot_repo(request)
    try:
        await manager.start_bot(bot_id)
        bot_repo.update_status(bot_id, "running")
    except KeyError:
        raise HTTPException(status_code=404, detail="Bot not found")
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"status": "running"}


@router.post("/{bot_id}/stop")
async def stop_bot(bot_id: str, request: Request):
    manager = _get_manager(request)
    bot_repo = _get_bot_repo(request)
    try:
        await manager.stop_bot(bot_id)
        bot_repo.update_status(bot_id, "stopped")
    except KeyError:
        raise HTTPException(status_code=404, detail="Bot not found")
    return {"status": "stopped"}


@router.post("/{bot_id}/kill")
async def kill_bot(bot_id: str, request: Request):
    manager = _get_manager(request)
    bot_repo = _get_bot_repo(request)
    report = await manager.kill_switch.activate_bot(bot_id)
    bot_repo.update_status(bot_id, "killed")
    return {"status": "killed", "report": report}


@router.delete("/{bot_id}")
async def delete_bot(bot_id: str, request: Request):
    manager = _get_manager(request)
    bot_repo = _get_bot_repo(request)
    try:
        await manager.remove_bot(bot_id)
    except KeyError:
        pass
    bot_repo.delete(bot_id)
    return {"deleted": True}


@router.get("/{bot_id}/trades")
async def get_bot_trades(bot_id: str, request: Request, limit: int = 50):
    trade_repo = _get_trade_repo(request)
    trades = trade_repo.list_by_bot(bot_id, limit=limit)
    return [t.model_dump() for t in trades]
