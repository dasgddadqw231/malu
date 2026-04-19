from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import logging

from fastapi import APIRouter, HTTPException, Request

from malu.config import Settings
from pydantic import BaseModel
from malu.db.schemas import SignatureCreateRequest, SignatureUpdateRequest, DiyTradeDB, DiyTradeUpdateRequest
from malu.exchange.models import Category
from malu.llm import chat_refine_strategy, generate_strategy_from_prompt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diy", tags=["diy"])


def _get_client(request: Request):
    return request.app.state.bot_manager.client


def _get_diy_trade_repo(request: Request):
    return request.app.state.diy_trade_repo


def _get_signature_repo(request: Request):
    return request.app.state.signature_repo


def _get_bot_tags(request: Request) -> set[str]:
    """Collect all known bot tags to filter out bot-placed orders."""
    manager = request.app.state.bot_manager
    tags = set()
    for bot in manager.bots.values():
        tags.add(bot.config.bot_tag)
    # Also check DB for historical bots
    bot_repo = request.app.state.bot_repo
    for db_bot in bot_repo.list_all():
        tags.add(db_bot.bot_tag)
    return tags


def _is_human_order(order: dict, bot_tags: set[str]) -> bool:
    """Return True if the order was NOT placed by a malu bot."""
    link_id = order.get("orderLinkId", "")
    if not link_id:
        return True
    # Bot orders use the bot_tag as prefix in orderLinkId
    for tag in bot_tags:
        if link_id.startswith(tag):
            return False
    return True


# ── Fetch human trades from Bybit ──


@router.post("/sync")
async def sync_human_trades(
    request: Request,
    symbol: str | None = None,
    category: str = "linear",
    pages: int = 3,
):
    """Pull order history from Bybit, filter out bot orders, save human trades."""
    client = _get_client(request)
    diy_repo = _get_diy_trade_repo(request)
    bot_tags = _get_bot_tags(request)
    cat = Category(category)

    all_orders: list[dict] = []
    cursor = ""
    for _ in range(pages):
        orders, cursor = await client.get_order_history(
            category=cat, symbol=symbol, limit=50, cursor=cursor
        )
        all_orders.extend(orders)
        if not cursor:
            break

    # Filter human-only, filled orders
    human_orders = [
        o for o in all_orders
        if _is_human_order(o, bot_tags) and o.get("orderStatus") == "Filled"
    ]

    # Convert to DiyTradeDB
    trades = []
    for o in human_orders:
        filled_at = None
        updated_time = o.get("updatedTime")
        if updated_time:
            try:
                filled_at = datetime.fromtimestamp(
                    int(updated_time) / 1000, tz=timezone.utc
                )
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
        return {"synced": 0, "message": "No human trades found"}

    saved = diy_repo.upsert_many(trades)
    return {"synced": len(saved)}


# ── DIY Trades CRUD ──


@router.get("/trades")
async def list_diy_trades(
    request: Request,
    symbol: str | None = None,
    limit: int = 200,
):
    repo = _get_diy_trade_repo(request)
    trades = repo.list_all(symbol=symbol, limit=limit)
    return [t.model_dump() for t in trades]


@router.patch("/trades/{trade_id}")
async def update_diy_trade(trade_id: str, req: DiyTradeUpdateRequest, request: Request):
    repo = _get_diy_trade_repo(request)
    updated = repo.update(trade_id, req)
    if not updated:
        raise HTTPException(status_code=404, detail="Trade not found")
    return updated.model_dump()


@router.post("/trades/pair")
async def pair_trades(
    request: Request,
    entry_id: str,
    exit_id: str,
):
    """Link an entry trade and exit trade as a pair."""
    repo = _get_diy_trade_repo(request)
    pair_id = str(uuid.uuid4())

    entry = repo.update(entry_id, DiyTradeUpdateRequest(trade_pair_id=pair_id, pair_role="entry"))
    exit_ = repo.update(exit_id, DiyTradeUpdateRequest(trade_pair_id=pair_id, pair_role="exit"))

    if not entry or not exit_:
        raise HTTPException(status_code=404, detail="Trade not found")

    return {"pair_id": pair_id, "entry": entry.model_dump(), "exit": exit_.model_dump()}


# ── Signatures CRUD ──


@router.get("/signatures")
async def list_signatures(request: Request):
    repo = _get_signature_repo(request)
    sigs = repo.list_active()
    return [s.model_dump() for s in sigs]


@router.post("/signatures")
async def create_signature(req: SignatureCreateRequest, request: Request):
    repo = _get_signature_repo(request)
    sig = repo.create(req)
    return sig.model_dump()


@router.get("/signatures/{sig_id}")
async def get_signature(sig_id: str, request: Request):
    repo = _get_signature_repo(request)
    sig = repo.get(sig_id)
    if not sig:
        raise HTTPException(status_code=404, detail="Signature not found")
    return sig.model_dump()


@router.patch("/signatures/{sig_id}")
async def update_signature(sig_id: str, req: SignatureUpdateRequest, request: Request):
    repo = _get_signature_repo(request)
    data = {k: v for k, v in req.model_dump().items() if v is not None}
    updated = repo.update(sig_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Signature not found")
    return updated.model_dump()


@router.delete("/signatures/{sig_id}")
async def delete_signature(sig_id: str, request: Request):
    repo = _get_signature_repo(request)
    repo.delete(sig_id)
    return {"deleted": True}


# ── Signature Chat (iterative refinement) ──


class ChatNewRequest(BaseModel):
    name: str
    message: str
    dataset_id: str | None = None


class ChatMessageRequest(BaseModel):
    message: str


def _build_trade_context(trades: list[DiyTradeDB]) -> str | None:
    """Build a concise summary of trades for LLM context."""
    if not trades:
        return None

    stats = _analyze_trades(trades)
    rules = _extract_rules(trades)

    # Build symbol breakdown
    symbols: dict[str, int] = {}
    for t in trades:
        symbols[t.symbol] = symbols.get(t.symbol, 0) + 1

    # Time range
    filled_dates = [t.filled_at for t in trades if t.filled_at]
    time_range = ""
    if filled_dates:
        earliest = min(filled_dates).strftime("%Y-%m-%d")
        latest = max(filled_dates).strftime("%Y-%m-%d")
        time_range = f"Period: {earliest} ~ {latest}"

    lines = [
        f"Total trades: {stats['total_trades']} (Buy: {stats['buy_count']}, Sell: {stats['sell_count']})",
        f"Win rate: {stats['win_rate']}% ({stats['win_count']}W / {stats['loss_count']}L)",
        f"Total PnL: {stats['total_pnl']}, Avg PnL: {stats['avg_pnl']}",
        f"Max win: {stats['max_win']}, Max loss: {stats['max_loss']}",
        f"Avg position size: {stats['avg_qty']}, Avg price: {stats['avg_price']}",
        f"Symbols: {', '.join(f'{s}({c})' for s, c in sorted(symbols.items(), key=lambda x: -x[1]))}",
    ]
    if time_range:
        lines.append(time_range)

    # Add rationales if any
    rationales = [t.rationale for t in trades if t.rationale]
    if rationales:
        lines.append(f"\nUser's trade rationales (sample):")
        for r in rationales[:10]:
            lines.append(f"  - {r}")

    # Add tags
    all_tags: dict[str, int] = {}
    for t in trades:
        for tag in t.tags:
            all_tags[tag] = all_tags.get(tag, 0) + 1
    if all_tags:
        top_tags = sorted(all_tags.items(), key=lambda x: -x[1])[:10]
        lines.append(f"Common tags: {', '.join(f'{tag}({cnt})' for tag, cnt in top_tags)}")

    # Add individual trade details (up to 30)
    lines.append(f"\nRecent trades (up to 30):")
    lines.append("symbol | side | qty | price | pnl | leverage | time")
    for t in trades[:30]:
        price = f"{t.avg_price}" if t.avg_price else "-"
        pnl = f"{t.pnl}" if t.pnl else "-"
        time = t.filled_at.strftime("%m-%d %H:%M") if t.filled_at else "-"
        lines.append(f"{t.symbol} | {t.side} | {t.qty} | {price} | {pnl} | {t.leverage}x | {time}")

    return "\n".join(lines)


@router.post("/signatures/chat/new")
async def start_signature_chat(
    request: Request,
    body: ChatNewRequest,
):
    """Start a new signature via conversational refinement."""
    settings = Settings()
    if not settings.gemini_api_key:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")

    signature_repo = _get_signature_repo(request)

    # Load dataset trades for LLM context
    trade_context = None
    if body.dataset_id:
        dataset_repo = request.app.state.dataset_repo
        diy_trade_repo = _get_diy_trade_repo(request)
        ds = dataset_repo.get(body.dataset_id)
        if ds and ds.trade_ids:
            trades = diy_trade_repo.get_by_ids(ds.trade_ids)
            trade_context = _build_trade_context(trades)

    try:
        reply, strategy_config, rules = await chat_refine_strategy(
            user_message=body.message,
            current_config=None,
            current_rules=[],
            messages=[],
            api_key=settings.gemini_api_key,
            trade_context=trade_context,
        )
    except Exception as e:
        logger.exception("LLM chat failed")
        raise HTTPException(status_code=502, detail=f"LLM generation failed: {e}")

    # Save signature with conversation history
    chat_messages = [
        {"role": "user", "content": body.message},
        {"role": "assistant", "content": reply},
    ]

    sig = signature_repo.create(
        SignatureCreateRequest(
            name=body.name,
            description=body.message[:200],
            dataset_id=body.dataset_id,
            source_trade_ids=[],
            strategy_config=strategy_config,
            rules=rules,
            stats={"source": "chat", "turns": 1},
        )
    )

    # Save messages
    signature_repo.update(sig.id, {"messages": chat_messages})

    result = sig.model_dump()
    result["messages"] = chat_messages
    result["strategy_config"] = strategy_config
    result["rules"] = rules
    result["reply"] = reply
    return result


@router.post("/signatures/{sig_id}/chat")
async def chat_with_signature(
    request: Request,
    sig_id: str,
    body: ChatMessageRequest,
):
    """Send a message to refine an existing signature's strategy."""
    settings = Settings()
    if not settings.gemini_api_key:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")

    signature_repo = _get_signature_repo(request)
    sig = signature_repo.get(sig_id)
    if not sig:
        raise HTTPException(status_code=404, detail="Signature not found")

    # Load dataset trades for LLM context
    trade_context = None
    if sig.dataset_id:
        dataset_repo = request.app.state.dataset_repo
        diy_trade_repo = _get_diy_trade_repo(request)
        ds = dataset_repo.get(sig.dataset_id)
        if ds and ds.trade_ids:
            trades = diy_trade_repo.get_by_ids(ds.trade_ids)
            trade_context = _build_trade_context(trades)

    try:
        reply, strategy_config, rules = await chat_refine_strategy(
            user_message=body.message,
            current_config=sig.strategy_config,
            current_rules=sig.rules,
            messages=sig.messages,
            api_key=settings.gemini_api_key,
            trade_context=trade_context,
        )
    except Exception as e:
        logger.exception("LLM chat failed")
        raise HTTPException(status_code=502, detail=f"LLM generation failed: {e}")

    # Append to conversation history
    updated_messages = list(sig.messages) + [
        {"role": "user", "content": body.message},
        {"role": "assistant", "content": reply},
    ]

    # Update signature
    signature_repo.update(sig_id, {
        "strategy_config": strategy_config,
        "rules": rules,
        "messages": updated_messages,
        "stats": {**sig.stats, "turns": len(updated_messages) // 2},
    })

    updated = signature_repo.get(sig_id)
    result = updated.model_dump()
    result["reply"] = reply
    return result


# ── Generate strategy from annotated trades ──


@router.post("/generate")
async def generate_style_from_trades(
    request: Request,
    name: str,
    trade_ids: list[str],
    description: str | None = None,
):
    """Analyze annotated trades and generate a strategy_config."""
    diy_trade_repo = _get_diy_trade_repo(request)
    signature_repo = _get_signature_repo(request)

    trades = diy_trade_repo.get_by_ids(trade_ids)
    if not trades:
        raise HTTPException(status_code=400, detail="No trades found for given IDs")

    # Analyze trades to extract patterns
    stats = _analyze_trades(trades)
    rules = _extract_rules(trades)
    config = _build_strategy_config(stats, rules)

    sig = signature_repo.create(
        SignatureCreateRequest(
            name=name,
            description=description,
            source_trade_ids=trade_ids,
            strategy_config=config,
            rules=rules,
            stats=stats,
        )
    )
    return sig.model_dump()


@router.post("/signatures/from-prompt")
async def create_signature_from_prompt(
    request: Request,
    name: str,
    prompt: str,
    description: str | None = None,
    source_trade_ids: list[str] | None = None,
):
    """Create a signature from a natural language strategy description."""
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    signature_repo = _get_signature_repo(request)

    settings = Settings()
    if not settings.gemini_api_key:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")

    try:
        config, rules, stats = await generate_strategy_from_prompt(
            prompt, settings.gemini_api_key
        )
    except Exception as e:
        logger.exception("LLM strategy generation failed")
        raise HTTPException(status_code=502, detail=f"LLM generation failed: {e}")

    sig = signature_repo.create(
        SignatureCreateRequest(
            name=name,
            description=description or prompt[:200],
            source_trade_ids=source_trade_ids or [],
            strategy_config=config,
            rules=rules,
            stats=stats,
        )
    )
    return sig.model_dump()


def _analyze_trades(trades: list[DiyTradeDB]) -> dict:
    """Compute basic statistics from trade list."""
    total = len(trades)
    buys = [t for t in trades if t.side == "Buy"]
    sells = [t for t in trades if t.side == "Sell"]

    pnls = [float(t.pnl) for t in trades if t.pnl is not None]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    avg_qty = float(sum(t.qty for t in trades) / total) if total else 0
    avg_price = float(
        sum(t.avg_price for t in trades if t.avg_price) /
        len([t for t in trades if t.avg_price])
    ) if any(t.avg_price for t in trades) else 0

    return {
        "total_trades": total,
        "buy_count": len(buys),
        "sell_count": len(sells),
        "win_count": len(wins),
        "loss_count": len(losses),
        "win_rate": round(len(wins) / len(pnls) * 100, 1) if pnls else 0,
        "avg_pnl": round(sum(pnls) / len(pnls), 4) if pnls else 0,
        "total_pnl": round(sum(pnls), 4) if pnls else 0,
        "avg_qty": round(avg_qty, 8),
        "avg_price": round(avg_price, 2),
        "max_win": round(max(wins), 4) if wins else 0,
        "max_loss": round(min(losses), 4) if losses else 0,
    }


def _extract_rules(trades: list[DiyTradeDB]) -> list[dict]:
    """Extract human-readable rules from trade annotations."""
    rules = []

    # Gather unique rationales
    rationales = [t.rationale for t in trades if t.rationale]
    if rationales:
        rules.append({
            "type": "rationale_summary",
            "description": "ì¬ì©ì ì£¼ììì ì¶ì¶í í¸ë ì´ë ê·¼ê±°",
            "entries": rationales,
        })

    # Gather tags
    all_tags: dict[str, int] = {}
    for t in trades:
        for tag in t.tags:
            all_tags[tag] = all_tags.get(tag, 0) + 1
    if all_tags:
        rules.append({
            "type": "common_tags",
            "description": "ìì£¼ ì¬ì©ë í¸ë ì´ë íê·¸",
            "tags": dict(sorted(all_tags.items(), key=lambda x: -x[1])),
        })

    # Position sizing pattern
    qtys = [float(t.qty) for t in trades]
    if qtys:
        rules.append({
            "type": "position_sizing",
            "description": "ê³¼ê±° í¸ë ì´ë ê¸°ë° í¬ì§ì ì¬ì´ì¦ ë²ì",
            "min_qty": round(min(qtys), 8),
            "max_qty": round(max(qtys), 8),
            "avg_qty": round(sum(qtys) / len(qtys), 8),
        })

    # PnL-based risk management
    pnls = [float(t.pnl) for t in trades if t.pnl is not None]
    if pnls:
        losses = [p for p in pnls if p < 0]
        wins = [p for p in pnls if p > 0]
        if losses:
            rules.append({
                "type": "stop_loss_pattern",
                "description": "ê³¼ê±° ìµë ìì¤ ê¸°ë° ìì  í¨í´",
                "avg_loss": round(sum(losses) / len(losses), 4),
                "max_loss": round(min(losses), 4),
            })
        if wins:
            rules.append({
                "type": "take_profit_pattern",
                "description": "ê³¼ê±° ìµë ììµ ê¸°ë° ìµì  í¨í´",
                "avg_win": round(sum(wins) / len(wins), 4),
                "max_win": round(max(wins), 4),
            })

    return rules



def _build_strategy_config(stats: dict, rules: list[dict]) -> dict:
    """Build a bot-compatible strategy_config from analyzed patterns."""
    max_loss_pct = 5.0
    take_profit_pct = 8.0
    position_size_pct = 50

    for rule in rules:
        if rule["type"] == "stop_loss_pattern":
            max_loss_pct = min(abs(rule["avg_loss"]), 15.0)
            max_loss_pct = max(max_loss_pct, 1.0)
        if rule["type"] == "take_profit_pattern":
            take_profit_pct = min(rule["avg_win"], 20.0)
            take_profit_pct = max(take_profit_pct, 2.0)

    # Win rate determines aggressiveness of entry signals
    win_rate = stats.get("win_rate", 50)
    if win_rate >= 65:
        bb_std = 1.5
        rsi_oversold, rsi_overbought = 35, 65
    elif win_rate >= 45:
        bb_std = 2.0
        rsi_oversold, rsi_overbought = 30, 70
    else:
        bb_std = 2.5
        rsi_oversold, rsi_overbought = 25, 75

    # Add concrete rules
    concrete_rules = [
        {
            "type": "entry_long",
            "situation": f"가격이 하단 BB({bb_std}표준편차) 터치 AND RSI < {rsi_oversold}",
            "action": f"예산의 {position_size_pct}%로 롱 포지션 진입",
        },
        {
            "type": "entry_short",
            "situation": f"가격이 상단 BB({bb_std}표준편차) 터치 AND RSI > {rsi_overbought}",
            "action": f"예산의 {position_size_pct}%로 숏 포지션 진입",
        },
        {
            "type": "stop_loss",
            "situation": f"미실현 손익이 -{max_loss_pct}% 도달",
            "action": "즉시 포지션 청산",
        },
        {
            "type": "take_profit",
            "situation": f"미실현 수익이 +{take_profit_pct}% 도달",
            "action": "수익 확정을 위해 포지션 청산",
        },
    ]
    rules.extend(concrete_rules)

    rules.append({
        "type": "cycle_interval",
        "situation": "5.0초 간격",
        "action": "진입/청산 시그널 스캔",
        "description": "포지션 스캔 주기: 5.0초 (기본값)",
    })

    return {
        "judgment": {
            "module": "bb_rsi",
            "params": {
                "bb_period": 20,
                "bb_std": bb_std,
                "rsi_period": 14,
                "rsi_oversold": rsi_oversold,
                "rsi_overbought": rsi_overbought,
            },
        },
        "action": {
            "module": "market_order",
            "params": {"position_size_pct": position_size_pct},
        },
        "defense": {
            "module": "trailing_stop",
            "params": {
                "max_loss_pct": round(max_loss_pct, 1),
                "take_profit_pct": round(take_profit_pct, 1),
            },
        },
        "cycle_interval": 5.0,
        "_diy_meta": {
            "source": "diy",
            "win_rate": stats.get("win_rate", 0),
            "total_trades_analyzed": stats.get("total_trades", 0),
        },
    }
