"use client";

import { useState, useMemo, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, type BotControls } from "@/lib/api";
import { StrategyEditor } from "@/components/strategy-editor";
import { DEFAULT_STRATEGY_JSON, validateStrategyJson } from "@/lib/strategy";
import {
  ArrowLeftIcon,
  RocketIcon,
  ShieldAlertIcon,
  ClockIcon,
  CoinsIcon,
  ChevronDownIcon,
} from "lucide-react";

const POPULAR_SYMBOLS = ["BTCUSDT", "ETHUSDT"];

function generateBotTag(): string {
  const chars = "abcdefghijklmnopqrstuvwxyz0123456789";
  let tag = "";
  for (let i = 0; i < 6; i++) tag += chars[Math.floor(Math.random() * chars.length)];
  return tag;
}

// --- Risk presets ---
type RiskPreset = "off" | "conservative" | "moderate" | "aggressive";

const RISK_PRESETS: Record<RiskPreset, { label: string; desc: string; controls: BotControls }> = {
  off: {
    label: "OFF",
    desc: "No limits",
    controls: {},
  },
  conservative: {
    label: "CONSERVATIVE",
    desc: "Daily -3% / 2 streak / 10 trades",
    controls: {
      risk: { max_daily_loss_pct: 3, max_consecutive_losses: 2, max_single_loss_pct: 1.5 },
      schedule: { cooldown_seconds: 120, max_trades_per_day: 10 },
    },
  },
  moderate: {
    label: "MODERATE",
    desc: "Daily -5% / 3 streak / 20 trades",
    controls: {
      risk: { max_daily_loss_pct: 5, max_consecutive_losses: 3 },
      schedule: { cooldown_seconds: 60, max_trades_per_day: 20 },
    },
  },
  aggressive: {
    label: "AGGRESSIVE",
    desc: "Daily -10% / 5 streak / unlimited",
    controls: {
      risk: { max_daily_loss_pct: 10, max_consecutive_losses: 5 },
    },
  },
};

export default function DeployPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [budget, setBudget] = useState("");
  const [name, setName] = useState("");
  const [strategyJson, setStrategyJson] = useState(DEFAULT_STRATEGY_JSON);
  const [available, setAvailable] = useState(0);
  const [riskPreset, setRiskPreset] = useState<RiskPreset>("off");
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Advanced controls (custom overrides)
  const [maxDailyLoss, setMaxDailyLoss] = useState("");
  const [maxConsecutive, setMaxConsecutive] = useState("");
  const [cooldown, setCooldown] = useState("");
  const [maxTradesDay, setMaxTradesDay] = useState("");
  const [sizingMode, setSizingMode] = useState<"pct" | "fixed">("pct");
  const [fixedAmount, setFixedAmount] = useState("");
  const [compound, setCompound] = useState(false);

  useEffect(() => {
    api.getDashboard().then((d) => setAvailable(Number(d.available_budget))).catch(() => {});
  }, []);

  const budgetNum = Number(budget) || 0;

  const autoName = useMemo(() => {
    const base = symbol.replace("USDT", "");
    return name.trim() || `${base} Bot`;
  }, [symbol, name]);

  const strategyCheck = useMemo(() => validateStrategyJson(strategyJson), [strategyJson]);
  const strategyValid = strategyCheck.valid;
  const judgmentModule = useMemo(() => {
    const j = strategyCheck.parsed?.judgment as { module?: string } | undefined;
    return j?.module ?? "—";
  }, [strategyCheck]);

  const canSubmit = !!symbol && strategyValid;

  // Build bot_controls from preset or advanced
  const buildControls = (): BotControls => {
    if (!showAdvanced) return RISK_PRESETS[riskPreset].controls;

    const controls: BotControls = {};
    const risk: BotControls["risk"] = {};
    if (maxDailyLoss) risk.max_daily_loss_pct = Number(maxDailyLoss);
    if (maxConsecutive) risk.max_consecutive_losses = Number(maxConsecutive);
    if (Object.keys(risk).length) controls.risk = risk;

    const schedule: BotControls["schedule"] = {};
    if (cooldown) schedule.cooldown_seconds = Number(cooldown);
    if (maxTradesDay) schedule.max_trades_per_day = Number(maxTradesDay);
    if (Object.keys(schedule).length) controls.schedule = schedule;

    const sizing: BotControls["sizing"] = {};
    if (sizingMode === "fixed" && fixedAmount) {
      sizing.mode = "fixed";
      sizing.fixed_amount_usd = Number(fixedAmount);
    }
    if (compound) sizing.compound = true;
    if (Object.keys(sizing).length) controls.sizing = sizing;

    return controls;
  };

  const handleSubmit = async () => {
    const v = validateStrategyJson(strategyJson);
    if (!symbol || !v.valid || !v.parsed) return;
    setLoading(true);
    try {
      const controls = buildControls();
      await api.createBot({
        name: autoName,
        bot_tag: generateBotTag(),
        symbol: symbol.toUpperCase(),
        seed_budget: budgetNum,
        cycle_interval: 5,
        strategy_config: v.parsed,
        bot_controls: Object.keys(controls).length > 0 ? controls : undefined,
      });
      router.push("/");
    } catch (e) {
      alert(e instanceof Error ? e.message : "Bot deployment failed");
    } finally {
      setLoading(false);
    }
  };

  const activeControls = showAdvanced ? buildControls() : RISK_PRESETS[riskPreset].controls;
  const hasControls = Object.keys(activeControls).length > 0;

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-center gap-4 mb-10 jarvis-boot jarvis-boot-1">
        <Link
          href="/"
          className="flex items-center justify-center w-9 h-9 rounded-lg border border-jarvis/15 text-jarvis/50 hover:text-jarvis hover:border-jarvis/30 transition-all jarvis-nav-link"
        >
          <ArrowLeftIcon className="size-4" />
        </Link>
        <div>
          <h1 className="text-xl font-bold tracking-[0.15em] font-mono text-jarvis text-glow jarvis-text-reveal">
            DEPLOY NEW BOT
          </h1>
          <p className="text-xs font-mono text-muted-foreground tracking-[0.15em] uppercase">
            Configure strategy &amp; triggers, then deploy
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
        {/* Left: Config */}
        <div className="lg:col-span-3 space-y-6">
          {/* Symbol */}
          <section className="jarvis-card jarvis-corners rounded-lg p-6 space-y-4">
            <SectionHeader step={1} label="Target" />
            <div className="flex flex-wrap gap-2">
              {POPULAR_SYMBOLS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setSymbol(s)}
                  className={`rounded-lg border px-4 py-2.5 text-sm font-mono transition-all ${
                    symbol === s
                      ? "border-jarvis/50 bg-jarvis/10 text-jarvis shadow-[0_0_15px_rgba(0,212,255,0.1)]"
                      : "border-jarvis/10 text-muted-foreground hover:border-jarvis/30 hover:text-foreground"
                  }`}
                >
                  {s.replace("USDT", "")}
                </button>
              ))}
              <Input
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                placeholder="SYMBOL"
                className="w-32 text-sm font-mono bg-jarvis/5 border-jarvis/15"
              />
            </div>
          </section>

          {/* Name + Budget */}
          <section className="jarvis-card jarvis-corners rounded-lg p-6 space-y-4">
            <SectionHeader step={2} label="Name & Budget" />
            <div className="space-y-1.5">
              <span className="text-xs font-mono text-muted-foreground/70 tracking-wider">NAME</span>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={`${symbol.replace("USDT", "")} Bot`}
                className="text-sm font-mono bg-jarvis/5 border-jarvis/15"
              />
            </div>
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-jarvis/40 text-lg font-mono">$</span>
              <Input
                type="number"
                step="1"
                min="0"
                placeholder="0"
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                className="pl-9 text-2xl font-mono h-14 bg-jarvis/5 border-jarvis/15 focus:border-jarvis/40 focus:ring-jarvis/20"
              />
            </div>
            <p className="text-xs font-mono text-jarvis/40 text-right">
              AVAIL ${available.toLocaleString()}
            </p>
          </section>

          {/* Strategy / Triggers */}
          <section className="jarvis-card jarvis-corners rounded-lg p-6 space-y-4">
            <SectionHeader step={3} label="Strategy & Triggers" sub="strategy_config — 진입 트리거 / 방어 / 필터를 직접 정의" />
            <StrategyEditor value={strategyJson} onChange={setStrategyJson} />
          </section>

          {/* Bot Controls */}
          <section className="jarvis-card jarvis-corners rounded-lg p-6 space-y-4">
            <SectionHeader step={4} label="Bot Controls" sub="Risk limits, schedule, and sizing (independent of strategy)" />

            {/* Preset selector */}
            {!showAdvanced && (
              <div className="grid grid-cols-2 gap-3">
                {(Object.entries(RISK_PRESETS) as [RiskPreset, typeof RISK_PRESETS[RiskPreset]][]).map(([key, preset]) => {
                  const selected = riskPreset === key;
                  const colorMap: Record<string, string> = {
                    off: "jarvis",
                    conservative: "emerald",
                    moderate: "amber",
                    aggressive: "red",
                  };
                  const color = colorMap[key];
                  const iconMap: Record<string, typeof ShieldAlertIcon> = {
                    off: ShieldAlertIcon,
                    conservative: ShieldAlertIcon,
                    moderate: ClockIcon,
                    aggressive: CoinsIcon,
                  };
                  const Icon = iconMap[key];
                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setRiskPreset(key)}
                      className={`flex flex-col items-center gap-1.5 rounded-lg border p-4 text-center transition-all ${
                        selected
                          ? `border-${color}-400/40 bg-${color}-400/10`
                          : "border-jarvis/10 hover:border-jarvis/25"
                      }`}
                    >
                      <Icon className={`size-4 ${selected ? `text-${color}-400` : "text-muted-foreground"}`} />
                      <span className={`text-xs font-mono font-semibold tracking-wider ${selected ? `text-${color}-400` : ""}`}>
                        {preset.label}
                      </span>
                      <span className="text-xs font-mono text-muted-foreground/80">
                        {preset.desc}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}

            {/* Toggle advanced */}
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center gap-1.5 text-xs font-mono text-jarvis/50 hover:text-jarvis transition-colors tracking-wider"
            >
              <ChevronDownIcon className={`size-3 transition-transform ${showAdvanced ? "rotate-180" : ""}`} />
              {showAdvanced ? "USE PRESETS" : "ADVANCED SETTINGS"}
            </button>

            {/* Advanced controls */}
            {showAdvanced && (
              <div className="space-y-4 pt-2">
                {/* Risk */}
                <div className="space-y-3">
                  <div className="flex items-center gap-1.5">
                    <ShieldAlertIcon className="size-3 text-red-400/60" />
                    <span className="text-xs font-mono text-red-400/60 tracking-wider">RISK</span>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <ControlInput
                      label="MAX DAILY LOSS %"
                      value={maxDailyLoss}
                      onChange={setMaxDailyLoss}
                      placeholder="5"
                      suffix="%"
                    />
                    <ControlInput
                      label="MAX STREAK LOSSES"
                      value={maxConsecutive}
                      onChange={setMaxConsecutive}
                      placeholder="3"
                    />
                  </div>
                </div>

                {/* Schedule */}
                <div className="space-y-3">
                  <div className="flex items-center gap-1.5">
                    <ClockIcon className="size-3 text-amber-400/60" />
                    <span className="text-xs font-mono text-amber-400/60 tracking-wider">SCHEDULE</span>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <ControlInput
                      label="COOLDOWN"
                      value={cooldown}
                      onChange={setCooldown}
                      placeholder="60"
                      suffix="s"
                    />
                    <ControlInput
                      label="MAX TRADES/DAY"
                      value={maxTradesDay}
                      onChange={setMaxTradesDay}
                      placeholder="20"
                    />
                  </div>
                </div>

                {/* Sizing */}
                <div className="space-y-3">
                  <div className="flex items-center gap-1.5">
                    <CoinsIcon className="size-3 text-emerald-400/60" />
                    <span className="text-xs font-mono text-emerald-400/60 tracking-wider">SIZING</span>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <span className="text-xs font-mono text-muted-foreground/70 tracking-wider">MODE</span>
                      <div className="flex gap-2">
                        {(["pct", "fixed"] as const).map((m) => (
                          <button
                            key={m}
                            type="button"
                            onClick={() => setSizingMode(m)}
                            className={`flex-1 rounded border px-2 py-1.5 text-xs font-mono transition-all ${
                              sizingMode === m
                                ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-400"
                                : "border-jarvis/10 text-muted-foreground hover:border-jarvis/25"
                            }`}
                          >
                            {m === "pct" ? "STRATEGY %" : "FIXED $"}
                          </button>
                        ))}
                      </div>
                    </div>
                    {sizingMode === "fixed" && (
                      <ControlInput
                        label="FIXED USD/TRADE"
                        value={fixedAmount}
                        onChange={setFixedAmount}
                        placeholder="100"
                        suffix="$"
                      />
                    )}
                  </div>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={compound}
                      onChange={(e) => setCompound(e.target.checked)}
                      className="w-3.5 h-3.5 rounded border-jarvis/20 bg-jarvis/5 text-jarvis focus:ring-jarvis/20"
                    />
                    <span className="text-xs font-mono text-muted-foreground tracking-wider">
                      COMPOUND (reinvest profits)
                    </span>
                  </label>
                </div>
              </div>
            )}
          </section>
        </div>

        {/* Right: Preview */}
        <div className="lg:col-span-2">
          <div className="lg:sticky lg:top-8 space-y-6">
            {/* Preview Card */}
            <div className="jarvis-card jarvis-corners rounded-lg p-6 space-y-4">
              <h2 className="text-xs font-mono text-jarvis/60 tracking-[0.15em] uppercase">
                Deployment Preview
              </h2>

              <div className="space-y-3">
                <PreviewRow label="NAME" value={autoName} />
                <div className="h-[1px] bg-jarvis/5" />
                <PreviewRow label="SYMBOL" value={symbol} />
                <div className="h-[1px] bg-jarvis/5" />
                <PreviewRow label="BUDGET" value={budgetNum > 0 ? `$${budgetNum.toLocaleString()}` : "---"} />
                <div className="h-[1px] bg-jarvis/5" />
                <PreviewRow label="TRIGGER" value={judgmentModule} />
              </div>

              {hasControls && (
                <>
                  <div className="h-[1px] bg-jarvis/10 my-2" />
                  <h3 className="text-xs font-mono text-jarvis/40 tracking-[0.15em] uppercase">Controls</h3>
                  {activeControls.risk?.max_daily_loss_pct && (
                    <PreviewRow label="DAILY LOSS" value={`-${activeControls.risk.max_daily_loss_pct}%`} />
                  )}
                  {activeControls.risk?.max_consecutive_losses && (
                    <PreviewRow label="STREAK LIMIT" value={`${activeControls.risk.max_consecutive_losses}`} />
                  )}
                  {activeControls.schedule?.max_trades_per_day && (
                    <PreviewRow label="MAX TRADES" value={`${activeControls.schedule.max_trades_per_day}/day`} />
                  )}
                  {activeControls.schedule?.cooldown_seconds && (
                    <PreviewRow label="COOLDOWN" value={`${activeControls.schedule.cooldown_seconds}s`} />
                  )}
                  {activeControls.sizing?.mode === "fixed" && activeControls.sizing?.fixed_amount_usd && (
                    <PreviewRow label="SIZE" value={`$${activeControls.sizing.fixed_amount_usd}`} />
                  )}
                  {activeControls.sizing?.compound && (
                    <PreviewRow label="COMPOUND" value="ON" />
                  )}
                </>
              )}
            </div>

            {/* Submit */}
            <Button
              className="w-full h-14 bg-jarvis/10 text-jarvis border border-jarvis/30 hover:bg-jarvis/20 hover:shadow-[0_0_30px_rgba(0,212,255,0.2)] font-mono text-sm tracking-[0.15em] uppercase transition-all disabled:opacity-30"
              disabled={loading || !canSubmit}
              onClick={handleSubmit}
            >
              {loading ? (
                <span className="flex items-center gap-3">
                  <div className="w-4 h-4 rounded-full border-2 border-jarvis border-t-transparent animate-spin" />
                  DEPLOYING...
                </span>
              ) : (
                <span className="flex items-center gap-3">
                  <RocketIcon className="size-4" />
                  INITIALIZE BOT
                </span>
              )}
            </Button>

            {!strategyValid && (
              <p className="text-xs font-mono text-center text-red-400/80 tracking-wider">
                전략 JSON을 먼저 올바르게 작성하세요
              </p>
            )}
            <p className="text-xs font-mono text-center text-muted-foreground/80 tracking-wider">
              Bot will start in STOPPED state. Deploy from dashboard to activate.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function SectionHeader({ step, label, sub }: { step: number; label: string; sub?: string }) {
  return (
    <div className="flex items-center gap-2 mb-1">
      <span className="flex items-center justify-center w-6 h-6 rounded-full bg-jarvis/10 text-jarvis text-xs font-mono font-bold">{step}</span>
      <div>
        <Label className="text-xs font-mono text-foreground tracking-[0.15em] uppercase">{label}</Label>
        {sub && <p className="text-xs font-mono text-muted-foreground/80">{sub}</p>}
      </div>
    </div>
  );
}

function PreviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-center">
      <span className="font-mono text-xs text-muted-foreground tracking-[0.15em]">{label}</span>
      <span className="font-mono text-sm text-foreground">{value}</span>
    </div>
  );
}

function ControlInput({
  label,
  value,
  onChange,
  placeholder,
  suffix,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  suffix?: string;
}) {
  return (
    <div className="space-y-1.5">
      <span className="text-xs font-mono text-muted-foreground/70 tracking-wider">{label}</span>
      <div className="relative">
        <Input
          type="number"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="text-sm font-mono bg-jarvis/5 border-jarvis/15 pr-8"
        />
        {suffix && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-jarvis/30 text-xs font-mono">
            {suffix}
          </span>
        )}
      </div>
    </div>
  );
}
