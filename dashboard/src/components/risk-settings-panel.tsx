"use client";

import { useEffect, useState, useCallback } from "react";
import { api, RiskSettings } from "@/lib/api";

interface RuleConfig {
  key: keyof RiskSettings;
  label: string;
  description: string;
  unit: string;
  type: "pct" | "usd" | "int";
  placeholder: string;
}

const RULES: RuleConfig[] = [
  {
    key: "max_loss_pct",
    label: "AUTO STOP LOSS",
    description: "포지션 손실이 이 %를 넘으면 자동 청산",
    unit: "%",
    type: "pct",
    placeholder: "5.0",
  },
  {
    key: "max_profit_pct",
    label: "AUTO TAKE PROFIT",
    description: "포지션 수익이 이 %를 넘으면 자동 익절",
    unit: "%",
    type: "pct",
    placeholder: "0 (비활성)",
  },
  {
    key: "max_daily_loss_usd",
    label: "일일 최대 손실",
    description: "당일 총 손실이 이 금액 초과 시 전체 포지션 청산",
    unit: "$",
    type: "usd",
    placeholder: "0 (비활성)",
  },
  {
    key: "max_daily_trades",
    label: "일일 최대 거래 횟수",
    description: "하루 거래 횟수 제한 (오버트레이딩 방지)",
    unit: "회",
    type: "int",
    placeholder: "0 (무제한)",
  },
  {
    key: "max_position_pct",
    label: "최대 포지션 비율",
    description: "총 자산 대비 단일 포지션 최대 크기",
    unit: "%",
    type: "pct",
    placeholder: "0 (비활성)",
  },
  {
    key: "max_leverage",
    label: "최대 레버리지",
    description: "이 배율 초과 포지션 자동 거부",
    unit: "x",
    type: "int",
    placeholder: "0 (무제한)",
  },
];

export function RiskSettingsPanel() {
  const [settings, setSettings] = useState<RiskSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);

  const fetchSettings = useCallback(async () => {
    try {
      const data = await api.getRiskSettings();
      setSettings(data);
    } catch {
      // API not ready yet
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const handleToggle = async () => {
    if (!settings) return;
    setSaving(true);
    try {
      const updated = await api.updateRiskSettings({ enabled: !settings.enabled });
      setSettings(updated);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed to update");
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (key: keyof RiskSettings, value: string) => {
    if (!settings) return;
    const num = value === "" ? 0 : Number(value);
    if (isNaN(num)) return;
    setSettings({ ...settings, [key]: num });
    setDirty(true);
  };

  const handleSave = async () => {
    if (!settings) return;
    setSaving(true);
    try {
      const updated = await api.updateRiskSettings({
        max_loss_pct: settings.max_loss_pct,
        max_profit_pct: settings.max_profit_pct,
        max_daily_loss_usd: settings.max_daily_loss_usd,
        max_daily_trades: settings.max_daily_trades,
        max_position_pct: settings.max_position_pct,
        max_leverage: settings.max_leverage,
        notify_on_close: settings.notify_on_close,
      });
      setSettings(updated);
      setDirty(false);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="jarvis-card jarvis-corners rounded-lg p-6 text-center">
        <p className="text-xs font-mono text-jarvis/40 tracking-wider">LOADING RISK SETTINGS...</p>
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="jarvis-card jarvis-corners rounded-lg p-6 text-center">
        <p className="text-muted-foreground text-sm font-mono">Risk settings unavailable</p>
        <p className="text-xs text-muted-foreground/60 font-mono mt-1">
          Run the migration and restart the engine
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Master toggle */}
      <div
        className={`jarvis-card jarvis-corners rounded-lg p-4 border transition-all ${
          settings.enabled ? "border-emerald-500/30" : "border-jarvis/10"
        }`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className={`w-3 h-3 rounded-full transition-all ${
                settings.enabled
                  ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]"
                  : "bg-muted-foreground/30"
              }`}
            />
            <div>
              <p className="text-sm font-mono font-bold text-foreground">
                RISK GUARD {settings.enabled ? "ACTIVE" : "INACTIVE"}
              </p>
              <p className="text-xs font-mono text-muted-foreground/60">
                매뉴얼 포지션 자동 리스크 관리
              </p>
            </div>
          </div>
          <button
            onClick={handleToggle}
            disabled={saving}
            className={`px-4 py-2 rounded text-xs font-mono font-bold tracking-wider transition-all ${
              settings.enabled
                ? "bg-red-500/15 text-red-400 border border-red-500/30 hover:bg-red-500/25"
                : "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/25"
            }`}
          >
            {settings.enabled ? "DEACTIVATE" : "ACTIVATE"}
          </button>
        </div>
      </div>

      {/* Rules grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {RULES.map((rule) => {
          const value = settings[rule.key] as number;
          const isActive = value > 0;
          return (
            <div
              key={rule.key}
              className={`jarvis-card jarvis-corners rounded-lg p-4 border transition-all ${
                isActive && settings.enabled
                  ? "border-jarvis/25"
                  : "border-jarvis/8"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-mono font-bold text-foreground tracking-wider">
                  {rule.label}
                </p>
                {isActive && settings.enabled && (
                  <span className="text-[10px] font-mono text-emerald-400 bg-emerald-400/10 px-1.5 py-0.5 rounded">
                    ON
                  </span>
                )}
              </div>
              <p className="text-[11px] font-mono text-muted-foreground/60 mb-3">
                {rule.description}
              </p>
              <div className="flex items-center gap-2">
                {rule.unit === "$" && (
                  <span className="text-xs font-mono text-muted-foreground/40">$</span>
                )}
                <input
                  type="number"
                  value={value || ""}
                  onChange={(e) => handleChange(rule.key, e.target.value)}
                  placeholder={rule.placeholder}
                  className="flex-1 bg-jarvis/5 border border-jarvis/15 rounded px-3 py-1.5 text-xs font-mono text-foreground placeholder:text-muted-foreground/30 focus:border-jarvis/40 focus:outline-none transition-colors"
                  min={0}
                  step={rule.type === "int" ? 1 : 0.1}
                />
                {rule.unit !== "$" && (
                  <span className="text-xs font-mono text-muted-foreground/40">{rule.unit}</span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Save button */}
      {dirty && (
        <div className="flex justify-end">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-6 py-2 rounded bg-jarvis/15 text-jarvis border border-jarvis/30 hover:bg-jarvis/25 text-xs font-mono font-bold tracking-wider transition-all"
          >
            {saving ? "SAVING..." : "SAVE CHANGES"}
          </button>
        </div>
      )}
    </div>
  );
}
