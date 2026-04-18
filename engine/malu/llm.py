"""Gemini LLM service for natural language → strategy config conversion."""

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
  "judgment": {
    "bb_period": <int, 10-50, default 20>,
    "bb_std": <float, 1.0-3.0, how wide the Bollinger Band — lower=more signals, higher=fewer>,
    "rsi_period": <int, 7-28, default 14>,
    "rsi_oversold": <int, 15-45, below this RSI triggers LONG>,
    "rsi_overbought": <int, 55-85, above this RSI triggers SHORT>
  },
  "action": {
    "position_size_pct": <int, 5-95, percent of budget per trade>
  },
  "defense": {
    "max_loss_pct": <float, 0.5-15.0, stop-loss threshold>,
    "take_profit_pct": <float, 0.5-30.0, take-profit threshold>
  },
  "cycle_interval": <float, 2.0-120.0, seconds between market scans>,
  "rules": [
    {
      "type": "entry" | "stop_loss" | "take_profit" | "position_size" | "cycle_interval",
      "situation": "<이 조건이 충족될 때>",
      "action": "<이 행동을 실행>"
    }
  ]
}"""

STYLE_GUIDELINES = """\
Guidelines:
- "보수적/conservative" → wider bb_std (2.0-2.5), tighter rsi thresholds (35/65), smaller position (10-20%), lower leverage, risk_per_trade 0.3-0.5%, SL 2.5x ATR, TP >= 1.5R
- "공격적/aggressive" → narrow bb_std (1.5-2.0), wider rsi thresholds (25/75), larger position (40-70%), higher leverage, risk_per_trade 1-2%, SL 1.5x ATR
- "스캘핑/scalp" → tight SL/TP (0.1-0.5%), fast cycle (2-5s), RSI period 7, BB period 10, leverage 5-20x, win rate target 60-70%
- "스윙/swing" → moderate SL/TP (3-7%), slower cycle (10-30s), RSI period 14-21, multi-timeframe confluence, leverage 2-5x
- "마라톤/hold" → wide SL/TP (5-15%), slow cycle (30-120s), BB period 50, 50/200 EMA golden cross, leverage 1-3x
- "평균회귀/mean reversion" → trade when ADX < 25, BB mean reversion setup, RSI extremes, target middle band
- "추세추종/trend following" → trade when ADX > 25, EMA alignment, momentum confirmation, trail stops
- IMPORTANT: All rules' "situation" and "action" fields MUST be written in Korean (한글). Example: "situation": "가격이 하단 BB 터치 AND RSI < 30", "action": "예산의 50%로 롱 진입"
- Always produce 4-6 rules covering entry, position_size, stop_loss, take_profit, cycle_interval
- Risk-reward ratio must make sense: TP generally >= 1.5x SL for trend, >= 1.0x for mean reversion
- Position sizing should follow volatility-adjusted principles (reduce size in high vol)
- Include confluence scoring logic in rules when appropriate (min 3/5 signals for entry)
- If user specifies exact percentages (e.g. "손절 3%"), use those exact values
- Consider drawdown limits: daily 2-3%, weekly 5-7%, monthly 10-15%"""

SYSTEM_PROMPT = f"""\
You are an expert crypto futures quant trading strategist with deep knowledge of:
- Technical indicators (BB, RSI, MACD, EMA, VWAP, ATR, Keltner Channels)
- Risk management (Kelly Criterion, ATR-based position sizing, R-multiple exits)
- Market microstructure (funding rates, liquidation levels, volatility regimes)
- Strategy archetypes (mean reversion, trend following, breakout, scalping, swing, position)

You operate on Bybit USDT Linear Perpetual contracts.

The user will describe their trading style in natural language (Korean or English).
Your job is to convert it into a precise, professional-grade trading strategy configuration
grounded in quantitative trading principles.

You MUST respond with ONLY valid JSON (no markdown, no explanation) in this exact schema:

{STRATEGY_SCHEMA}

{STYLE_GUIDELINES}

REFERENCE KNOWLEDGE (use this to make informed parameter decisions):

{_KNOWLEDGE_BASE}
"""

CHAT_SYSTEM_PROMPT = f"""\
You are an expert crypto futures quant trading strategist assistant.
You help the user iteratively build and refine their trading strategy through conversation.
You have deep expertise in quantitative trading, risk management, and crypto market microstructure.

You MUST respond with valid JSON in this schema:
{{
  "reply": "<your conversational response in the user's language (Korean if they use Korean). Explain what you changed and WHY from a quant perspective (reference specific concepts like R-multiple, ATR-based stops, Kelly sizing, regime detection, etc). Keep it concise (2-4 sentences). Ask a follow-up question to help refine further. Proactively suggest improvements based on quant best practices.>",
  "strategy": {STRATEGY_SCHEMA}
}}

{STYLE_GUIDELINES}

IMPORTANT:
- The "reply" field is your conversational response to the user. Be helpful, professional, and educational.
- When explaining changes, reference quant trading concepts (e.g. "R:R 비율을 2:1로 조정했습니다" or "ATR 기반으로 변동성에 맞게 손절을 설정했습니다")
- Proactively warn about risk issues (e.g. position too large, SL too tight for volatility, leverage too high)
- The "strategy" field is the COMPLETE current strategy after applying the user's request.
- When the user says things like "손절 좀 더 타이트하게", modify ONLY the relevant parameters.
- Preserve all other settings from the current strategy unless the user asks to change them.
- If the user's request is ambiguous, apply reasonable changes and explain what you did.
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
    """Convert raw LLM result into our strategy_config format."""
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
                "position_size_pct": a.get("position_size_pct", 50),
            },
        },
        "defense": {
            "module": "trailing_stop",
            "params": {
                "max_loss_pct": d.get("max_loss_pct", 5.0),
                "take_profit_pct": d.get("take_profit_pct", 10.0),
            },
        },
        "cycle_interval": result.get("cycle_interval", 5.0),
        "_diy_meta": {
            "source": "natural_language",
            "prompt": prompt,
        },
    }


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

    strategy_config = _build_strategy_config(result, prompt)
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
) -> tuple[str, dict, list[dict]]:
    """Iteratively refine a strategy through conversation.

    Args:
        user_message: The user's new message
        current_config: Current strategy_config (None if first message)
        current_rules: Current rules list
        messages: Conversation history [{role, content}, ...]
        api_key: Gemini API key

    Returns (reply, strategy_config, rules).
    """
    # Build conversation contents for Gemini
    contents: list[dict] = []

    # First message includes system prompt
    if not messages:
        # First turn — treat as initial strategy description
        first_text = CHAT_SYSTEM_PROMPT + "\n\nUser's initial strategy description:\n" + user_message
        contents.append({"role": "user", "parts": [{"text": first_text}]})
    else:
        # Multi-turn — include history
        # First message with system prompt
        contents.append({
            "role": "user",
            "parts": [{"text": CHAT_SYSTEM_PROMPT + "\n\nUser's initial strategy description:\n" + messages[0]["content"]}],
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
    strategy_config = _build_strategy_config(strategy, user_message)
    rules = strategy.get("rules", current_rules)

    return reply, strategy_config, rules
