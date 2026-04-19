"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { api, BotStatus } from "@/lib/api";
import { useTilt } from "@/hooks/use-tilt";
import { useWebSocket } from "@/hooks/use-websocket";
import { BotEditDialog } from "@/components/bot-edit-dialog";
import { BotLogModal } from "@/components/bot-log-modal";

const statusConfig: Record<string, { color: string; glow: string; label: string }> = {
  running: { color: "text-emerald-400", glow: "bg-emerald-400", label: "RUNNING" },
  waiting: { color: "text-amber-400", glow: "bg-amber-400", label: "WAITING" },
  in_position: { color: "text-jarvis", glow: "bg-jarvis", label: "IN POSITION" },
  judging: { color: "text-violet-400", glow: "bg-violet-400", label: "JUDGING" },
  acting: { color: "text-orange-400", glow: "bg-orange-400", label: "EXECUTING" },
  defending: { color: "text-red-400", glow: "bg-red-400", label: "DEFENDING" },
  stopped: { color: "text-zinc-500", glow: "bg-zinc-500", label: "OFFLINE" },
  killed: { color: "text-red-600", glow: "bg-red-600", label: "KILLED" },
  error: { color: "text-red-500", glow: "bg-red-500", label: "ERROR" },
};

export function BotCard({
  bot,
  budget,
  onAction,
}: {
  bot: BotStatus;
  budget?: { seed: string; used: string; available: string };
  onAction: () => void;
}) {
  const [loading, setLoading] = useState<string | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [logOpen, setLogOpen] = useState(false);
  const status = statusConfig[bot.status] || statusConfig.stopped;
  const { ref: tiltRef, handlers: tiltHandlers } = useTilt<HTMLDivElement>(!editOpen && !logOpen);
  const { events: botEvents } = useWebSocket(bot.bot_id, 5);

  const doAction = async (action: "start" | "stop" | "kill" | "delete") => {
    setLoading(action);
    try {
      if (action === "start") await api.startBot(bot.bot_id);
      else if (action === "stop") await api.stopBot(bot.bot_id);
      else if (action === "kill") await api.killBot(bot.bot_id);
      else if (action === "delete") {
        if (!confirm(`"${bot.name}" 봇을 삭제할까요?`)) return;
        await api.deleteBot(bot.bot_id);
      }
      onAction();
    } catch (e) {
      alert(e instanceof Error ? e.message : "작업 실패");
    } finally {
      setLoading(null);
    }
  };

  const isActive = !["stopped", "killed"].includes(bot.status);
  const budgetPct = budget
    ? Math.min(100, (Number(budget.available) / Number(budget.seed)) * 100)
    : 0;

  const meta = (bot.strategy_config as Record<string, unknown>)?._diy_meta as Record<string, unknown> | undefined;
  const strategySource: "nl" | "trade" =
    meta?.source === "natural_language" ? "nl" : "trade";

  return (
    <div
      ref={tiltRef}
      {...tiltHandlers}
      onClick={(e) => {
        if (logOpen || editOpen) return;
        // Don't open modal if clicking buttons or edit dialog
        if ((e.target as HTMLElement).closest("button, [data-slot]")) return;
        setLogOpen(true);
      }}
      className={`jarvis-card jarvis-corners jarvis-scanline rounded-lg p-5 group ${
        logOpen || editOpen ? "" : "jarvis-card-interactive cursor-pointer"
      }`}
    >
      {/* Holographic shimmer */}
      <div className="holo-shimmer" />

      {/* Header */}
      <div className="flex items-center justify-between mb-4 relative z-[2]">
        <div className="flex items-center gap-2">
          <div className="relative">
            <div className={`w-2 h-2 rounded-full ${status.glow} ${isActive ? "status-dot" : ""}`} />
          </div>
          <h3 className="font-mono font-semibold text-sm tracking-wide text-foreground">
            {bot.name}
          </h3>
        </div>
        <span className={`text-xs font-mono tracking-[0.1em] ${status.color}`}>
          {status.label}
        </span>
      </div>

      {/* Symbol & Strategy Tags */}
      <div className="flex items-center gap-2 mb-4 relative z-[2]">
        <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-jarvis/5 border border-jarvis/10">
          <span className="text-xs font-mono text-jarvis/60 uppercase tracking-wider">SYM</span>
          <span className="text-xs font-mono text-jarvis font-semibold">{bot.symbol}</span>
        </div>
        <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs font-mono tracking-wider ${
          strategySource === "nl"
            ? "bg-purple-400/5 border-purple-400/20 text-purple-400/70"
            : "bg-purple-400/5 border-purple-400/15 text-purple-400/60"
        }`}>
          {strategySource === "nl" ? "SIG·NL" : "SIG·TRADE"}
        </div>
        {bot.bot_controls && Object.keys(bot.bot_controls).length > 0 && (
          <div className="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-amber-400/15 bg-amber-400/5 text-xs font-mono tracking-wider text-amber-400/60">
            GUARD
          </div>
        )}
      </div>

      {/* Budget Data */}
      <div className="space-y-2 mb-4 relative z-[2]">
        <DataRow label="SEED" value={`$${Number(bot.seed_budget).toLocaleString()}`} />
        {budget && (
          <>
            <DataRow label="USED" value={`$${Number(budget.used).toLocaleString()}`} dim />
            <DataRow
              label="AVAIL"
              value={`$${Number(budget.available).toLocaleString()}`}
              highlight
            />
            {/* Budget bar */}
            <div className="h-1 bg-jarvis/5 rounded-full overflow-hidden mt-1">
              <div
                className="h-full rounded-full transition-all duration-500 progress-glow"
                style={{
                  width: `${budgetPct}%`,
                  background: `linear-gradient(90deg, #00d4ff, ${budgetPct > 50 ? "#00ff88" : "#ff6b00"})`,
                }}
              />
            </div>
          </>
        )}
      </div>

      {/* Mini Live Feed */}
      {botEvents.length > 0 && (
        <div className="mb-3 relative z-[2]">
          <div className="flex items-center gap-1.5 mb-1.5">
            <div className="w-1 h-1 rounded-full bg-jarvis/40 status-dot" />
            <span className="text-xs font-mono text-jarvis/40 tracking-[0.15em] uppercase">
              Live
            </span>
          </div>
          <div className="space-y-0.5">
            {botEvents.slice(0, 3).map((ev, i) => (
              <div
                key={i}
                className="flex items-center gap-1.5 text-xs font-mono py-0.5 px-1.5 rounded bg-jarvis/3"
              >
                <span className="text-jarvis/50 shrink-0">{ev.event}</span>
                <span className="text-muted-foreground/70 truncate">
                  {Object.entries(ev)
                    .filter(([k]) => !["event", "bot_id"].includes(k))
                    .map(([k, v]) => `${k}=${v}`)
                    .join(" ")}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2 pt-2 border-t border-jarvis/10 relative z-[2]">
        {!isActive ? (
          <>
            <Button
              size="sm"
              onClick={() => doAction("start")}
              disabled={loading !== null}
              className="flex-1 bg-jarvis/10 text-jarvis border border-jarvis/20 hover:bg-jarvis/20 jarvis-btn-interactive font-mono text-xs tracking-wider"
            >
              {loading === "start" ? "..." : "DEPLOY"}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setEditOpen(true)}
              disabled={loading !== null}
              className="text-jarvis/50 hover:text-jarvis hover:bg-jarvis/10 font-mono text-xs"
            >
              EDIT
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => doAction("delete")}
              disabled={loading !== null}
              className="text-red-400/70 hover:text-red-400 hover:bg-red-500/10 jarvis-btn-danger font-mono text-xs"
            >
              DEL
            </Button>
          </>
        ) : (
          <>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => doAction("stop")}
              disabled={loading !== null}
              className="flex-1 bg-amber-500/10 text-amber-400 border border-amber-500/20 hover:bg-amber-500/20 jarvis-btn-interactive font-mono text-xs tracking-wider"
            >
              {loading === "stop" ? "..." : "HALT"}
            </Button>
            <Button
              size="sm"
              variant="destructive"
              onClick={() => doAction("kill")}
              disabled={loading !== null}
              className="bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 jarvis-btn-interactive jarvis-btn-danger font-mono text-xs tracking-wider"
            >
              {loading === "kill" ? "..." : "KILL"}
            </Button>
          </>
        )}
      </div>

      <BotEditDialog
        botId={bot.bot_id}
        open={editOpen}
        onOpenChange={setEditOpen}
        onSaved={onAction}
      />

      <BotLogModal
        botId={bot.bot_id}
        botName={bot.name}
        open={logOpen}
        onOpenChange={setLogOpen}
      />
    </div>
  );
}

function DataRow({
  label,
  value,
  dim,
  highlight,
}: {
  label: string;
  value: string;
  dim?: boolean;
  highlight?: boolean;
}) {
  return (
    <div className="flex justify-between items-center text-xs">
      <span className="font-mono text-xs text-muted-foreground tracking-[0.1em]">{label}</span>
      <span
        className={`font-mono ${
          highlight
            ? "text-emerald-400 text-glow-sm"
            : dim
              ? "text-muted-foreground"
              : "text-foreground"
        }`}
      >
        {value}
      </span>
    </div>
  );
}
