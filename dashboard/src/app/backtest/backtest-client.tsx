"use client";

import { Suspense, useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { api, type BacktestRun, type BacktestTrade } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeftIcon,
  RefreshCwIcon,
  Trash2Icon,
  ChevronDownIcon,
  ChevronUpIcon,
} from "lucide-react";
import { BootSound } from "@/components/click-effects";

export default function BacktestPageClient() {
  return (
    <Suspense
      fallback={
        <div className="flex flex-col items-center justify-center min-h-screen gap-4">
          <BootSound />
          <div className="arc-spinner" />
          <p className="text-sm font-mono text-jarvis/60 tracking-widest uppercase">
            Loading Backtest Results...
          </p>
        </div>
      }
    >
      <BacktestContent />
    </Suspense>
  );
}

function BacktestContent() {
  const searchParams = useSearchParams();
  const focusId = searchParams.get("id");

  const [runs, setRuns] = useState<BacktestRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(focusId);
  const [trades, setTrades] = useState<Record<string, BacktestTrade[]>>({});
  const [polling, setPolling] = useState<string | null>(focusId);

  const loadRuns = useCallback(async () => {
    try {
      const data = await api.listBacktests();
      setRuns(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  // Poll running backtest
  useEffect(() => {
    if (!polling) return;
    const interval = setInterval(async () => {
      try {
        const run = await api.getBacktest(polling);
        setRuns((prev) => prev.map((r) => (r.id === run.id ? run : r)));
        if (run.status !== "running") {
          setPolling(null);
          clearInterval(interval);
        }
      } catch {
        setPolling(null);
        clearInterval(interval);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [polling]);

  const loadTrades = async (runId: string) => {
    if (trades[runId]) return;
    try {
      const data = await api.getBacktestTrades(runId);
      setTrades((prev) => ({ ...prev, [runId]: data }));
    } catch {
      // ignore
    }
  };

  const toggleExpand = (runId: string) => {
    if (expandedId === runId) {
      setExpandedId(null);
    } else {
      setExpandedId(runId);
      loadTrades(runId);
    }
  };

  const handleDelete = async (runId: string) => {
    try {
      await api.deleteBacktest(runId);
      setRuns((prev) => prev.filter((r) => r.id !== runId));
      if (expandedId === runId) setExpandedId(null);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Delete failed");
    }
  };

  // Auto-expand focused run on load
  useEffect(() => {
    if (focusId && runs.length > 0) {
      const run = runs.find((r) => r.id === focusId);
      if (run) {
        setExpandedId(focusId);
        if (run.status === "running") setPolling(focusId);
        else loadTrades(focusId);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusId, runs.length]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <BootSound />
        <div className="arc-spinner" />
        <p className="text-sm font-mono text-jarvis/60 tracking-widest uppercase">
          Loading Backtest Results...
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-6">
      {/* Header */}
      <header className="flex items-end justify-between mb-8">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Link href="/" className="text-jarvis/50 hover:text-jarvis transition-colors">
              <ArrowLeftIcon className="size-5" />
            </Link>
            <h1 className="text-3xl font-bold tracking-[0.2em] font-mono text-jarvis text-glow">
              BACKTEST
            </h1>
            <div className="h-[1px] w-16 bg-gradient-to-r from-jarvis/60 to-transparent" />
          </div>
          <p className="text-xs font-mono text-muted-foreground tracking-[0.15em] uppercase">
            Strategy simulation results
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={loadRuns}
          className="font-mono text-xs text-jarvis/60"
        >
          <RefreshCwIcon className="size-3 mr-1" />
          REFRESH
        </Button>
      </header>

      {runs.length === 0 ? (
        <div className="jarvis-card rounded-lg text-center py-12">
          <p className="text-muted-foreground text-sm font-mono mb-2">No backtest runs yet</p>
          <p className="text-xs text-muted-foreground/80 font-mono">
            시그니처에서 BACKTEST 버튼을 눌러 실행해보세요
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {runs.map((run) => {
            const isExpanded = expandedId === run.id;
            const isRunning = run.status === "running";
            const netPnl = parseFloat(run.net_pnl || "0");
            const runTrades = trades[run.id] || [];

            return (
              <div
                key={run.id}
                className={`jarvis-card jarvis-corners rounded-lg border ${
                  isRunning
                    ? "border-yellow-400/30"
                    : netPnl >= 0
                    ? "border-emerald-400/15"
                    : "border-red-400/15"
                } transition-all`}
              >
                {/* Run Summary */}
                <button
                  onClick={() => toggleExpand(run.id)}
                  className="w-full p-5 text-left"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-sm font-semibold text-jarvis tracking-wider">
                        {run.symbol}
                      </span>
                      <Badge
                        variant="outline"
                        className={`text-xs font-mono ${
                          isRunning
                            ? "border-yellow-400/30 text-yellow-400"
                            : run.status === "completed"
                            ? "border-emerald-400/20 text-emerald-400/70"
                            : "border-red-400/20 text-red-400/70"
                        }`}
                      >
                        {isRunning && <RefreshCwIcon className="size-3 mr-1 animate-spin" />}
                        {run.status.toUpperCase()}
                      </Badge>
                      <span className="text-xs font-mono text-muted-foreground">
                        {run.interval}m &middot; {run.start_date} ~ {run.end_date}
                      </span>
                    </div>
                    {isExpanded ? (
                      <ChevronUpIcon className="size-4 text-jarvis/40" />
                    ) : (
                      <ChevronDownIcon className="size-4 text-jarvis/40" />
                    )}
                  </div>

                  {run.status === "completed" && (
                    <div className="grid grid-cols-6 gap-4">
                      <StatBlock
                        label="NET PNL"
                        value={`$${netPnl.toFixed(2)}`}
                        accent={netPnl >= 0 ? "text-emerald-400" : "text-red-400"}
                      />
                      <StatBlock
                        label="TOTAL PNL"
                        value={`$${parseFloat(run.total_pnl || "0").toFixed(2)}`}
                      />
                      <StatBlock
                        label="FEES"
                        value={`$${parseFloat(run.total_fees || "0").toFixed(2)}`}
                      />
                      <StatBlock
                        label="WIN RATE"
                        value={`${(run.win_rate ?? 0).toFixed(1)}%`}
                        accent={(run.win_rate ?? 0) >= 50 ? "text-emerald-400" : "text-red-400"}
                      />
                      <StatBlock
                        label="DRAWDOWN"
                        value={`${((run.max_drawdown ?? 0) * 100).toFixed(1)}%`}
                        accent="text-red-400"
                      />
                      <StatBlock
                        label="SHARPE"
                        value={(run.sharpe_ratio ?? 0).toFixed(2)}
                        accent={(run.sharpe_ratio ?? 0) >= 1 ? "text-emerald-400" : "text-muted-foreground"}
                      />
                    </div>
                  )}

                  {run.status === "error" && run.error_message && (
                    <p className="text-xs font-mono text-red-400/80 mt-1">{run.error_message}</p>
                  )}
                </button>

                {/* Expanded: Equity Curve + Trades */}
                {isExpanded && run.status === "completed" && (
                  <div className="px-5 pb-5 space-y-4 border-t border-jarvis/10 pt-4">
                    {/* Mini equity curve (text-based) */}
                    {run.equity_curve && run.equity_curve.length > 0 && (
                      <div>
                        <p className="text-xs font-mono text-jarvis/40 tracking-wider uppercase mb-2">
                          EQUITY CURVE
                        </p>
                        <div className="flex items-end gap-px h-16">
                          {sampleEquityCurve(run.equity_curve, 60).map((point, i) => {
                            const min = Math.min(...run.equity_curve!.map((p) => p.equity));
                            const max = Math.max(...run.equity_curve!.map((p) => p.equity));
                            const range = max - min || 1;
                            const height = ((point.equity - min) / range) * 100;
                            const color =
                              point.equity >= parseFloat(run.initial_capital)
                                ? "bg-emerald-400/60"
                                : "bg-red-400/60";
                            return (
                              <div
                                key={i}
                                className={`flex-1 rounded-t ${color}`}
                                style={{ height: `${Math.max(2, height)}%` }}
                              />
                            );
                          })}
                        </div>
                        <div className="flex justify-between text-xs font-mono text-muted-foreground/60 mt-1">
                          <span>${parseFloat(run.initial_capital).toLocaleString()}</span>
                          <span>${(parseFloat(run.initial_capital) + netPnl).toLocaleString()}</span>
                        </div>
                      </div>
                    )}

                    {/* Trades table */}
                    <div>
                      <p className="text-xs font-mono text-jarvis/40 tracking-wider uppercase mb-2">
                        TRADES ({run.total_trades ?? runTrades.length})
                      </p>
                      {runTrades.length > 0 ? (
                        <div className="overflow-x-auto">
                          <table className="w-full text-xs font-mono">
                            <thead>
                              <tr className="text-muted-foreground/60 border-b border-jarvis/10">
                                <th className="text-left py-1.5 pr-3">SIDE</th>
                                <th className="text-right py-1.5 pr-3">ENTRY</th>
                                <th className="text-right py-1.5 pr-3">EXIT</th>
                                <th className="text-right py-1.5 pr-3">QTY</th>
                                <th className="text-right py-1.5 pr-3">PNL</th>
                                <th className="text-right py-1.5 pr-3">FEE</th>
                                <th className="text-left py-1.5">EXIT REASON</th>
                              </tr>
                            </thead>
                            <tbody>
                              {runTrades.map((t) => {
                                const pnl = parseFloat(t.pnl);
                                return (
                                  <tr key={t.id} className="border-b border-jarvis/5">
                                    <td className={`py-1.5 pr-3 ${t.side === "Buy" ? "text-emerald-400" : "text-red-400"}`}>
                                      {t.side === "Buy" ? "LONG" : "SHORT"}
                                    </td>
                                    <td className="text-right py-1.5 pr-3 text-muted-foreground">${parseFloat(t.entry_price).toFixed(2)}</td>
                                    <td className="text-right py-1.5 pr-3 text-muted-foreground">${parseFloat(t.exit_price).toFixed(2)}</td>
                                    <td className="text-right py-1.5 pr-3 text-muted-foreground">{parseFloat(t.qty).toFixed(4)}</td>
                                    <td className={`text-right py-1.5 pr-3 ${pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                                      ${pnl.toFixed(2)}
                                    </td>
                                    <td className="text-right py-1.5 pr-3 text-muted-foreground/60">${parseFloat(t.fee).toFixed(2)}</td>
                                    <td className="py-1.5 text-muted-foreground/80">{t.exit_reason}</td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <p className="text-xs font-mono text-muted-foreground/60">Loading trades...</p>
                      )}
                    </div>

                    {/* Delete button */}
                    <div className="flex justify-end">
                      <button
                        onClick={() => handleDelete(run.id)}
                        className="text-xs font-mono text-red-400/50 hover:text-red-400 transition-colors tracking-wider flex items-center gap-1"
                      >
                        <Trash2Icon className="size-3" />
                        DELETE RUN
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function StatBlock({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div>
      <p className="text-xs font-mono text-muted-foreground/80 tracking-wider">{label}</p>
      <p className={`text-sm font-mono font-semibold ${accent || "text-foreground"}`}>{value}</p>
    </div>
  );
}

function sampleEquityCurve(
  curve: { timestamp: number; equity: number }[],
  maxPoints: number
): { timestamp: number; equity: number }[] {
  if (curve.length <= maxPoints) return curve;
  const step = curve.length / maxPoints;
  const sampled: { timestamp: number; equity: number }[] = [];
  for (let i = 0; i < maxPoints; i++) {
    sampled.push(curve[Math.floor(i * step)]);
  }
  return sampled;
}
