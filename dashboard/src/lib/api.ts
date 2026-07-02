const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }
  return res.json();
}

// Types
export interface BotControls {
  risk?: {
    max_daily_loss_pct?: number;
    max_consecutive_losses?: number;
    max_single_loss_pct?: number;
  };
  schedule?: {
    trading_hours?: { start: string; end: string }[];
    cooldown_seconds?: number;
    max_trades_per_day?: number;
  };
  sizing?: {
    mode?: "pct" | "fixed";
    fixed_amount_usd?: number;
    compound?: boolean;
  };
}

export interface BotStatus {
  bot_id: string;
  name: string;
  status: string;
  symbol: string;
  seed_budget: string;
  strategy_config?: Record<string, unknown>;
  bot_controls?: BotControls;
}

export interface DashboardSummary {
  bots: BotStatus[];
  budget: Record<string, { seed: string; used: string; reserved: string; available: string }>;
  available_budget: string;
  total_bots: number;
  active_bots: number;
  kill_switch_active: boolean;
  total_pnl: string;
}

export interface BotCreateRequest {
  name: string;
  bot_tag: string;
  symbol: string;
  category?: string;
  seed_budget: number;
  strategy_config?: Record<string, unknown>;
  bot_controls?: BotControls;
  cycle_interval?: number;
}

export interface TradeHistory {
  id: string;
  bot_id: string;
  order_link_id: string;
  symbol: string;
  side: string;
  order_type: string;
  qty: string;
  price: string | null;
  status: string;
  pnl: string | null;
  created_at: string;
}

// Backtest Types
export interface BacktestRun {
  id: string;
  symbol: string;
  interval: string;
  start_date: string;
  end_date: string;
  initial_capital: string;
  strategy_config: Record<string, unknown>;
  total_pnl: string | null;
  total_fees: string | null;
  total_funding: string | null;
  net_pnl: string | null;
  win_rate: number | null;
  max_drawdown: number | null;
  sharpe_ratio: number | null;
  total_trades: number | null;
  equity_curve: { timestamp: number; equity: number }[] | null;
  status: string;
  error_message: string | null;
  created_at: string;
}

export interface BacktestTrade {
  id: string;
  run_id: string;
  entry_time: string;
  exit_time: string;
  side: string;
  entry_price: string;
  exit_price: string;
  qty: string;
  pnl: string;
  fee: string;
  funding_paid: string;
  exit_reason: string;
}

// Position Types
export interface Position {
  symbol: string;
  side: string;
  size: string;
  entry_price: string;
  unrealised_pnl: string;
  leverage: string;
  liq_price: string;
  take_profit: string;
  stop_loss: string;
  source: "bot" | "manual";
  bot: { bot_id: string; name: string; status: string } | null;
}

// Risk Settings Types
export interface RiskSettings {
  id: string;
  enabled: boolean;
  max_loss_pct: number;
  max_profit_pct: number;
  max_daily_loss_usd: number;
  max_daily_trades: number;
  max_position_pct: number;
  max_leverage: number;
  notify_on_close: boolean;
  updated_at: string;
}

// API functions
export const api = {
  getDashboard: () => request<DashboardSummary>("/dashboard/summary"),

  listBots: () => request<BotStatus[]>("/bots"),

  getBot: (id: string) => request<BotStatus & { strategy_config: Record<string, unknown>; bot_controls?: BotControls }>(`/bots/${id}`),

  createBot: (data: BotCreateRequest) =>
    request<{ bot_id: string; name: string; status: string }>("/bots", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateBot: (id: string, data: { name?: string; seed_budget?: number; strategy_config?: Record<string, unknown>; bot_controls?: BotControls; cycle_interval?: number }) =>
    request<{ bot_id: string; name: string }>(`/bots/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  startBot: (id: string) =>
    request<{ status: string }>(`/bots/${id}/start`, { method: "POST" }),

  stopBot: (id: string) =>
    request<{ status: string }>(`/bots/${id}/stop`, { method: "POST" }),

  killBot: (id: string) =>
    request<{ status: string }>(`/bots/${id}/kill`, { method: "POST" }),

  deleteBot: (id: string) =>
    request<{ deleted: boolean }>(`/bots/${id}`, { method: "DELETE" }),

  getBotTrades: (id: string) => request<TradeHistory[]>(`/bots/${id}/trades`),

  getAllBotTrades: (limit = 200) => request<TradeHistory[]>(`/dashboard/trades?limit=${limit}`),

  getPositions: () => request<Position[]>("/dashboard/positions"),

  killAll: () =>
    request<{ bots_stopped: string[]; errors: string[] }>("/dashboard/kill-all", {
      method: "POST",
    }),

  resetKillSwitch: () =>
    request<{ kill_switch_active: boolean }>("/dashboard/kill-switch/reset", {
      method: "POST",
    }),

  // Backtest
  runBacktest: (data: {
    symbol: string;
    interval?: string;
    start_date: string;
    end_date: string;
    initial_capital?: number;
    strategy_config: Record<string, unknown>;
  }) =>
    request<{ run_id: string; status: string }>("/backtest", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getBacktest: (runId: string) => request<BacktestRun>(`/backtest/${runId}`),

  listBacktests: () => request<BacktestRun[]>("/backtest"),

  getBacktestTrades: (runId: string) => request<BacktestTrade[]>(`/backtest/${runId}/trades`),

  deleteBacktest: (runId: string) =>
    request<{ status: string }>(`/backtest/${runId}`, { method: "DELETE" }),

  // Risk Settings
  getRiskSettings: () => request<RiskSettings>("/risk/settings"),

  updateRiskSettings: (data: Partial<RiskSettings>) =>
    request<RiskSettings>("/risk/settings", {
      method: "PUT",
      body: JSON.stringify(data),
    }),
};
