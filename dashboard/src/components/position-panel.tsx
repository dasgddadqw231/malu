"use client";

import { useEffect, useState, useCallback } from "react";
import { api, Position } from "@/lib/api";

const DEMO_POSITIONS: Position[] = [
  {
    symbol: "BTCUSDT",
    side: "Buy",
    size: "0.15",
    entry_price: "84230.50",
    unrealised_pnl: "342.18",
    leverage: "10",
    liq_price: "76420.00",
    take_profit: "88500.00",
    stop_loss: "82100.00",
    source: "bot",
    bot: { bot_id: "demo-1", name: "ALPHA-1", status: "in_position" },
  },
  {
    symbol: "ETHUSDT",
    side: "Sell",
    size: "2.5",
    entry_price: "1612.40",
    unrealised_pnl: "-28.75",
    leverage: "5",
    liq_price: "1890.00",
    take_profit: "1480.00",
    stop_loss: "1660.00",
    source: "bot",
    bot: { bot_id: "demo-2", name: "BETA-ETH", status: "defending" },
  },
  {
    symbol: "SOLUSDT",
    side: "Buy",
    size: "120",
    entry_price: "132.85",
    unrealised_pnl: "186.40",
    leverage: "3",
    liq_price: "89.20",
    take_profit: "155.00",
    stop_loss: "125.00",
    source: "manual",
    bot: null,
  },
  {
    symbol: "DOGEUSDT",
    side: "Buy",
    size: "50000",
    entry_price: "0.1542",
    unrealised_pnl: "-12.50",
    leverage: "2",
    liq_price: "0.0810",
    take_profit: "0",
    stop_loss: "0",
    source: "manual",
    bot: null,
  },
];

export function PositionPanel() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchPositions = useCallback(async () => {
    try {
      const data = await api.getPositions();
      setPositions(data.length > 0 ? data : DEMO_POSITIONS);
    } catch {
      setPositions(DEMO_POSITIONS);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPositions();
    const interval = setInterval(fetchPositions, 5000);
    return () => clearInterval(interval);
  }, [fetchPositions]);

  if (loading) {
    return (
      <div className="jarvis-card jarvis-corners rounded-lg p-6 text-center">
        <p className="text-xs font-mono text-jarvis/40 tracking-wider">LOADING POSITIONS...</p>
      </div>
    );
  }

  if (positions.length === 0) {
    return (
      <div className="jarvis-card jarvis-corners rounded-lg p-6 text-center">
        <p className="text-muted-foreground text-sm font-mono">No open positions</p>
        <p className="text-xs text-muted-foreground/60 font-mono mt-1">
          Positions will appear here when bots or manual trades are active
        </p>
      </div>
    );
  }

  const totalUnrealised = positions.reduce(
    (sum, p) => sum + Number(p.unrealised_pnl),
    0
  );

  return (
    <div className="space-y-3">
      {/* Summary bar */}
      <div className="flex items-center justify-between px-1">
        <span className="text-xs font-mono text-jarvis/60 tracking-wider">
          {positions.length} OPEN POSITION{positions.length !== 1 ? "S" : ""}
        </span>
        <span
          className={`text-xs font-mono font-bold ${
            totalUnrealised >= 0 ? "text-emerald-400" : "text-red-400"
          }`}
        >
          UNREALISED: {totalUnrealised >= 0 ? "+" : ""}
          ${Math.abs(totalUnrealised).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}
        </span>
      </div>

      {/* Position cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {positions.map((pos) => (
          <PositionCard key={`${pos.symbol}-${pos.side}`} position={pos} />
        ))}
      </div>
    </div>
  );
}

function formatPrice(value: number): string {
  if (value >= 1) {
    return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
  return `$${value.toLocaleString(undefined, { minimumFractionDigits: 4, maximumFractionDigits: 4 })}`;
}

function PositionCard({ position }: { position: Position }) {
  const pnl = Number(position.unrealised_pnl);
  const isLong = position.side === "Buy";
  const entryPrice = Number(position.entry_price);
  const liqPrice = Number(position.liq_price);
  const tp = Number(position.take_profit);
  const sl = Number(position.stop_loss);
  const liqDistance =
    liqPrice > 0 && entryPrice > 0
      ? Math.abs(((entryPrice - liqPrice) / entryPrice) * 100)
      : null;

  return (
    <div
      className={`jarvis-card jarvis-corners rounded-lg p-4 border ${
        pnl >= 0
          ? "border-emerald-500/20"
          : "border-red-500/20"
      }`}
    >
      {/* Header: symbol + side */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-mono font-bold text-foreground">
            {position.symbol}
          </span>
          <span
            className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${
              isLong
                ? "bg-emerald-500/15 text-emerald-400"
                : "bg-red-500/15 text-red-400"
            }`}
          >
            {isLong ? "LONG" : "SHORT"}
          </span>
          <span className="text-[10px] font-mono text-jarvis/50 px-1.5 py-0.5 rounded bg-jarvis/5">
            {position.leverage}x
          </span>
        </div>
        <span
          className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
            position.source === "bot"
              ? "bg-jarvis/10 text-jarvis/70"
              : "bg-purple-400/10 text-purple-400/70"
          }`}
        >
          {position.source === "bot" ? position.bot?.name ?? "BOT" : "MANUAL"}
        </span>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-3 gap-y-2 gap-x-3 text-xs font-mono">
        <div>
          <p className="text-muted-foreground/60 mb-0.5">SIZE</p>
          <p className="text-foreground">{Number(position.size).toLocaleString()}</p>
        </div>
        <div>
          <p className="text-muted-foreground/60 mb-0.5">ENTRY</p>
          <p className="text-foreground">{formatPrice(entryPrice)}</p>
        </div>
        <div>
          <p className="text-muted-foreground/60 mb-0.5">UNREAL. PNL</p>
          <p
            className={`font-bold ${
              pnl >= 0 ? "text-emerald-400" : "text-red-400"
            }`}
          >
            {pnl >= 0 ? "+" : ""}$
            {Math.abs(pnl).toLocaleString(undefined, {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </p>
        </div>
        <div>
          <p className="text-emerald-400/60 mb-0.5">TP</p>
          {tp > 0 ? (
            <p className="text-emerald-400">{formatPrice(tp)}</p>
          ) : (
            <p className="text-muted-foreground/40">-</p>
          )}
        </div>
        <div>
          <p className="text-red-400/60 mb-0.5">SL</p>
          {sl > 0 ? (
            <p className="text-red-400">{formatPrice(sl)}</p>
          ) : (
            <p className="text-muted-foreground/40">-</p>
          )}
        </div>
        <div>
          <p className="text-muted-foreground/60 mb-0.5">LIQ.</p>
          {liqPrice > 0 ? (
            <p className={`${liqDistance && liqDistance < 5 ? "text-red-400" : "text-foreground"}`}>
              {formatPrice(liqPrice)}
              {liqDistance !== null && (
                <span className="text-muted-foreground/50 ml-1">
                  ({liqDistance.toFixed(1)}%)
                </span>
              )}
            </p>
          ) : (
            <p className="text-muted-foreground/40">-</p>
          )}
        </div>
      </div>
    </div>
  );
}
