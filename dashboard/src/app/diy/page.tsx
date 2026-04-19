"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, type Signature } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeftIcon,
  RefreshCwIcon,
  PencilIcon,
  PlayIcon,
  XIcon,
  PlusIcon,
  TrendingUpIcon,
  TrendingDownIcon,
  ShieldIcon,
  TargetIcon,
  TimerIcon,
  PercentIcon,
} from "lucide-react";
import { BootSound } from "@/components/click-effects";

function RuleIcon({ type }: { type: string }) {
  switch (type) {
    case "entry":
      return <TrendingUpIcon className="size-3 mt-0.5 text-emerald-400 shrink-0" />;
    case "exit":
    case "stop_loss":
      return <ShieldIcon className="size-3 mt-0.5 text-red-400 shrink-0" />;
    case "take_profit":
      return <TargetIcon className="size-3 mt-0.5 text-emerald-400 shrink-0" />;
    case "position_size":
      return <PercentIcon className="size-3 mt-0.5 text-blue-400 shrink-0" />;
    case "cycle_interval":
      return <TimerIcon className="size-3 mt-0.5 text-yellow-400 shrink-0" />;
    default:
      return <TrendingDownIcon className="size-3 mt-0.5 text-jarvis/30 shrink-0" />;
  }
}

export default function DiyPage() {
  const router = useRouter();
  const [signatures, setSignatures] = useState<Signature[]>([]);
  const [loading, setLoading] = useState(true);

  // Backtest state
  const [backtestSigId, setBacktestSigId] = useState<string | null>(null);
  const [btSymbol, setBtSymbol] = useState("BTCUSDT");
  const [btStart, setBtStart] = useState("2025-01-01");
  const [btEnd, setBtEnd] = useState("2025-03-01");
  const [btCapital, setBtCapital] = useState(10000);
  const [btRunning, setBtRunning] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const s = await api.listSignatures();
      setSignatures(s);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleDelete = async (id: string) => {
    try {
      await api.deleteSignature(id);
      await loadData();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Delete failed");
    }
  };

  const handleRunBacktest = async (sigId: string) => {
    setBtRunning(true);
    try {
      const result = await api.runBacktestFromSignature(sigId, {
        symbol: btSymbol,
        start_date: btStart,
        end_date: btEnd,
        initial_capital: btCapital,
      });
      router.push(`/backtest?id=${result.run_id}`);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Backtest failed");
      setBtRunning(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <BootSound />
        <div className="arc-spinner" />
        <p className="text-sm font-mono text-jarvis/60 tracking-widest uppercase">Loading Signatures...</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-6">
      {/* Header */}
      <header className="flex items-end justify-between mb-8 jarvis-boot jarvis-boot-1">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Link href="/" className="text-jarvis/50 hover:text-jarvis transition-colors jarvis-nav-link">
              <ArrowLeftIcon className="size-5" />
            </Link>
            <h1 className="text-3xl font-bold tracking-[0.2em] font-mono text-jarvis text-glow jarvis-text-reveal">
              SIGNATURE
            </h1>
            <div className="h-[1px] w-16 bg-gradient-to-r from-jarvis/60 to-transparent jarvis-divider" />
          </div>
          <p className="text-xs font-mono text-muted-foreground tracking-[0.15em] uppercase">
            Your saved trading strategies
          </p>
        </div>
        <Link href="/diy/new">
          <Button className="bg-purple-400/20 text-purple-400 border border-purple-400/40 hover:bg-purple-400/30 font-mono text-xs tracking-wider">
            <PlusIcon className="size-3 mr-1.5" />
            NEW SIGNATURE
          </Button>
        </Link>
      </header>

      {/* Signature List */}
      {signatures.length === 0 ? (
        <div className="jarvis-card rounded-lg text-center py-16">
          <p className="text-muted-foreground text-sm font-mono mb-2">No signatures yet</p>
          <p className="text-xs text-muted-foreground/80 font-mono mb-6">
            전략을 설명하고 첫 시그니처를 만들어보세요
          </p>
          <Link href="/diy/new">
            <Button variant="outline" className="font-mono text-xs border-purple-400/30 text-purple-400/70 hover:bg-purple-400/10">
              <PlusIcon className="size-3 mr-1.5" />
              CREATE FIRST SIGNATURE
            </Button>
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 jarvis-boot jarvis-boot-2">
          {signatures.map((sig) => {
            const stats = sig.stats as Record<string, number>;
            const config = sig.strategy_config as Record<string, Record<string, unknown>>;
            const defense = config?.defense as { params?: { max_loss_pct?: number; take_profit_pct?: number } } | undefined;
            const isBacktesting = backtestSigId === sig.id;
            const refCount = sig.source_trade_ids?.length ?? 0;

            return (
              <div
                key={sig.id}
                className="jarvis-card jarvis-corners rounded-lg p-5 border border-jarvis/15 space-y-4"
              >
                {/* Header */}
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-mono text-sm font-semibold text-jarvis tracking-wider">
                      {sig.name}
                    </h3>
                    {sig.description && (
                      <p className="text-xs font-mono text-muted-foreground mt-0.5 line-clamp-1">
                        {sig.description}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {refCount > 0 && (
                      <Badge variant="outline" className="text-xs font-mono border-jarvis/20 text-jarvis/50">
                        {refCount} refs
                      </Badge>
                    )}
                    <Badge
                      variant="outline"
                      className={`text-xs font-mono ${
                        (sig.stats as Record<string, unknown>).source === "natural_language"
                          ? "border-purple-400/30 text-purple-400/70"
                          : "border-jarvis/20 text-jarvis/70"
                      }`}
                    >
                      {(sig.stats as Record<string, unknown>).source === "natural_language" ? "NL" : "TRADE"}
                    </Badge>
                  </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-4 gap-3">
                  <StatBlock label="TRADES" value={String(stats.total_trades ?? 0)} />
                  <StatBlock label="WIN RATE" value={`${stats.win_rate ?? 0}%`} accent={(stats.win_rate ?? 0) >= 50 ? "text-emerald-400" : "text-red-400"} />
                  <StatBlock label="AVG PNL" value={String(stats.avg_pnl ?? 0)} accent={(stats.avg_pnl ?? 0) >= 0 ? "text-emerald-400" : "text-red-400"} />
                  <StatBlock label="TOTAL PNL" value={String(stats.total_pnl ?? 0)} accent={(stats.total_pnl ?? 0) >= 0 ? "text-emerald-400" : "text-red-400"} />
                </div>

                {/* Config summary */}
                <div className="flex gap-4 text-xs font-mono text-muted-foreground">
                  {defense?.params?.max_loss_pct != null && <span>SL: {defense.params.max_loss_pct}%</span>}
                  {defense?.params?.take_profit_pct != null && <span>TP: {defense.params.take_profit_pct}%</span>}
                  {config?.cycle_interval != null && <span>Cycle: {String(config.cycle_interval)}s</span>}
                </div>

                {/* Rules */}
                {sig.rules.length > 0 && (
                  <div className="space-y-1.5">
                    <p className="text-xs font-mono text-jarvis/40 tracking-wider uppercase">전략 룰</p>
                    {sig.rules.map((rule, i) => {
                      const r = rule as { type?: string; situation?: string; action?: string; description?: string };
                      return (
                        <div key={i} className="text-xs font-mono text-muted-foreground flex items-start gap-1.5">
                          <RuleIcon type={r.type || "default"} />
                          {r.situation && r.action ? (
                            <span>
                              <span className="text-muted-foreground/90">{r.situation}</span>
                              <span className="text-jarvis/40 mx-1">&rarr;</span>
                              <span className="text-foreground/80">{r.action}</span>
                            </span>
                          ) : (
                            <span>{r.description || r.type}</span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Backtest Form */}
                {isBacktesting && (
                  <div className="space-y-3 p-3 rounded border border-blue-400/20 bg-blue-400/5">
                    <div className="flex items-center gap-2 mb-1">
                      <PlayIcon className="size-3 text-blue-400" />
                      <span className="text-xs font-mono text-blue-400 tracking-wider font-semibold">BACKTEST</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-xs font-mono text-muted-foreground">Symbol</label>
                        <Input value={btSymbol} onChange={(e) => setBtSymbol(e.target.value)} className="font-mono text-xs h-8" />
                      </div>
                      <div>
                        <label className="text-xs font-mono text-muted-foreground">Capital</label>
                        <Input type="number" value={btCapital} onChange={(e) => setBtCapital(Number(e.target.value))} className="font-mono text-xs h-8" />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-xs font-mono text-muted-foreground">Start</label>
                        <Input type="date" value={btStart} onChange={(e) => setBtStart(e.target.value)} className="font-mono text-xs h-8" />
                      </div>
                      <div>
                        <label className="text-xs font-mono text-muted-foreground">End</label>
                        <Input type="date" value={btEnd} onChange={(e) => setBtEnd(e.target.value)} className="font-mono text-xs h-8" />
                      </div>
                    </div>
                    <div className="flex gap-2 justify-end">
                      <Button variant="ghost" size="sm" onClick={() => setBacktestSigId(null)} className="font-mono text-xs">
                        <XIcon className="size-3 mr-1" /> CANCEL
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => handleRunBacktest(sig.id)}
                        disabled={btRunning}
                        className="bg-blue-400/20 text-blue-400 border border-blue-400/40 hover:bg-blue-400/30 font-mono text-xs"
                      >
                        {btRunning ? (
                          <span className="flex items-center gap-1"><RefreshCwIcon className="size-3 animate-spin" /> RUNNING...</span>
                        ) : (
                          <span className="flex items-center gap-1"><PlayIcon className="size-3" /> RUN</span>
                        )}
                      </Button>
                    </div>
                  </div>
                )}

                {/* Action buttons */}
                <div className="flex justify-between items-center pt-2 border-t border-jarvis/10">
                  <div className="flex gap-3">
                    <button
                      onClick={() => router.push(`/diy/${sig.id}/edit`)}
                      className="text-xs font-mono text-jarvis/50 hover:text-jarvis transition-colors tracking-wider flex items-center gap-1"
                    >
                      <PencilIcon className="size-3" /> EDIT
                    </button>
                    <button
                      onClick={() => setBacktestSigId(isBacktesting ? null : sig.id)}
                      className="text-xs font-mono text-blue-400/50 hover:text-blue-400 transition-colors tracking-wider flex items-center gap-1"
                    >
                      <PlayIcon className="size-3" /> BACKTEST
                    </button>
                  </div>
                  <button
                    onClick={() => handleDelete(sig.id)}
                    className="text-xs font-mono text-red-400/50 hover:text-red-400 transition-colors tracking-wider"
                  >
                    DELETE
                  </button>
                </div>
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
