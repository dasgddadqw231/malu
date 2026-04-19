from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/risk", tags=["risk"])


class RiskSettingsUpdate(BaseModel):
    enabled: bool | None = None
    max_loss_pct: float | None = None
    max_profit_pct: float | None = None
    max_daily_loss_usd: float | None = None
    max_daily_trades: int | None = None
    max_position_pct: float | None = None
    max_leverage: int | None = None
    notify_on_close: bool | None = None


@router.get("/settings")
async def get_risk_settings(request: Request):
    repo = request.app.state.risk_repo
    settings = repo.get()
    return settings.model_dump()


@router.put("/settings")
async def update_risk_settings(request: Request, body: RiskSettingsUpdate):
    repo = request.app.state.risk_repo
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    settings = repo.update(data)
    return settings.model_dump()


@router.get("/guard/status")
async def get_guard_status(request: Request):
    guard = request.app.state.manual_guard
    return {
        "running": guard._task is not None and not guard._task.done(),
        "poll_interval": guard.poll_interval,
        "recent_actions": list(guard.recent_actions),
    }
