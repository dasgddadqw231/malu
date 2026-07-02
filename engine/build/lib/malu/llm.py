"""Gemini LLM service for natural language → modular strategy config conversion."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# ── Load quant trading knowledge base ──
_KB_PATH = Path(__file__).parent / "strategy" / "QUANT_KNOWLEDGE_BASE.md"
_KNOWLEDGE_BASE = _KB_PATH.read_text(encoding="utf-8") if _KB_PATH.exists() else ""

STRATEGY_SCHEMA = """\
{
  "description": "전략에 대한 간단한 설명 (한글)",
  "entry": {
    "module": "<bb_rsi | bb_squeeze | ema_cross | macd_cross | rsi_divergence | bnf_dip_buy>",
    "params": {
      // bb_rsi params:
      //   bb_period: int 10-50 (default 20), bb_std: float 1.0-3.0 (default 2.0),
      //   rsi_period: int 7-28 (default 14), rsi_oversold: int 15-45 (default 30),
      //   rsi_overbought: int 55-85 (default 70)
      // bb_squeeze params:
      //   bb_period: int 10-50 (default 20), bb_std: float 1.5-3.0 (default 2.0),
      //   squeeze_lookback: int 20-100 (default 48), squeeze_percentile: float 5-30 (default 20),
      //   volume_multiple: float 1.0-3.0 (default 1.5)
      // ema_cross params:
      //   fast_period: int 5-50 (default 9), slow_period: int 20-200 (default 21),
      //   trend_ema: int 0|100-200 (default 200, 0=disable), require_trend: bool (default true)
      // macd_cross params:
      //   fast_ema: int 5-20 (default 12), slow_ema: int 15-40 (default 26),
      //   signal_period: int 5-15 (default 9), require_zero_cross: bool (default false)
      // rsi_divergence params:
      //   rsi_period: int 7-28 (default 14), lookback: int 10-50 (default 20),
      //   min_bars_between: int 3-10 (default 5), confirmation: bool (default true)
      // bnf_dip_buy params (BNF-style dip buying, best on "D" or "240"):
      //   drawdown_pct: float 20-50 (default 30), drawdown_max_pct: float 30-60 (default 45),
      //   high_lookback: int 60-200 (default 120), no_new_low_bars: int 3-10 (default 5),
      //   volume_multiple: float 1.2-3.0 (default 1.5),
      //   macd_fast: int 5-20 (default 12), macd_slow: int 15-40 (default 26),
      //   macd_signal: int 5-15 (default 9)
      // ALL modules: interval: str (default "15", options: "1","5","15","60","240","D")
    }
  },
  "exit": {
    "module": "<fixed_pct | atr_stop | trailing_atr | time_stop>",
    "params": {
      // fixed_pct: stop_loss_pct: float 0.5-15 (default 5), take_profit_pct: float 0.5-30 (default 10)
      // atr_stop: atr_period: int 7-21 (default 14), stop_atr_multiple: float 1-4 (default 2),
      //   tp_atr_multiple: float 1.5-6 (default 3), interval: str (default "15")
      // trailing_atr: method: "atr"|"pct" (default "atr"), atr_multiple: float 1.5-4 (default 2),
      //   trail_pct: float 1-10 (default 3), activate_after_pct: float 0-10 (default 1),
      //   atr_period: int 7-21 (default 14), interval: str (default "15")
      // time_stop: max_seconds: int 60-86400 (default 3600), min_profit_pct: float 0-5 (default 0.5)
    }
  },
  "sizing": {
    "module": "<fixed_fraction | risk_based | volatility_adjusted>",
    "params": {
      // fixed_fraction: size_pct: float 5-95 (default 50)
      // risk_based: risk_per_trade: float 0.1-3 (default 1), stop_loss_pct: float 0.5-10 (default 2)
      // volatility_adjusted: risk_per_trade: float 0.1-3 (default 1), atr_period: int 7-21 (default 14),
      //   atr_multiple: float 1.5-4 (default 2), interval: str (default "15")
    }
  },
  "filters": [
    // Optional array, 0 or more filters:
    // { "module": "trend_filter", "params": { "ema_period": 200, "interval": "D" } }
    // { "module": "regime_filter", "params": { "adx_period": 14, "trending_threshold": 25, "ranging_threshold": 20, "interval": "15" } }
    // { "module": "volatility_filter", "params": { "atr_period": 14, "max_atr_ratio": 5.0, "interval": "15" } }
  ],
  "leverage": <int, 1-100, leverage multiplier for futures. Default 1 (no leverage)>,
  "cycle_interval": <float, 2.0-120.0, seconds between market scans>,
  "rules": [
    {
      "type": "entry" | "exit" | "sizing" | "filter" | "cycle_interval",
      "situation": "<이 조건이 충족될 때 (한글)>",
      "action": "<이 행동을 실행 (한글)>"
    }
  ]
}"""

STYLE_GUIDELINES = """\
Module selection guidelines:
- "횡보장/mean reversion" entry → bb_rsi or rsi_divergence
- "추세추종/trend following" entry → ema_cross or macd_cross
- "돌파/breakout" entry → bb_squeeze
- "보수적/conservative" → exit: atr_stop (stop 2.5x ATR), sizing: risk_based (0.5%), filters: [trend_filter, volatility_filter]
- "공격적/aggressive" → exit: trailing_atr (1.5x ATR), sizing: risk_based (1.5%), filters: [trend_filter]
- "스캘핑/scalp" → entry interval "1" or "5", exit: fixed_pct (tight), sizing: fixed_fraction, cycle 2-5s
- "스윙/swing" → entry interval "60" or "240", exit: atr_stop or trailing_atr, sizing: volatility_adjusted, cycle 10-30s
- "마라톤/hold" → entry interval "D", exit: trailing_atr (wide), sizing: risk_based (0.5%), cycle 30-120s, leverage 1-3
- When user says "안전하게" → add volatility_filter + trend_filter, use risk_based sizing with low risk_per_trade, leverage 1-2
- "레버리지 높게" → leverage 10-20 (requires tight stop_loss_pct, warn about liquidation risk)
- Leverage guidelines: scalp 5-20x, day-trade 3-10x, swing 2-5x, position 1-3x
- IMPORTANT: Higher leverage requires tighter stops. Rule of thumb: stop_loss_pct * leverage < 50% to avoid liquidation
- Risk-reward: TP generally >= 1.5x SL for trend, >= 1.0x for mean reversion
- IMPORTANT: All rules' "situation" and "action" fields MUST be in Korean (한글)
- Always produce 4-6 rules covering entry, exit, sizing, and optionally filter/cycle_interval
- If user specifies exact values (e.g. "손절 3%"), use those exact values
- Match interval to strategy type: scalp(1/5), day(15), swing(60/240), position(D)"""

SYSTEM_PROMPT = f"""\
You are an expert crypto futures quant trading strategist with deep knowledge of:
- Technical indicators (BB, RSI, MACD, EMA, VWAP, ATR, Keltner Channels)
- Risk management (Kelly Criterion, ATR-based position sizing, R-multiple exits)
- Market microstructure (funding rates, liquidation levels, volatility regimes)
- Strategy archetypes (mean reversion, trend following, breakout, scalping, swing, position)

You operate on Bybit USDT Linear Perpetual contracts.

The user will describe their trading style in natural language (Korean or English).
Your job is to convert it into a MODULAR trading strategy configuration by selecting
the best combination of entry, exit, sizing, and filter modules.

You MUST respond with ONLY valid JSON (no markdown, no explanation) in this exact schema:

{STRATEGY_SCHEMA}

{STYLE_GUIDELINES}

REFERENCE KNOWLEDGE (use this to make informed parameter decisions):

{_KNOWLEDGE_BASE}
"""

CHAT_SYSTEM_PROMPT = f"""\
You are an expert crypto futures quant trading strategist assistant.
You help the user iteratively build and refine their MODULAR trading strategy through conversation.
You have deep expertise in quantitative trading, risk management, and crypto market microstructure.

The strategy is built from independent modules that can be swapped:
- Entry module: determines WHEN to enter (bb_rsi, bb_squeeze, ema_cross, macd_cross, rsi_divergence, bnf_dip_buy)
- Exit module: determines WHEN to exit (fixed_pct, atr_stop, trailing_atr, time_stop)
- Sizing module: determines HOW MUCH to trade (fixed_fraction, risk_based, volatility_adjusted)
- Filter modules: determine IF trading is allowed (trend_filter, regime_filter, volatility_filter)

You MUST respond with valid JSON in this schema:
{{
  "reply": "<your conversational response in the user's language (Korean if they use Korean). Explain what you changed and WHY from a quant perspective. Keep it concise (2-4 sentences). Ask a follow-up question to help refine further.>",
  "strategy": {STRATEGY_SCHEMA}
}}

{STYLE_GUIDELINES}

IMPORTANT:
- The "reply" field is your conversational response. Be helpful, professional, and educational.
- Reference quant concepts when explaining (R-multiple, ATR-based stops, Kelly sizing, regime detection, etc.)
- Proactively warn about risk issues (position too large, SL too tight, leverage too high)
- The "strategy" field is the COMPLETE current strategy after applying the user's request.
- When user says "진입만 바꿔줘" → change only the entry module, preserve everything else.
- When user says "손절 좀 더 타이트하게" → modify only the exit module params.
- Always include the full strategy object, not just the changes.

REFERENCE KNOWLEDGE (use this to make informed parameter decisions):

{_KNOWLEDGE_BASE}
"""

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"


def _parse_gemini_json(data: dict) -> dict:
    """Extract and parse JSON from Gemini response."""
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text.strip())


def _build_strategy_config(result: dict, prompt: str) -> dict:
    """Convert raw LLM result into our modular strategy_config format."""
    entry = result.get("entry", {})
    exit_ = result.get("exit", {})
    sizing = result.get("sizing", {})
    filters = result.get("filters", [])

    # Determine entry module and params
    entry_module = entry.get("module", "bb_rsi")
    entry_params = entry.get("params", {})

    # Determine exit module and params
    exit_module = exit_.get("module", "fixed_pct")
    exit_params = exit_.get("params", {})

    # Determine sizing module and params
    sizing_module = sizing.get("module", "fixed_fraction")
    sizing_params = sizing.get("params", {})

    # Build filter configs
    filter_configs = []
    for f in filters:
        if isinstance(f, dict) and "module" in f:
            filter_configs.append({
                "module": f["module"],
                "params": f.get("params", {}),
            })

    # Map exit params for backward compatibility
    # fixed_pct uses stop_loss_pct/take_profit_pct
    # but old code used max_loss_pct/take_profit_pct
    if exit_module in ("fixed_pct", "trailing_stop"):
        if "max_loss_pct" not in exit_params and "stop_loss_pct" in exit_params:
            exit_params["max_loss_pct"] = exit_params["stop_loss_pct"]

    # For action module, derive size_pct from sizing if fixed_fraction
    action_params = {}
    if sizing_module == "fixed_fraction":
        action_params["size_pct"] = sizing_params.get("size_pct", 50) / 100
    else:
        action_params["size_pct"] = 0.5  # default, sizing module will override

    config = {
        "judgment": {
            "module": entry_module,
            "params": entry_params,
        },
        "action": {
            "module": "market_order",
            "params": action_params,
        },
        "defense": {
            "module": exit_module,
            "params": exit_params,
        },
        "sizing": {
            "module": sizing_module,
            "params": sizing_params,
        },
        "filters": filter_configs,
        "leverage": int(result.get("leverage", 1)),
        "cycle_interval": result.get("cycle_interval", 5.0),
        "_diy_meta": {
            "source": "natural_language",
            "prompt": prompt,
        },
    }

    return config


# ── Legacy conversion helper ──

def _build_strategy_config_legacy(result: dict, prompt: str) -> dict:
    """Fallback: convert old-format LLM result (flat judgment/action/defense)."""
    j = result.get("judgment", {})
    a = result.get("action", {})
    d = result.get("defense", {})

    return {
        "judgment": {
            "module": "bb_rsi",
            "params": {
                "bb_period": j.get("bb_period", 20),
                "bb_std": j.get("bb_std", 2.0),
                "rsi_period": j.get("rsi_period", 14),
                "rsi_oversold": j.get("rsi_oversold", 30),
                "rsi_overbought": j.get("rsi_overbought", 70),
            },
        },
        "action": {
            "module": "market_order",
            "params": {
                "size_pct": a.get("position_size_pct", 50) / 100,
            },
        },
        "defense": {
            "module": "fixed_pct",
            "params": {
                "max_loss_pct": d.get("max_loss_pct", 5.0),
                "take_profit_pct": d.get("take_profit_pct", 10.0),
            },
        },
        "leverage": int(result.get("leverage", 1)),
        "cycle_interval": result.get("cycle_interval", 5.0),
        "_diy_meta": {
            "source": "natural_language",
            "prompt": prompt,
        },
    }


def _convert_result(result: dict, prompt: str) -> dict:
    """Auto-detect result format and convert accordingly."""
    if "entry" in result:
        # New modular format
        return _build_strategy_config(result, prompt)
    else:
        # Legacy flat format
        return _build_strategy_config_legacy(result, prompt)


async def _call_gemini(contents: list[dict], api_key: str) -> dict:
    """Make a Gemini API call and return parsed JSON."""
    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.3,
            "responseMimeType": "application/json",
        },
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            GEMINI_URL,
            headers={
                "Content-Type": "application/json",
                "X-goog-api-key": api_key,
            },
            json=payload,
        )
        resp.raise_for_status()

    return _parse_gemini_json(resp.json())


async def generate_strategy_from_prompt(
    prompt: str,
    api_key: str,
) -> tuple[dict, list[dict], dict]:
    """Call Gemini to convert natural language into strategy config.

    Returns (strategy_config, rules, stats).
    """
    contents = [
        {
            "role": "user",
            "parts": [{"text": SYSTEM_PROMPT + "\n\nUser strategy description:\n" + prompt}],
        }
    ]

    result = await _call_gemini(contents, api_key)
    logger.info("LLM strategy result: %s", json.dumps(result, ensure_ascii=False)[:500])

    strategy_config = _convert_result(result, prompt)
    rules = result.get("rules", [])
    stats = {
        "source": "natural_language",
        "prompt": prompt,
        "description": result.get("description", ""),
    }

    return strategy_config, rules, stats


async def chat_refine_strategy(
    user_message: str,
    current_config: dict | None,
    current_rules: list[dict],
    messages: list[dict],
    api_key: str,
    trade_context: str | None = None,
) -> tuple[str, dict, list[dict]]:
    """Iteratively refine a strategy through conversation.

    Args:
        user_message: The user's new message
        current_config: Current strategy_config (None if first message)
        current_rules: Current rules list
        messages: Conversation history [{role, content}, ...]
        api_key: Gemini API key
        trade_context: Optional summary of user's past trades from a dataset

    Returns (reply, strategy_config, rules).
    """
    # Build conversation contents for Gemini
    contents: list[dict] = []

    # Inject trade context into system prompt if available
    dataset_section = ""
    if trade_context:
        dataset_section = f"\n\nUSER'S PAST TRADE DATA (use this to inform your recommendations):\n{trade_context}\n"

    # First message includes system prompt
    if not messages:
        # First turn — treat as initial strategy description
        first_text = CHAT_SYSTEM_PROMPT + dataset_section + "\n\nUser's initial strategy description:\n" + user_message
        contents.append({"role": "user", "parts": [{"text": first_text}]})
    else:
        # Multi-turn — include history
        # First message with system prompt
        contents.append({
            "role": "user",
            "parts": [{"text": CHAT_SYSTEM_PROMPT + dataset_section + "\n\nUser's initial strategy description:\n" + messages[0]["content"]}],
        })

        # Reconstruct conversation history
        for msg in messages[1:]:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}],
            })

        # Add current strategy context + new message
        context = ""
        if current_config:
            context = f"\n\n[Current strategy state:\n{json.dumps(current_config, ensure_ascii=False)}\nCurrent rules:\n{json.dumps(current_rules, ensure_ascii=False)}]\n\n"
        contents.append({
            "role": "user",
            "parts": [{"text": context + "User message:\n" + user_message}],
        })

    result = await _call_gemini(contents, api_key)
    logger.info("LLM chat result: %s", json.dumps(result, ensure_ascii=False)[:500])

    reply = result.get("reply", "Strategy updated.")
    strategy = result.get("strategy", result)
    strategy_config = _convert_result(strategy, user_message)
    rules = strategy.get("rules", current_rules)

    return reply, strategy_config, rules
