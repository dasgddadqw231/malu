"use client";

import { useWebSocket } from "@/hooks/use-websocket";
import { useEffect, useRef, useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { api, type TradeHistory } from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";

type Tab = "logs" | "trades";

export function BotLogModal({
  botId,
  botName,
  open,
  onOpenChange,
}: {
  botId: string;
  botName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { events, connected, clearEvents } = useWebSocket(
    open ? botId : undefined,
    200
  );
  const feedRef = useRef<HTMLDivElement>(null);
  const [tab, setTab] = useState<Tab>("logs");
  const [trades, setTrades] = useState<TradeHistory[]>([]);
  const [tradesLoading, setTradesLoading] = useState(false);

  // Auto-scroll to latest
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = 0;
    }
  }, [events.length]);

  const loadTrades = useCallback(async () => {
    setTradesLoading(true);
    try {
      const t = await api.getBotTrades(botId);
      setTrades(t);
    } catch {
      // ignore
    } finally {
      setTradesLoading(false);
    }
  }, [botId]);

  useEffect(() => {
    if (open && tab === "trades") {
      loadTrades();
    }
  }, [open, tab, loadTrades]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl sm:max-h-[85vh]" showCloseButton>
        <DialogHeader>
          <DialogTitle className="font-mono text-sm tracking-[0.15em] text-jarvis flex items-center gap-3">
            <div className="flex items-center gap-2">
              <svg
                viewBox="0 0 24 24"
                className="w-4 h-4 text-jarvis/50"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <span>{botName}</span>
            </div>
            <div className="flex items-center gap-1.5 ml-auto mr-6">
              <div
                className={`w-1.5 h-1.5 rounded-full ${
                  connected ? "bg-emerald-400 status-dot" : "bg-red-500"
                }`}
              />
              <span className="text-xs text-muted-foreground tracking-wider font-normal">
                {connected ? "LIVE" : "OFFLINE"}
              </span>
            </div>
          </DialogTitle>
          <DialogDescription className="sr-only">
            Real-time log stream and trade history for {botName}
          </DialogDescription>
        </DialogHeader>

        {/* Tab Bar */}
        <div className="flex items-center gap-1 border-b border-jarvis/10 pb-1">
          <button
            onClick={() => setTab("logs")}
            className={`px-3 py-1.5 text-xs font-mono tracking-wider rounded-t transition-colors ${
              tab === "logs"
                ? "text-jarvis border-b-2 border-jarvis"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            LOGS
          </button>
          <button
            onClick={() => setTab("trades")}
            className={`px-3 py-1.5 text-xs font-mono tracking-wider rounded-t transition-colors ${
              tab === "trades"
                ? "text-jarvis border-b-2 border-jarvis"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            TRADES
          </button>
        </div>

        {tab === "logs" && (
          <>
            {/* Controls */}
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-jarvis/30">
                {events.length} events
              </span>
              {events.length > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearEvents}
                  className="text-xs font-mono text-muted-foreground hover:text-jarvis h-6 px-2 tracking-wider"
                >
                  CLEAR
                </Button>
              )}
            </div>

            {/* Live Feed */}
            <div
              ref={feedRef}
              className="max-h-[60vh] overflow-y-auto jarvis-scroll rounded-lg border border-jarvis/10 bg-black/30"
            >
              {events.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 gap-2">
                  <div className="w-8 h-8 rounded-full border border-jarvis/10 flex items-center justify-center">
                    <div className="w-2 h-2 rounded-full bg-jarvis/20 jarvis-pulse" />
                  </div>
                  <p className="text-xs font-mono text-muted-foreground/80 tracking-wider">
                    Awaiting data stream...
                  </p>
                </div>
              ) : (
                <div className="p-2 space-y-0.5">
                  {events.map((event, i) => (
                    <div
                      key={i}
                      className="feed-row-interactive flex items-start gap-2 text-xs font-mono py-1.5 px-2 rounded"
                    >
                      <div className="w-1 h-1 rounded-full bg-jarvis/30 shrink-0 mt-1.5" />
                      <span className="text-jarvis/70 shrink-0 min-w-[80px]">
                        {event.event}
                      </span>
                      <span className="text-jarvis/15">|</span>
                      <span className="text-muted-foreground/80 break-all">
                        {Object.entries(event)
                          .filter(([k]) => !["event", "bot_id"].includes(k))
                          .map(([k, v]) => `${k}=${v}`)
                          .join(" ")}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        {tab === "trades" && (
          <div className="max-h-[60vh] overflow-y-auto jarvis-scroll rounded-lg border border-jarvis/10 bg-black/30">
            {tradesLoading ? (
              <div className="flex flex-col items-center justify-center py-16 gap-2">
                <div className="arc-spinner !w-6 !h-6" />
                <p className="text-xs font-mono text-muted-foreground/80 tracking-wider">
                  Loading trades...
                </p>
              </div>
            ) : trades.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 gap-2">
                <p className="text-xs font-mono text-muted-foreground/80 tracking-wider">
                  No trades yet
                </p>
              </div>
            ) : (
              <div className="p-2 space-y-0.5">
                {trades.map((trade) => {
                  const pnl = trade.pnl ? Number(trade.pnl) : null;
                  return (
                    <div
                      key={trade.id}
                      className="feed-row-interactive flex items-center gap-3 text-xs font-mono py-2 px-3 rounded"
                    >
                      <span
                        className={`font-semibold w-10 ${
                          trade.side === "Buy"
                            ? "text-emerald-400"
                            : "text-red-400"
                        }`}
                      >
                        {trade.side === "Buy" ? "LONG" : "SHORT"}
                      </span>
                      <span className="text-foreground/80 w-20">
                        {trade.symbol.replace("USDT", "")}
                      </span>
                      <span className="text-muted-foreground w-16">
                        {Number(trade.qty).toFixed(4)}
                      </span>
                      <span className="text-muted-foreground w-24">
                        {trade.price
                          ? `$${Number(trade.price).toLocaleString()}`
                          : "-"}
                      </span>
                      <span className="text-muted-foreground/60 w-16 uppercase">
                        {trade.status}
                      </span>
                      {pnl !== null ? (
                        <span
                          className={`w-20 text-right ${
                            pnl >= 0
                              ? "text-emerald-400"
                              : "text-red-400"
                          }`}
                        >
                          {pnl >= 0 ? "+" : ""}
                          {pnl.toFixed(4)}
                        </span>
                      ) : (
                        <span className="w-20 text-right text-muted-foreground">
                          -
                        </span>
                      )}
                      <span className="ml-auto text-muted-foreground/50">
                        {new Date(trade.created_at).toLocaleString("ko-KR", {
                          month: "2-digit",
                          day: "2-digit",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
