"use client";

import Link from "next/link";
import { useDashboard } from "@/hooks/use-dashboard";
import { BotCard } from "@/components/bot-card";
import { KillSwitch } from "@/components/kill-switch";
import { BootSound } from "@/components/click-effects";

export default function Dashboard() {
  const { data, error, loading, refresh } = useDashboard();

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <BootSound />
        <div className="arc-spinner" />
        <p className="text-sm font-mono text-jarvis/60 tracking-widest uppercase">
          Initializing System...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <div className="w-12 h-12 rounded-full border-2 border-red-500/50 flex items-center justify-center">
          <span className="text-red-400 text-xl">!</span>
        </div>
        <p className="text-red-400 font-mono text-sm">SYSTEM ERROR: {error}</p>
        <p className="text-xs text-muted-foreground font-mono">
          API endpoint http://localhost:8000 unreachable
        </p>
      </div>
    );
  }

  const totalBots = data?.total_bots ?? 0;
  const activeBots = data?.active_bots ?? 0;
  const availBudget = Number(data?.available_budget ?? 0);
  const killActive = data?.kill_switch_active ?? false;
  const totalPnl = Number(data?.total_pnl ?? 0);

  return (
    <div className="max-w-7xl mx-auto px-6 py-6">
      {/* Header */}
      <header className="flex items-end justify-between mb-8 jarvis-boot jarvis-boot-1">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-3xl font-bold tracking-[0.2em] font-mono text-jarvis text-glow jarvis-text-reveal">
              MALU
            </h1>
            <div className="h-[1px] w-16 bg-gradient-to-r from-jarvis/60 to-transparent jarvis-divider" />
          </div>
          <p className="text-xs font-mono text-muted-foreground tracking-[0.15em] uppercase">
            Multi-Agent Leverage Unit // Trading System v1.0
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/trades"
            className="jarvis-nav-link rounded border border-jarvis/20 bg-jarvis/5 px-3 py-2 text-xs font-mono text-jarvis/70 hover:text-jarvis hover:border-jarvis/40 transition-all tracking-wider"
          >
            MANUAL TRADES
          </Link>
          <Link
            href="/bot-trades"
            className="jarvis-nav-link rounded border border-jarvis/20 bg-jarvis/5 px-3 py-2 text-xs font-mono text-jarvis/70 hover:text-jarvis hover:border-jarvis/40 transition-all tracking-wider"
          >
            BOT TRADES
          </Link>
          <Link
            href="/diy"
            className="jarvis-nav-link jarvis-nav-link-purple rounded border border-purple-400/20 bg-purple-400/5 px-3 py-2 text-xs font-mono text-purple-400/70 hover:text-purple-400 hover:border-purple-400/40 transition-all tracking-wider"
          >
            SIGNATURE
          </Link>
        </div>
      </header>

      {/* Stats HUD */}
      <div className="grid grid-cols-5 gap-3 mb-8 jarvis-boot jarvis-boot-2">
        <HudStat
          label="TOTAL PNL"
          value={`${totalPnl >= 0 ? "+" : ""}$${Math.abs(totalPnl).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          accent={totalPnl >= 0 ? "green" : "red"}
          icon={
            <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M3 3v18h18" />
              <path d="M7 16l4-8 4 4 6-10" />
            </svg>
          }
        />
        <HudStat
          label="TOTAL BOTS"
          value={totalBots}
          icon={
            <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.5">
              <rect x="3" y="3" width="7" height="7" rx="1" />
              <rect x="14" y="3" width="7" height="7" rx="1" />
              <rect x="3" y="14" width="7" height="7" rx="1" />
              <rect x="14" y="14" width="7" height="7" rx="1" />
            </svg>
          }
        />
        <HudStat
          label="ACTIVE"
          value={activeBots}
          accent={activeBots > 0 ? "cyan" : undefined}
          icon={
            <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
            </svg>
          }
        />
        <HudStat
          label="AVAIL BUDGET"
          value={`$${availBudget.toLocaleString()}`}
          accent="green"
          icon={
            <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" />
            </svg>
          }
        />
        <HudStat
          label="KILL SWITCH"
          value={killActive ? "ARMED" : "STANDBY"}
          accent={killActive ? "red" : "green"}
          icon={
            <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            </svg>
          }
        />
      </div>

      {/* Bot Fleet Header */}
      <div className="flex items-center gap-4 mb-8 jarvis-boot jarvis-boot-3">
        <div className="h-[1px] flex-1 bg-gradient-to-r from-transparent via-jarvis/20 to-transparent jarvis-divider" />
        <span className="text-xs font-mono text-jarvis/40 tracking-[0.3em] uppercase">
          Bot Fleet
        </span>
        <div className="h-[1px] flex-1 bg-gradient-to-r from-transparent via-jarvis/20 to-transparent" />
        <div className="flex items-center gap-2">
          <Link
            href="/deploy"
            className="jarvis-nav-link flex items-center gap-1.5 rounded border border-jarvis/20 bg-jarvis/5 px-3 py-1.5 text-xs font-mono text-jarvis/70 hover:text-jarvis hover:border-jarvis/40 hover:bg-jarvis/10 transition-all tracking-wider"
          >
            <svg viewBox="0 0 24 24" className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M12 5v14M5 12h14" />
            </svg>
            DEPLOY
          </Link>
          <KillSwitch isActive={killActive} onKilled={refresh} />
        </div>
      </div>

      {/* Bot Grid */}
      {data?.bots.length === 0 ? (
        <div className="jarvis-card jarvis-corners rounded-lg text-center py-16 mb-8">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full border border-jarvis/20 flex items-center justify-center">
            <svg viewBox="0 0 24 24" className="w-6 h-6 text-jarvis/30" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M12 5v14M5 12h14" />
            </svg>
          </div>
          <p className="text-muted-foreground text-sm font-mono mb-1">No bots deployed</p>
          <p className="text-xs text-muted-foreground/80 font-mono">
            Deploy your first trading bot to begin operations
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8 jarvis-boot jarvis-boot-4">
          {data?.bots.map((bot) => (
            <BotCard
              key={bot.bot_id}
              bot={bot}
              budget={data.budget[bot.bot_id]}
              onAction={refresh}
            />
          ))}
        </div>
      )}

      {/* Footer line */}
      <div className="mt-8 pb-4 flex items-center justify-center">
        <span className="text-xs font-mono text-jarvis/20 tracking-[0.2em]">
          MALU SYSTEM // OPERATIONAL
        </span>
      </div>
    </div>
  );
}

function HudStat({
  label,
  value,
  accent,
  icon,
}: {
  label: string;
  value: string | number;
  accent?: "cyan" | "green" | "red";
  icon?: React.ReactNode;
}) {
  const accentColors = {
    cyan: "text-jarvis text-glow-sm",
    green: "text-emerald-400",
    red: "text-red-400",
  };

  const borderColors = {
    cyan: "border-jarvis/30",
    green: "border-emerald-500/20",
    red: "border-red-500/20",
  };

  return (
    <div
      className={`jarvis-card jarvis-corners hud-stat-interactive rounded-lg p-4 cursor-default ${
        accent ? borderColors[accent] : ""
      }`}
    >
      <div className="flex items-center gap-2 mb-2">
        <span className="text-jarvis/50">{icon}</span>
        <p className="text-xs font-mono text-muted-foreground tracking-[0.15em] uppercase">
          {label}
        </p>
      </div>
      <p
        className={`text-2xl font-bold font-mono hud-value transition-all ${
          accent ? accentColors[accent] : "text-foreground"
        }`}
      >
        {value}
      </p>
    </div>
  );
}
