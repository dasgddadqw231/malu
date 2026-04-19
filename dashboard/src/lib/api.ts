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

// DIY Types
export interface DiyTrade {
  id: string;
  bybit_order_id: string;
  symbol: string;
  side: string;
  order_type: string;
  qty: string;
  avg_price: string | null;
  pnl: string | null;
  fee: string | null;
  leverage: string;
  trade_pair_id: string | null;
  pair_role: string | null;
  rationale: string | null;
  tags: string[];
  filled_at: string | null;
  created_at: string;
}

export interface SignatureMessage {
  role: "user" | "assistant";
  content: string;
}

export interface Signature {
  id: string;
  name: string;
  description: string | null;
  source_trade_ids: string[];
  strategy_config: Record<string, unknown>;
  rules: Record<string, unknown>[];
  stats: Record<string, unknown>;
  is_active: boolean;
  dataset_id: string | null;
  messages: SignatureMessage[];
  created_at: string;
  updated_at: string;
}

export interface SignatureChatResponse {
  id: string;
  reply: string;
  strategy_config: Record<string, unknown>;
  rules: Record<string, unknown>[];
  messages: SignatureMessage[];
}

// Dataset Types
export interface ManualDataset {
  id: string;
  name: string;
  description: string | null;
  trade_ids: string[];
  auto_sync: boolean;
  sync_symbol: string | null;
  sync_category: string;
  created_at: string;
  updated_at: string;
}

export interface ManualDatasetWithTrades extends ManualDataset {
  trades: DiyTrade[];
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

  // DIY Trading / Signatures
  syncDiyTrades: (symbol?: string, category?: string) => {
    const params = new URLSearchParams();
    if (symbol) params.set("symbol", symbol);
    if (category) params.set("category", category);
    return request<{ synced: number }>(`/diy/sync?${params}`, { method: "POST" });
  },

  listDiyTrades: (symbol?: string) => {
    const params = symbol ? `?symbol=${symbol}` : "";
    return request<DiyTrade[]>(`/diy/trades${params}`);
  },

  updateDiyTrade: (id: string, data: { rationale?: string; tags?: string[] }) =>
    request<DiyTrade>(`/diy/trades/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  pairDiyTrades: (entryId: string, exitId: string) =>
    request<{ pair_id: string }>(`/diy/trades/pair?entry_id=${entryId}&exit_id=${exitId}`, {
      method: "POST",
    }),

  listSignatures: () => request<Signature[]>("/diy/signatures"),

  getSignature: (id: string) => request<Signature>(`/diy/signatures/${id}`),

  createSignature: (data: { name: string; description?: string; source_trade_ids: string[]; strategy_config: Record<string, unknown>; rules: Record<string, unknown>[]; stats: Record<string, unknown> }) =>
    request<Signature>("/diy/signatures", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateSignature: (id: string, data: { name?: string; description?: string; strategy_config?: Record<string, unknown>; rules?: Record<string, unknown>[] }) =>
    request<Signature>(`/diy/signatures/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  deleteSignature: (id: string) =>
    request<{ deleted: boolean }>(`/diy/signatures/${id}`, { method: "DELETE" }),

  createSignatureFromPrompt: (name: string, prompt: string, description?: string, sourceTradeIds?: string[]) => {
    const params = new URLSearchParams({ name, prompt });
    if (description) params.set("description", description);
    if (sourceTradeIds?.length) {
      for (const id of sourceTradeIds) params.append("source_trade_ids", id);
    }
    return request<Signature>(`/diy/signatures/from-prompt?${params}`, {
      method: "POST",
    });
  },

  generateSignature: (name: string, tradeIds: string[], description?: string) => {
    const params = new URLSearchParams({ name });
    if (description) params.set("description", description);
    return request<Signature>(`/diy/generate?${params}`, {
      method: "POST",
      body: JSON.stringify(tradeIds),
    });
  },

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

  runBacktestFromSignature: (
    sigId: string,
    params: { symbol: string; start_date: string; end_date: string; initial_capital?: number }
  ) => {
    const qs = new URLSearchParams({
      symbol: params.symbol,
      start_date: params.start_date,
      end_date: params.end_date,
    });
    if (params.initial_capital) qs.set("initial_capital", String(params.initial_capital));
    return request<{ run_id: string; status: string }>(
      `/backtest/from-signature/${sigId}?${qs}`,
      { method: "POST" }
    );
  },

  getBacktest: (runId: string) => request<BacktestRun>(`/backtest/${runId}`),

  listBacktests: () => request<BacktestRun[]>("/backtest"),

  getBacktestTrades: (runId: string) => request<BacktestTrade[]>(`/backtest/${runId}/trades`),

  deleteBacktest: (runId: string) =>
    request<{ status: string }>(`/backtest/${runId}`, { method: "DELETE" }),

  // Datasets
  listDatasets: () => request<ManualDataset[]>("/diy/datasets"),

  getDataset: (id: string) => request<ManualDatasetWithTrades>(`/diy/datasets/${id}`),

  createDataset: (data: { name: string; description?: string; trade_ids?: string[]; auto_sync?: boolean; sync_symbol?: string; sync_category?: string }) =>
    request<ManualDataset>("/diy/datasets", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateDataset: (id: string, data: { name?: string; description?: string; auto_sync?: boolean; sync_symbol?: string; add_trade_ids?: string[]; remove_trade_ids?: string[] }) =>
    request<ManualDataset>(`/diy/datasets/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  deleteDataset: (id: string) =>
    request<{ deleted: boolean }>(`/diy/datasets/${id}`, { method: "DELETE" }),

  syncDataset: (id: string) =>
    request<{ synced: number; added_to_dataset: number }>(`/diy/datasets/${id}/sync`, { method: "POST" }),

  // Signature Chat
  startSignatureChat: (name: string, message: string, datasetId?: string) => {
    const body: Record<string, unknown> = { name, message };
    if (datasetId) body.dataset_id = datasetId;
    return request<SignatureChatResponse>("/diy/signatures/chat/new", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  chatWithSignature: (sigId: string, message: string) =>
    request<SignatureChatResponse>(`/diy/signatures/${sigId}/chat`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),

  uploadDatasetCsv: async (id: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/diy/datasets/${id}/upload`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(error.detail || `API error: ${res.status}`);
    }
    return res.json() as Promise<{ uploaded: number; added_to_dataset: number }>;
  },
};
