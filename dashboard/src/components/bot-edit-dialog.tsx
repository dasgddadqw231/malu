"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { api, type BotControls } from "@/lib/api";
import { StrategyEditor } from "@/components/strategy-editor";
import { validateStrategyJson, DEFAULT_STRATEGY_JSON } from "@/lib/strategy";
import {
  CoinsIcon,
  ShieldAlertIcon,
} from "lucide-react";

// ─── Component ───────────────────────────────────────────────

export function BotEditDialog({
  botId,
  open,
  onOpenChange,
  onSaved,
}: {
  botId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
}) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState("");
  const [budget, setBudget] = useState("");
  const [strategyJson, setStrategyJson] = useState(DEFAULT_STRATEGY_JSON);
  const strategyValid = validateStrategyJson(strategyJson).valid;

  // Bot controls state
  const [maxDailyLoss, setMaxDailyLoss] = useState("");
  const [maxConsecutive, setMaxConsecutive] = useState("");
  const [cooldown, setCooldown] = useState("");
  const [maxTradesDay, setMaxTradesDay] = useState("");
  const [sizingMode, setSizingMode] = useState<"pct" | "fixed">("pct");
  const [fixedAmount, setFixedAmount] = useState("");
  const [compound, setCompound] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    api.getBot(botId).then((bot) => {
      setName(bot.name);
      setBudget(String(bot.seed_budget));
      if (bot.strategy_config && Object.keys(bot.strategy_config).length > 0) {
        setStrategyJson(JSON.stringify(bot.strategy_config, null, 2));
      }

      // Load controls
      const ctrl = bot.bot_controls;
      if (ctrl) {
        setMaxDailyLoss(ctrl.risk?.max_daily_loss_pct ? String(ctrl.risk.max_daily_loss_pct) : "");
        setMaxConsecutive(ctrl.risk?.max_consecutive_losses ? String(ctrl.risk.max_consecutive_losses) : "");
        setCooldown(ctrl.schedule?.cooldown_seconds ? String(ctrl.schedule.cooldown_seconds) : "");
        setMaxTradesDay(ctrl.schedule?.max_trades_per_day ? String(ctrl.schedule.max_trades_per_day) : "");
        setSizingMode(ctrl.sizing?.mode || "pct");
        setFixedAmount(ctrl.sizing?.fixed_amount_usd ? String(ctrl.sizing.fixed_amount_usd) : "");
        setCompound(ctrl.sizing?.compound || false);
      }
    }).catch(() => {}).finally(() => setLoading(false));
  }, [open, botId]);

  const buildControls = (): BotControls => {
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

  const handleSave = async () => {
    const v = validateStrategyJson(strategyJson);
    if (!v.valid || !v.parsed) {
      alert(v.error ?? "전략 JSON이 올바르지 않습니다.");
      return;
    }
    setSaving(true);
    try {
      await api.updateBot(botId, {
        name,
        seed_budget: Number(budget),
        strategy_config: v.parsed,
        bot_controls: buildControls(),
      });
      onOpenChange(false);
      onSaved();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-mono text-sm tracking-[0.15em] text-jarvis uppercase">
            Edit Bot Settings
          </DialogTitle>
        </DialogHeader>

        {loading ? (
          <div className="flex justify-center py-8">
            <div className="arc-spinner" />
          </div>
        ) : (
          <div className="space-y-5">
            {/* Name */}
            <div className="space-y-2">
              <Label className="text-xs font-mono text-muted-foreground tracking-wider">NAME</Label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="font-mono text-sm bg-jarvis/5 border-jarvis/15"
              />
            </div>

            {/* Budget */}
            <div className="space-y-2">
              <Label className="text-xs font-mono text-muted-foreground tracking-wider">SEED BUDGET</Label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-jarvis/40 font-mono">$</span>
                <Input
                  type="number"
                  value={budget}
                  onChange={(e) => setBudget(e.target.value)}
                  className="pl-7 font-mono text-sm bg-jarvis/5 border-jarvis/15"
                />
              </div>
            </div>

            {/* Strategy & Triggers */}
            <div className="pt-3 border-t border-jarvis/10 space-y-3">
              <Label className="text-xs font-mono text-foreground tracking-[0.15em] uppercase">STRATEGY &amp; TRIGGERS</Label>
              <StrategyEditor value={strategyJson} onChange={setStrategyJson} />
            </div>

            {/* Bot Controls */}
            <div className="pt-3 border-t border-jarvis/10 space-y-4">
              <div className="flex items-center gap-1.5">
                <ShieldAlertIcon className="size-3.5 text-jarvis/60" />
                <Label className="text-xs font-mono text-foreground tracking-[0.15em] uppercase">BOT CONTROLS</Label>
              </div>

              {/* Risk */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <span className="text-xs font-mono text-muted-foreground/70 tracking-wider">MAX DAILY LOSS %</span>
                  <Input type="number" value={maxDailyLoss} onChange={(e) => setMaxDailyLoss(e.target.value)} placeholder="off" className="font-mono text-sm bg-jarvis/5 border-jarvis/15" />
                </div>
                <div className="space-y-1">
                  <span className="text-xs font-mono text-muted-foreground/70 tracking-wider">STREAK LIMIT</span>
                  <Input type="number" value={maxConsecutive} onChange={(e) => setMaxConsecutive(e.target.value)} placeholder="off" className="font-mono text-sm bg-jarvis/5 border-jarvis/15" />
                </div>
              </div>

              {/* Schedule */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <span className="text-xs font-mono text-muted-foreground/70 tracking-wider">COOLDOWN (s)</span>
                  <Input type="number" value={cooldown} onChange={(e) => setCooldown(e.target.value)} placeholder="off" className="font-mono text-sm bg-jarvis/5 border-jarvis/15" />
                </div>
                <div className="space-y-1">
                  <span className="text-xs font-mono text-muted-foreground/70 tracking-wider">MAX TRADES/DAY</span>
                  <Input type="number" value={maxTradesDay} onChange={(e) => setMaxTradesDay(e.target.value)} placeholder="off" className="font-mono text-sm bg-jarvis/5 border-jarvis/15" />
                </div>
              </div>

              {/* Sizing */}
              <div className="space-y-2">
                <div className="flex items-center gap-1.5">
                  <CoinsIcon className="size-3 text-emerald-400/60" />
                  <span className="text-xs font-mono text-muted-foreground/70 tracking-wider">SIZING</span>
                </div>
                <div className="flex gap-2">
                  {(["pct", "fixed"] as const).map((m) => (
                    <button key={m} type="button" onClick={() => setSizingMode(m)}
                      className={`flex-1 rounded border px-2 py-1.5 text-xs font-mono transition-all ${
                        sizingMode === m ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-400" : "border-jarvis/10 text-muted-foreground hover:border-jarvis/25"
                      }`}>
                      {m === "pct" ? "STRATEGY %" : "FIXED $"}
                    </button>
                  ))}
                </div>
                {sizingMode === "fixed" && (
                  <Input type="number" value={fixedAmount} onChange={(e) => setFixedAmount(e.target.value)} placeholder="USD per trade" className="font-mono text-sm bg-jarvis/5 border-jarvis/15" />
                )}
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={compound} onChange={(e) => setCompound(e.target.checked)}
                    className="w-3.5 h-3.5 rounded border-jarvis/20 bg-jarvis/5 text-jarvis focus:ring-jarvis/20" />
                  <span className="text-xs font-mono text-muted-foreground tracking-wider">COMPOUND</span>
                </label>
              </div>
            </div>
          </div>
        )}

        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={saving}
            className="font-mono text-xs tracking-wider"
          >
            CANCEL
          </Button>
          <Button
            onClick={handleSave}
            disabled={saving || loading || !strategyValid}
            className="bg-jarvis/10 text-jarvis border border-jarvis/30 hover:bg-jarvis/20 font-mono text-xs tracking-[0.15em] uppercase disabled:opacity-30"
          >
            {saving ? "SAVING..." : "SAVE CHANGES"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
