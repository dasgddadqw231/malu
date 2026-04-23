"""
전략 파라미터 최적화 스크립트.

1시간봉 기준, 레버리지 3배, 스윙 지지/저항 방어 + 4H 추세 필터 지원.

Usage:
    cd engine
    .venv/bin/python -m scripts.optimize --symbol BTCUSDT --start 2026-01-01 --end 2026-04-23
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from malu.backtest.data import HistoricalDataFetcher
from malu.backtest.simulator import BacktestConfig, BacktestSimulator
from malu.config import Settings
from malu.exchange.bybit_client import BybitClient


# ──────────────────────────────────────────────
# Parameter grids
# ──────────────────────────────────────────────

def _bb_rsi_grid() -> list[dict]:
    combos = []
    for bb_period in [12, 15, 20, 25, 30]:
        for bb_std in [1.5, 1.8, 2.0, 2.5]:
            for rsi_period in [7, 10, 14]:
                for rsi_oversold in [20, 25, 30]:
                    for rsi_overbought in [70, 75, 80]:
                        combos.append({
                            "module": "bb_rsi",
                            "params": {
                                "bb_period": bb_period,
                                "bb_std": bb_std,
                                "rsi_period": rsi_period,
                                "rsi_oversold": rsi_oversold,
                                "rsi_overbought": rsi_overbought,
                            },
                        })
    return combos


def _macd_cross_grid() -> list[dict]:
    combos = []
    for fast in [6, 8, 12]:
        for slow in [21, 26, 30]:
            for signal in [7, 9, 12]:
                for require_zero in [False, True]:
                    if fast >= slow:
                        continue
                    combos.append({
                        "module": "macd_cross",
                        "params": {
                            "fast_ema": fast,
                            "slow_ema": slow,
                            "signal_period": signal,
                            "require_zero_cross": require_zero,
                        },
                    })
    return combos


def _ema_cross_grid() -> list[dict]:
    combos = []
    for fast in [3, 5, 9, 13]:
        for slow in [15, 21, 30, 50]:
            for trend_ema in [0, 100, 200]:
                if fast >= slow:
                    continue
                combos.append({
                    "module": "ema_cross",
                    "params": {
                        "fast_period": fast,
                        "slow_period": slow,
                        "trend_ema": trend_ema,
                        "require_trend": trend_ema > 0,
                    },
                })
    return combos


STRATEGY_GRIDS = {
    "bb_rsi": _bb_rsi_grid(),
    "macd_cross": _macd_cross_grid(),
    "ema_cross": _ema_cross_grid(),
}

# Defense grids
DEFENSE_GRID_FIXED = [
    {"module": "fixed_pct", "params": {"stop_loss_pct": sl, "take_profit_pct": tp}}
    for sl in [2.0, 3.0, 5.0, 7.0]
    for tp in [3.0, 5.0, 8.0, 10.0]
]

DEFENSE_GRID_ATR = [
    {"module": "atr_stop", "params": {"atr_period": 14, "stop_atr_multiple": sl, "tp_atr_multiple": tp}}
    for sl in [1.5, 2.0, 3.0]
    for tp in [3.0, 4.5, 6.0]
]

DEFENSE_GRID_SWING = [
    {"module": "swing_sr", "params": {
        "swing_lookback": lb, "swing_left_bars": left, "swing_right_bars": 2,
        "sl_buffer_pct": buf, "min_rr": rr,
    }}
    for lb in [30, 50]
    for left in [3, 5]
    for buf in [0.2]
    for rr in [1.5, 2.0, 2.5]
]

DEFENSE_GRID = DEFENSE_GRID_FIXED + DEFENSE_GRID_ATR + DEFENSE_GRID_SWING

# Trend filter options (None = disabled, or 4H EMA configs)
TREND_FILTER_OPTIONS: list[list[dict]] = [
    [],  # no filter
    [{"module": "trend_filter", "params": {"ema_period": 50, "interval": "240"}}],
    [{"module": "trend_filter", "params": {"ema_period": 100, "interval": "240"}}],
]


def _date_to_ms(date_str: str) -> int:
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def run_single(
    candles,
    funding_rates,
    judgment_cfg: dict,
    defense_cfg: dict,
    filters_cfg: list[dict],
    leverage: int = 3,
    initial_capital: Decimal = Decimal("10000"),
) -> dict | None:
    """Run one backtest using pre-fetched data. Returns summary or None."""
    config = BacktestConfig(
        symbol="",
        leverage=leverage,
        strategy_config={
            "judgment": judgment_cfg,
            "defense": defense_cfg,
            "action": {"params": {"position_size_pct": 100}},
            "filters": filters_cfg,
            "max_consecutive_losses": 3,
            "cooldown_bars": 12,
        },
        slippage_bps=5,
        fee_rate=Decimal("0.00055"),
        initial_capital=initial_capital,
    )

    try:
        sim = BacktestSimulator(config)
        result = sim.run_from_candles(candles, funding_rates)
    except Exception:
        return None

    if result.total_trades < 3:
        return None

    return {
        "judgment": judgment_cfg,
        "defense": defense_cfg,
        "filters": filters_cfg,
        "leverage": leverage,
        "net_pnl": float(result.net_pnl),
        "return_pct": float(result.net_pnl / initial_capital * 100),
        "win_rate": result.win_rate,
        "max_drawdown": result.max_drawdown,
        "sharpe_ratio": result.sharpe_ratio,
        "total_trades": result.total_trades,
        "total_fees": float(result.total_fees),
        "avg_pnl_per_trade": float(result.net_pnl / result.total_trades),
    }


async def main():
    parser = argparse.ArgumentParser(description="전략 파라미터 최적화 (1H + 스윙SR)")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--start", default="2026-01-01", help="시작일 YYYY-MM-DD")
    parser.add_argument("--end", default="2026-04-23", help="종료일 YYYY-MM-DD")
    parser.add_argument("--intervals", default="60", help="봉 간격 (쉼표 구분)")
    parser.add_argument("--leverage", type=int, default=3)
    parser.add_argument("--top", type=int, default=10, help="상위 N개 결과 표시")
    parser.add_argument("--strategies", default="bb_rsi,macd_cross,ema_cross")
    parser.add_argument("--max-combos", type=int, default=0, help="0=무제한")
    parser.add_argument("--defense-type", default="all",
                        help="all | fixed | atr | swing")
    parser.add_argument("--no-trend-filter", action="store_true",
                        help="추세 필터 조합 제외 (속도 향상)")
    args = parser.parse_args()

    settings = Settings()
    client = BybitClient(
        api_key=settings.bybit_api_key,
        api_secret=settings.bybit_api_secret,
        testnet=settings.bybit_testnet,
    )

    intervals = [i.strip() for i in args.intervals.split(",")]
    strategy_names = [s.strip() for s in args.strategies.split(",")]
    start_ms = _date_to_ms(args.start)
    end_ms = _date_to_ms(args.end)

    # Select defense grid
    if args.defense_type == "fixed":
        defense_grid = DEFENSE_GRID_FIXED
    elif args.defense_type == "atr":
        defense_grid = DEFENSE_GRID_ATR
    elif args.defense_type == "swing":
        defense_grid = DEFENSE_GRID_SWING
    else:
        defense_grid = DEFENSE_GRID

    # Select trend filter options
    if args.no_trend_filter:
        trend_options = [[]]  # no filter only
    else:
        trend_options = TREND_FILTER_OPTIONS

    # ── Step 1: Fetch data once per interval ──
    print(f"\n{'='*70}")
    print(f"  전략 파라미터 최적화 (개편: 1H + 스윙SR + 4H추세)")
    print(f"  Symbol: {args.symbol} | 기간: {args.start} → {args.end}")
    print(f"  레버리지: {args.leverage}x | 전략: {', '.join(strategy_names)}")
    print(f"  인터벌: {', '.join(intervals)} | 방어: {args.defense_type}")
    print(f"{'='*70}")

    fetcher = HistoricalDataFetcher(client)
    data_cache: dict[str, tuple] = {}

    print(f"\n📊 데이터 로딩 중...")
    funding_rates = await fetcher.fetch_funding_rates(args.symbol, start_ms, end_ms)
    print(f"   펀딩비: {len(funding_rates)}건")

    for interval in intervals:
        candles = await fetcher.fetch_klines(args.symbol, interval, start_ms, end_ms)
        data_cache[interval] = (candles, funding_rates)
        print(f"   {interval}분봉: {len(candles)}봉")

    # ── Step 2: Build all combos ──
    all_combos: list[tuple[str, dict, dict, list[dict]]] = []
    for strat_name in strategy_names:
        if strat_name not in STRATEGY_GRIDS:
            print(f"   ⚠️  Unknown: {strat_name}")
            continue
        for interval in intervals:
            for jcfg in STRATEGY_GRIDS[strat_name]:
                cfg = {
                    "module": jcfg["module"],
                    "params": {**jcfg["params"], "interval": interval},
                }
                for defense in defense_grid:
                    for trend_filter in trend_options:
                        all_combos.append((interval, cfg, defense, trend_filter))

    if args.max_combos > 0:
        all_combos = all_combos[:args.max_combos]

    total = len(all_combos)
    print(f"\n🔄 총 {total:,}개 조합 백테스트 시작...\n")

    # ── Step 3: Run all backtests ──
    results: list[dict] = []
    start_time = time.time()

    for i, (interval, jcfg, defense, trend_filter) in enumerate(all_combos):
        candles, funding = data_cache[interval]
        r = run_single(candles, funding, jcfg, defense, trend_filter,
                       leverage=args.leverage)
        if r is not None:
            r["interval"] = interval
            results.append(r)

        if (i + 1) % 500 == 0 or (i + 1) == total:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            eta = (total - i - 1) / rate if rate > 0 else 0
            valid = len(results)
            print(f"  [{i+1:>6,}/{total:,}] {rate:,.0f}/s | 유효: {valid:,} | ETA: {eta:.0f}s")

    elapsed = time.time() - start_time
    print(f"\n✅ 완료: {total:,}개 테스트, {len(results):,}개 유효 ({elapsed:.1f}초, {total/elapsed:,.0f}/s)")

    if not results:
        print("❌ 유효한 결과가 없습니다.")
        return

    # ── Step 4: Rank results ──
    results.sort(key=lambda r: (r["net_pnl"], r["sharpe_ratio"], -r["max_drawdown"]), reverse=True)

    top = results[:args.top]
    print(f"\n{'='*70}")
    print(f"  🏆 상위 {len(top)}개 전략")
    print(f"{'='*70}")

    for i, r in enumerate(top, 1):
        module = r["judgment"]["module"]
        params = r["judgment"]["params"]
        defense = r["defense"]
        d_mod = defense.get("module", "fixed_pct")
        d_params = defense.get("params", defense)
        filters = r.get("filters", [])
        trend_str = "없음"
        for f in filters:
            if f.get("module") == "trend_filter":
                fp = f.get("params", {})
                trend_str = f"EMA{fp.get('ema_period', '?')} {fp.get('interval', '?')}분"

        print(f"\n{'─'*70}")
        print(f"  #{i}  [{module}] {r['interval']}분봉 | 레버리지 {r['leverage']}x")
        print(f"{'─'*70}")
        print(f"  💰 순수익: ${r['net_pnl']:>+10,.2f}  ({r['return_pct']:+.1f}%)")
        print(f"  📈 승률: {r['win_rate']:.1f}%  |  샤프: {r['sharpe_ratio']:.2f}  |  MDD: {r['max_drawdown']:.1f}%")
        print(f"  🔢 거래수: {r['total_trades']}  |  건당 평균: ${r['avg_pnl_per_trade']:+.2f}  |  수수료: ${r['total_fees']:.2f}")
        print(f"  🎯 Entry: {json.dumps({k:v for k,v in params.items() if k != 'interval'}, ensure_ascii=False)}")
        if d_mod == "swing_sr":
            print(f"  🛡️  Exit:  SwingSR lb={d_params['swing_lookback']} L={d_params['swing_left_bars']} buf={d_params['sl_buffer_pct']}% R:R>={d_params['min_rr']}")
        elif d_mod == "atr_stop":
            print(f"  🛡️  Exit:  ATR SL={d_params['stop_atr_multiple']}x / TP={d_params['tp_atr_multiple']}x")
        else:
            print(f"  🛡️  Exit:  SL={d_params.get('stop_loss_pct', d_params.get('max_loss_pct', '?'))}% / TP={d_params.get('take_profit_pct', '?')}%")
        print(f"  📊 추세필터: {trend_str}")

    # ── Step 5: Output best as bot-ready config ──
    best = top[0]
    best_params = best["judgment"]["params"]
    best_defense = best["defense"]
    best_filters = best.get("filters", [])

    bot_config = {
        "name": f"최적화_{best['judgment']['module']}_{best['interval']}m_v3",
        "symbol": args.symbol,
        "category": "linear",
        "seed_budget": 10000,
        "leverage": args.leverage,
        "cycle_interval": 5.0,
        "strategy_config": {
            "judgment": best["judgment"],
            "defense": best_defense,
            "action": {
                "module": "market_order",
                "params": {"size_pct": 1.0},
            },
            "sizing": None,
            "filters": best_filters,
            "max_consecutive_losses": 3,
            "cooldown_bars": 12,
        },
        "bot_controls": {
            "daily_loss_limit_pct": 5.0,
            "daily_trade_limit": 20,
            "consecutive_loss_limit": 5,
            "max_position_pct": 15.0,
        },
    }

    output_path = Path(__file__).parent / "best_strategy.json"
    output_path.write_text(json.dumps(bot_config, indent=2, ensure_ascii=False))

    print(f"\n{'='*70}")
    print(f"  📁 봇 세팅용 config 저장: {output_path}")
    print(f"{'='*70}")
    print(f"\n{json.dumps(bot_config, indent=2, ensure_ascii=False)}")

    # 요약 테이블
    print(f"\n{'='*70}")
    print(f"  📊 상위 전략 요약 비교")
    print(f"{'='*70}")
    print(f"  {'#':>2} {'전략':<12} {'봉':>3} {'방어':<10} {'추세':>6} {'수익':>10} {'수익률':>7} {'승률':>5} {'샤프':>5} {'MDD':>5} {'거래':>4}")
    print(f"  {'─'*80}")
    for i, r in enumerate(top, 1):
        m = r["judgment"]["module"]
        d = r["defense"]
        d_mod = d.get("module", "fixed_pct")
        d_params = d.get("params", d)
        if d_mod == "swing_sr":
            d_str = f"SR{d_params['swing_lookback']}"
        elif d_mod == "atr_stop":
            d_str = f"ATR{d_params['stop_atr_multiple']}/{d_params['tp_atr_multiple']}"
        else:
            d_str = f"{d_params.get('stop_loss_pct', '?')}/{d_params.get('take_profit_pct', '?')}"
        filters = r.get("filters", [])
        t_str = "-"
        for f in filters:
            if f.get("module") == "trend_filter":
                t_str = f"E{f['params']['ema_period']}"
        print(f"  {i:>2} {m:<12} {r['interval']:>3} {d_str:<10} {t_str:>6} ${r['net_pnl']:>+9,.0f} {r['return_pct']:>+6.1f}% {r['win_rate']:>4.0f}% {r['sharpe_ratio']:>5.2f} {r['max_drawdown']:>4.1f}% {r['total_trades']:>4}")


if __name__ == "__main__":
    asyncio.run(main())
