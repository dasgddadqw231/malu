from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from malu.api.routes_backtest import router as backtest_router
from malu.api.routes_bot import router as bot_router
from malu.api.routes_dashboard import router as dashboard_router
from malu.api.routes_dataset import router as dataset_router
from malu.api.routes_diy import router as diy_router
from malu.api.routes_risk import router as risk_router
from malu.api.ws import bot_event_handler, router as ws_router
from malu.config import Settings
from malu.core.bot import BotConfig
from malu.core.bot_manager import BotManager
from malu.core.budget import BudgetLedger
from malu.core.kill_switch import KillSwitch
from malu.core.rate_limiter import APIRateLimiter
from malu.db.repositories import BacktestRepository, BotRepository, ManualDatasetRepository, ManualRiskRepository, SignatureRepository, DiyTradeRepository, TradeRepository
from malu.db.supabase_client import get_supabase
from malu.exchange.bybit_client import BybitClient
from malu.exchange.market_data_feed import MarketDataFeed
from malu.utils.logger import get_logger

log = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    log.info("starting_malu", testnet=settings.bybit_testnet)

    # Initialize core components
    client = BybitClient(
        api_key=settings.bybit_api_key,
        api_secret=settings.bybit_api_secret,
        testnet=settings.bybit_testnet,
    )
    rate_limiter = APIRateLimiter()
    budget_ledger = BudgetLedger()
    kill_switch = KillSwitch()

    # Initialize real-time market data feed (WebSocket)
    market_data_feed: MarketDataFeed | None = None
    if settings.ws_enabled:
        kline_intervals = [s.strip() for s in settings.ws_kline_intervals.split(",")]
        market_data_feed = MarketDataFeed(
            testnet=settings.bybit_testnet,
            kline_intervals=kline_intervals,
        )
        await market_data_feed.start()
        log.info("market_data_feed_started")

    manager = BotManager(
        client=client,
        rate_limiter=rate_limiter,
        budget_ledger=budget_ledger,
        kill_switch=kill_switch,
        reconcile_interval=settings.reconcile_interval_sec,
        on_event=bot_event_handler,
        market_data_feed=market_data_feed,
    )

    # Initialize DB repositories
    supabase = get_supabase(settings)
    bot_repo = BotRepository(supabase)
    trade_repo = TradeRepository(supabase)
    diy_trade_repo = DiyTradeRepository(supabase)
    signature_repo = SignatureRepository(supabase)
    backtest_repo = BacktestRepository(supabase)
    dataset_repo = ManualDatasetRepository(supabase)
    risk_repo = ManualRiskRepository(supabase)

    # Store in app state
    app.state.market_data_feed = market_data_feed
    app.state.bot_manager = manager
    app.state.bot_repo = bot_repo
    app.state.trade_repo = trade_repo
    app.state.diy_trade_repo = diy_trade_repo
    app.state.signature_repo = signature_repo
    app.state.backtest_repo = backtest_repo
    app.state.dataset_repo = dataset_repo
    app.state.risk_repo = risk_repo
    app.state.settings = settings

    # Load existing bots from DB
    try:
        db_bots = bot_repo.list_all()
        for db_bot in db_bots:
            config = BotConfig(
                bot_id=db_bot.id,
                bot_tag=db_bot.bot_tag,
                name=db_bot.name,
                symbol=db_bot.symbol,
                category=db_bot.category,
                seed_budget=db_bot.seed_budget,
                strategy_config=db_bot.strategy_config,
                bot_controls=db_bot.bot_controls,
                cycle_interval=db_bot.cycle_interval,
            )
            await manager.add_bot(config)
            if db_bot.status == "running":
                await manager.start_bot(db_bot.id)
        log.info("bots_loaded", count=len(db_bots))
    except Exception as e:
        log.error("failed_to_load_bots", error=str(e))

    await manager.start()

    yield

    # Shutdown
    log.info("shutting_down")
    await manager.shutdown()
    if market_data_feed:
        await market_data_feed.stop()


app = FastAPI(title="Malu", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(backtest_router)
app.include_router(bot_router)
app.include_router(dashboard_router)
app.include_router(dataset_router)
app.include_router(diy_router)
app.include_router(risk_router)
app.include_router(ws_router)


@app.get("/")
async def root():
    return {"service": "malu", "version": "0.1.0", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "malu"}
