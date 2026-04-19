"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { api, type TradeHistory, type BotStatus } from "@/lib/api";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ArrowLeftIcon, RefreshCwIcon } from "lucide-react";
import { BootSound } from "@/components/click-effects";
import { Button } from "@/components/ui/button";

export default function BotTradesPage() {
  const [trades, setTrades] = useState<TradeHistory[]>([]);
  const [bots, setBots] = useState<BotStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [botFilter, setBotFilter] = useState("all");

  const loadData = useCallback(async () => {
    try {
      const [t, dashboard] = await Promise.all([
        api.getAllBotTrades(),
        api.getDashboard(),
      ]);
      setTrades(t);
      setBots(dashboard.bots);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const filteredTrades =
    botFilter === "all"
      ? trades
      : trades.filter((t) => t.bot_id === botFilter);

  const botName = (botId: string) =>
    bots.find((b) => b.bot_id === botId)?.name ?? botId.slice(0, 8);

  // Summary stats
  const totalPnl = filteredTrades.reduce(
    (sum, t) => sum + (t.pnl ? Number(t.pnl) : 0),
    0
  );
  const wins = filteredTrades.filter(
    (t) => t.pnl && Number(t.pnl) > 0
  ).length;
  const losses = filteredTrades.filter(
    (t) => t.pnl && Number(t.pnl) < 0
  ).length;

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <BootSound />
        <div className="arc-spinner" />
        <p className="text-sm font-mono text-jarvis/60 tracking-widest uppercase">
          Loading Bot Trades...
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-6">
      {/* Header */}
      <header className="flex items-end justify-between mb-8 jarvis-boot jarvis-boot-1">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Link
              href="/"
              className="text-jarvis/50 hover:text-jarvis transition-colors jarvis-nav-link"
            >
              <ArrowLeftIcon className="size-5" />
            </Link>
            <h1 className="text-3xl font-bold tracking-[0.2em] font-mono text-jarvis text-glow jarvis-text-reveal">
              BOT TRADES
            </h1>
            <div className="h-[1px] w-16 bg-gradient-to-r from-jarvis/60 to-transparent jarvis-divider" />
          </div>
          <p className="text-xs font-mono text-muted-foreground tracking-[0.15em] uppercase">
            Execution history from your trading bots
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select
            value={botFilter}
            onValueChange={(v) => setBotFilter(v ?? "all")}
          >
            <SelectTrigger className="w-48 font-mono text-xs bg-jarvis/5 border-jarvis/15">
              <SelectValue placeholder="All bots" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all" className="font-mono text-xs">
                ALL BOTS
              </SelectItem>
              {bots.map((b) => (
                <SelectItem
                  key={b.bot_id}
                  value={b.bot_id}
                  className="font-mono text-xs"
                >
                  {b.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            onClick={() => {
              setLoading(true);
              loadData();
            }}
            className="bg-jarvis/10 text-jarvis border border-jarvis/30 hover:bg-jarvis/20 font-mono text-xs tracking-wider"
          >
            <RefreshCwIcon className="size-3 mr-2" />
            REFRESH
          </Button>
        </div>
      </header>

      {/* Summary Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <StatCard label="TOTAL TRADES" value={String(filteredTrades.length)} />
        <StatCard
          label="TOTAL PNL"
          value={`${totalPnl >= 0 ? "+" : ""}${totalPnl.toFixed(4)}`}
          accent={totalPnl >= 0 ? "text-emerald-400" : "text-red-400"}
        />
        <StatCard
          label="WINS"
          value={String(wins)}
          accent="text-emerald-400"
        />
        <StatCard
          label="LOSSES"
          value={String(losses)}
          accent="text-red-400"
        />
      </div>

      {filteredTrades.length === 0 ? (
        <div className="jarvis-card rounded-lg text-center py-16">
          <p className="text-muted-foreground text-sm font-mono mb-2">
            No bot trades found
          </p>
          <p className="text-xs text-muted-foreground/80 font-mono">
            Deploy and run a bot to see its trade execution history here
          </p>
        </div>
      ) : (
        <div className="jarvis-card rounded-lg border border-jarvis/10 overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="border-jarvis/10">
                <TableHead className="text-xs font-mono text-jarvis/60 tracking-wider">
                  BOT
                </TableHead>
                <TableHead className="text-xs font-mono text-jarvis/60 tracking-wider">
                  SYMBOL
                </TableHead>
                <TableHead className="text-xs font-mono text-jarvis/60 tracking-wider">
                  SIDE
                </TableHead>
                <TableHead className="text-xs font-mono text-jarvis/60 tracking-wider">
                  TYPE
                </TableHead>
                <TableHead className="text-xs font-mono text-jarvis/60 tracking-wider">
                  QTY
                </TableHead>
                <TableHead className="text-xs font-mono text-jarvis/60 tracking-wider">
                  PRICE
                </TableHead>
                <TableHead className="text-xs font-mono text-jarvis/60 tracking-wider">
                  STATUS
                </TableHead>
                <TableHead className="text-xs font-mono text-jarvis/60 tracking-wider">
                  PNL
                </TableHead>
                <TableHead className="text-xs font-mono text-jarvis/60 tracking-wider">
                  TIME
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredTrades.map((trade) => {
                const pnl = trade.pnl ? Number(trade.pnl) : null;
                return (
                  <TableRow key={trade.id} className="border-jarvis/5 jarvis-table-row">
                    <TableCell className="font-mono text-xs text-jarvis/70">
                      {botName(trade.bot_id)}
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {trade.symbol.replace("USDT", "")}
                    </TableCell>
                    <TableCell>
                      <span
                        className={`font-mono text-xs font-semibold ${
                          trade.side === "Buy"
                            ? "text-emerald-400"
                            : "text-red-400"
                        }`}
                      >
                        {trade.side === "Buy" ? "LONG" : "SHORT"}
                      </span>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {trade.order_type}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {Number(trade.qty).toFixed(4)}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {trade.price
                        ? `$${Number(trade.price).toLocaleString()}`
                        : "-"}
                    </TableCell>
                    <TableCell>
                      <span
                        className={`font-mono text-xs ${
                          trade.status === "Filled"
                            ? "text-emerald-400/70"
                            : trade.status === "Cancelled"
                              ? "text-red-400/70"
                              : "text-muted-foreground"
                        }`}
                      >
                        {trade.status}
                      </span>
                    </TableCell>
                    <TableCell>
                      {pnl !== null ? (
                        <span
                          className={`font-mono text-xs ${
                            pnl >= 0
                              ? "text-emerald-400"
                              : "text-red-400"
                          }`}
                        >
                          {pnl >= 0 ? "+" : ""}
                          {pnl.toFixed(4)}
                        </span>
                      ) : (
                        <span className="font-mono text-xs text-muted-foreground">
                          -
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {new Date(trade.created_at).toLocaleString("ko-KR", {
                        month: "2-digit",
                        day: "2-digit",
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                      })}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: string;
}) {
  return (
    <div className="jarvis-card rounded-lg p-4">
      <p className="text-xs font-mono text-muted-foreground/80 tracking-wider mb-1">
        {label}
      </p>
      <p
        className={`text-lg font-mono font-semibold ${accent || "text-foreground"}`}
      >
        {value}
      </p>
    </div>
  );
}
