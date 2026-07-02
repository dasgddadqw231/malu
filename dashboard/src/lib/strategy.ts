// Strategy configuration helpers for direct (JSON-based) bot strategy editing.
// Mirrors the engine's module registries in engine/malu/core/bot.py.

export const DEFAULT_STRATEGY_CONFIG = {
  judgment: {
    module: "bb_rsi",
    params: {
      interval: "60",
      bb_period: 20,
      bb_std: 2,
      rsi_period: 14,
      rsi_oversold: 30,
      rsi_overbought: 70,
    },
  },
  action: {
    module: "market_order",
    params: { size_pct: 1 },
  },
  defense: {
    module: "fixed_pct",
    params: { stop_loss_pct: 5, take_profit_pct: 8 },
  },
  filters: [] as unknown[],
  sizing: null as unknown,
  leverage: 3,
  cooldown_bars: 12,
} as const;

export const DEFAULT_STRATEGY_JSON = JSON.stringify(DEFAULT_STRATEGY_CONFIG, null, 2);

// Reference catalog of available modules (the "triggers"). Kept in sync with
// the engine registries so users editing JSON know the valid module names.
export const MODULE_CATALOG: {
  category: string;
  key: "judgment" | "defense" | "filters" | "sizing" | "action";
  modules: { name: string; desc: string }[];
}[] = [
  {
    category: "진입 트리거 (judgment)",
    key: "judgment",
    modules: [
      { name: "bb_rsi", desc: "볼린저밴드 + RSI 반전" },
      { name: "bb_squeeze", desc: "밴드 스퀴즈 돌파" },
      { name: "ema_cross", desc: "EMA 골든/데드 크로스" },
      { name: "macd_cross", desc: "MACD 시그널 교차" },
      { name: "rsi_divergence", desc: "RSI 다이버전스" },
      { name: "bnf_dip_buy", desc: "급락 저점 매수" },
    ],
  },
  {
    category: "방어 (defense)",
    key: "defense",
    modules: [
      { name: "fixed_pct", desc: "고정 % 손절/익절" },
      { name: "atr_stop", desc: "ATR 기반 손절/익절" },
      { name: "trailing_atr", desc: "ATR 트레일링 스탑" },
      { name: "time_stop", desc: "시간 기반 청산" },
    ],
  },
  {
    category: "필터 (filters)",
    key: "filters",
    modules: [
      { name: "trend_filter", desc: "상위 추세 필터" },
      { name: "regime_filter", desc: "장세(추세/횡보) 판별" },
      { name: "volatility_filter", desc: "변동성 필터" },
    ],
  },
  {
    category: "사이징 (sizing)",
    key: "sizing",
    modules: [
      { name: "fixed_fraction", desc: "고정 비율" },
      { name: "risk_based", desc: "리스크 기반" },
      { name: "volatility_adjusted", desc: "변동성 조정" },
    ],
  },
  {
    category: "실행 (action)",
    key: "action",
    modules: [{ name: "market_order", desc: "시장가 주문" }],
  },
];

export interface StrategyValidation {
  valid: boolean;
  error: string | null;
  parsed: Record<string, unknown> | null;
}

// Validate a strategy_config JSON string. Requires the three mandatory modules
// (judgment/action/defense) so the engine can build the bot.
export function validateStrategyJson(text: string): StrategyValidation {
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch (e) {
    return { valid: false, error: `JSON 문법 오류: ${e instanceof Error ? e.message : String(e)}`, parsed: null };
  }
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    return { valid: false, error: "최상위는 객체(object)여야 합니다.", parsed: null };
  }
  const obj = parsed as Record<string, unknown>;
  for (const key of ["judgment", "action", "defense"] as const) {
    const mod = obj[key];
    if (typeof mod !== "object" || mod === null || Array.isArray(mod)) {
      return { valid: false, error: `필수 항목 "${key}" 가 없거나 객체가 아닙니다.`, parsed: null };
    }
    if (typeof (mod as Record<string, unknown>).module !== "string") {
      return { valid: false, error: `"${key}.module" (문자열)이 필요합니다.`, parsed: null };
    }
  }
  return { valid: true, error: null, parsed: obj };
}
