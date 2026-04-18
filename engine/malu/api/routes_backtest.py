from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from malu.backtest.simulator import BacktestConfig, BacktestSimulator
from malu.db.repositories import BacktestRepository, SignatureRepository
from malu.db.schemas import BacktestRunDB, BacktestRunRequest, BacktestTradeDB
from malu.exchange.bybit_client import BybitClient
from malu.utils.logger import get_logger

log = get_logger("api.backtest")

router = APIRouter(prefix="/backtest", tags=["backtest"])


async def _run_backtest_task(
    run_id: str,
    config: BacktestConfig,
    client: BybitClient,
    repo: BacktestRepository,
) -> None:
    """Background task that runs the backtest and saves results."""
    try:
        simulator = BacktestSimulator(config)
        result = await simulator.run(client)

        # Save trades
        trade_dbs = []
        for t in result.trades:
            trade_dbs.append(
                BacktestTradeDB(
                    run_id=run_id,
                    entry_time=datetime.fromtimestamp(t.entry_time / 1000, tz=timezone.utc),
                    exit_time=datetime.fromtimestamp(t.exit_time / 1000, tz=timezone.utc),
                    side=t.side,
                    entry_price=t.entry_price,
                    exit_price=t.exit_price,
                    qty=t.qty,
                    pnl=t.pnl,
                    fee=t.fee,
                    funding_paid=t.funding_paid,
                    exit_reason=t.exit_reason,
                )
            )
        repo.insert_trades(trade_dbs)

        # Update run with results
        repo.update_run(run_id, {
            "status": "completed",
            "total_pnl": result.total_pnl,
            "total_fees": result.total_fees,
            "total_funding": result.total_funding,
            "net_pnl": result.net_pnl,
            "win_rate": result.win_rate,
            "max_drawdown": result.max_drawdown,
            "sharpe_ratio": result.sharpe_ratio,
            "total_trades": result.total_trades,
            "equity_curve": result.equity_curve,
        })

        log.info(
            "backtest_completed",
            run_id=run_id,
            trades=result.total_trades,
            net_pnl=str(result.net_pnl),
        )

    except Exception as e:
        log.error("backtest_failed", run_id=run_id, error=str(e))
        repo.update_run(run_id, {
            "status": "failed",
            "error_message": str(e),
        })


@router.post("")
async def run_backtest(req: BacktestRunRequest, request: Request):
    """Start a backtest run. Returns immediately; poll GET /backtest/{run_id} for results."""
    repo: BacktestRepository = request.app.state.backtest_repo
    settings = request.app.state.settings

    # Create a dedicated client for backtest (uses same API keys)
    client = BybitClient(
        api_key=settings.bybit_api_key,
        api_secret=settings.bybit_api_secret,
        testnet=settings.bybit_testnet,
    )

    # Insert run record
    run_db = repo.create_run(
        BacktestRunDB(
            symbol=req.symbol,
            interval=req.interval,
            start_date=req.start_date,
            end_date=req.end_date,
            initial_capital=req.initial_capital,
            strategy_config=req.strategy_config,
            slippage_bps=req.slippage_bps,
            fee_rate=req.fee_rate,
        )
    )

    config = BacktestConfig(
        symbol=req.symbol,
        interval=req.interval,
        start_date=req.start_date,
        end_date=req.end_date,
        initial_capital=req.initial_capital,
        strategy_config=req.strategy_config,
        slippage_bps=req.slippage_bps,
        fee_rate=req.fee_rate,
    )

    # Launch as background task
    asyncio.create_task(_run_backtest_task(run_db.id, config, client, repo))

    return {"run_id": run_db.id, "status": "running"}


@router.post("/from-signature/{sig_id}")
async def run_backtest_from_signature(
    sig_id: str,
    request: Request,
    symbol: str = "BTCUSDT",
    interval: str = "15",
    start_date: str = "",
    end_date: str = "",
    initial_capital: float = 10000,
):
    """Run a backtest using a signature's strategy_config directly."""
    sig_repo: SignatureRepository = request.app.state.signature_repo
    sig = sig_repo.get(sig_id)
    if not sig:
        return JSONResponse(status_code=404, content={"detail": "signature not found"})

    if not start_date or not end_date:
        return JSONResponse(
            status_code=400,
            content={"detail": "start_date and end_date are required (YYYY-MM-DD)"},
        )

    req = BacktestRunRequest(
        symbol=symbol,
        interval=interval,
        start_date=start_date,
        end_date=end_date,
        initial_capital=Decimal(str(initial_capital)),
        strategy_config=sig.strategy_config,
    )
    return await run_backtest(req, request)


@router.get("")
async def list_backtests(request: Request):
    """List all backtest runs."""
    repo: BacktestRepository = request.app.state.backtest_repo
    runs = repo.list_runs()
    return [r.model_dump() for r in runs]


@router.get("/{run_id}")
async def get_backtest(run_id: str, request: Request):
    """Get backtest result including summary and equity curve."""
    repo: BacktestRepository = request.app.state.backtest_repo
    run = repo.get_run(run_id)
    if not run:
        return JSONResponse(status_code=404, content={"detail": "backtest not found"})
    return run.model_dump()


@router.get("/{run_id}/trades")
async def get_backtest_trades(run_id: str, request: Request):
    """Get individual trades for a backtest run."""
    repo: BacktestRepository = request.app.state.backtest_repo
    trades = repo.get_trades(run_id)
    return [t.model_dump() for t in trades]


@router.delete("/{run_id}")
async def delete_backtest(run_id: str, request: Request):
    """Delete a backtest run and its trades."""
    repo: BacktestRepository = request.app.state.backtest_repo
    repo.delete_run(run_id)
    return {"status": "deleted"}
