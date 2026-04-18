"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, type ManualDataset, type SignatureMessage, type SignatureChatResponse } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeftIcon,
  RefreshCwIcon,
  SparklesIcon,
  XIcon,
  DatabaseIcon,
  CheckIcon,
  ZapIcon,
  SendIcon,
  ShieldIcon,
  TargetIcon,
  TimerIcon,
  TrendingUpIcon,
  ArrowRightIcon,
} from "lucide-react";

// Rule type icon helper
function RuleIcon({ type }: { type: string }) {
  switch (type) {
    case "entry": return <TrendingUpIcon className="size-3 text-emerald-400" />;
    case "stop_loss": return <ShieldIcon className="size-3 text-red-400" />;
    case "take_profit": return <TargetIcon className="size-3 text-amber-400" />;
    case "position_size": return <ArrowRightIcon className="size-3 text-blue-400" />;
    case "cycle_interval": return <TimerIcon className="size-3 text-purple-400" />;
    default: return <SparklesIcon className="size-3 text-jarvis/50" />;
  }
}

export default function NewSignaturePage() {
  const router = useRouter();

  // Chat state
  const [signatureId, setSignatureId] = useState<string | null>(null);
  const [messages, setMessages] = useState<SignatureMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [signatureName, setSignatureName] = useState("");
  const [nameSet, setNameSet] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Strategy preview
  const [strategyConfig, setStrategyConfig] = useState<Record<string, unknown> | null>(null);
  const [rules, setRules] = useState<Record<string, unknown>[]>([]);

  // Dataset picker
  const [datasets, setDatasets] = useState<ManualDataset[]>([]);
  const [datasetsLoading, setDatasetsLoading] = useState(false);
  const [showDatasetPicker, setShowDatasetPicker] = useState(false);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(null);

  const selectedDataset = datasets.find((d) => d.id === selectedDatasetId);

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const loadDatasets = async () => {
    if (showDatasetPicker) { setShowDatasetPicker(false); return; }
    if (datasets.length > 0) { setShowDatasetPicker(true); return; }
    setDatasetsLoading(true);
    try {
      const ds = await api.listDatasets();
      setDatasets(ds);
      setShowDatasetPicker(true);
    } catch { /* ignore */ } finally {
      setDatasetsLoading(false);
    }
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;
    if (!nameSet) return;

    setSending(true);
    setInput("");

    // Optimistically add user message
    setMessages((prev) => [...prev, { role: "user", content: text }]);

    try {
      let res: SignatureChatResponse;

      if (!signatureId) {
        // First message — create signature
        res = await api.startSignatureChat(signatureName, text, selectedDatasetId || undefined);
        setSignatureId(res.id);
      } else {
        // Subsequent messages — refine
        res = await api.chatWithSignature(signatureId, text);
      }

      // Add assistant reply
      setMessages((prev) => [...prev, { role: "assistant", content: res.reply }]);
      setStrategyConfig(res.strategy_config);
      setRules(res.rules);
    } catch (e) {
      // Remove optimistic message on error
      setMessages((prev) => prev.slice(0, -1));
      setInput(text);
      alert(e instanceof Error ? e.message : "Failed to send");
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNameKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && signatureName.trim()) {
      setNameSet(true);
    }
  };

  // Extract config values for preview
  const judgment = (strategyConfig?.judgment as Record<string, unknown>) || null;
  const judgmentParams = (judgment?.params as Record<string, unknown>) || null;
  const action = (strategyConfig?.action as Record<string, unknown>) || null;
  const actionParams = (action?.params as Record<string, unknown>) || null;
  const defense = (strategyConfig?.defense as Record<string, unknown>) || null;
  const defenseParams = (defense?.params as Record<string, unknown>) || null;
  const cycleInterval = strategyConfig?.cycle_interval;

  return (
    <div className="h-[calc(100vh-3.5rem)] flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-jarvis/10 shrink-0">
        <div className="flex items-center gap-3">
          <Link href="/diy" className="text-jarvis/50 hover:text-jarvis transition-colors">
            <ArrowLeftIcon className="size-5" />
          </Link>
          <SparklesIcon className="size-4 text-purple-400" />
          <h1 className="text-lg font-bold tracking-[0.15em] font-mono text-jarvis">
            {nameSet ? signatureName : "NEW SIGNATURE"}
          </h1>
          {signatureId && (
            <Badge variant="outline" className="text-xs font-mono border-emerald-400/30 text-emerald-400/70">
              SAVED
            </Badge>
          )}
        </div>
        {signatureId && (
          <Button
            onClick={() => router.push("/diy")}
            className="bg-jarvis/20 text-jarvis border border-jarvis/40 hover:bg-jarvis/30 font-mono text-xs tracking-wider"
          >
            DONE
          </Button>
        )}
      </header>

      <div className="flex flex-1 min-h-0">
        {/* Chat panel */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Messages area */}
          <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
            {/* Name input step */}
            {!nameSet && (
              <div className="flex flex-col items-center justify-center h-full gap-6">
                <div className="text-center space-y-2">
                  <SparklesIcon className="size-8 text-purple-400 mx-auto" />
                  <h2 className="text-xl font-bold font-mono text-jarvis tracking-wider">CREATE SIGNATURE</h2>
                  <p className="text-xs font-mono text-muted-foreground max-w-sm">
                    Give your strategy a name, then describe it in natural language. We'll refine it together through conversation.
                  </p>
                </div>

                <div className="w-full max-w-md space-y-4">
                  <div className="space-y-1">
                    <label className="text-xs font-mono text-muted-foreground tracking-wider">SIGNATURE NAME</label>
                    <Input
                      placeholder="예: 보수적 스캘핑"
                      value={signatureName}
                      onChange={(e) => setSignatureName(e.target.value)}
                      onKeyDown={handleNameKeyDown}
                      className="font-mono text-sm bg-jarvis/5 border-purple-400/15 focus:border-purple-400/40"
                      autoFocus
                    />
                  </div>

                  {/* Dataset selector */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <DatabaseIcon className="size-3.5 text-jarvis/40" />
                        <span className="text-xs font-mono text-jarvis/60 tracking-wider">REFERENCE DATASET</span>
                        <span className="text-xs font-mono text-muted-foreground/40">(optional)</span>
                      </div>
                      <button
                        onClick={loadDatasets}
                        disabled={datasetsLoading}
                        className="text-xs font-mono text-purple-400/50 hover:text-purple-400 transition-colors flex items-center gap-1"
                      >
                        {datasetsLoading ? (
                          <RefreshCwIcon className="size-3 animate-spin" />
                        ) : showDatasetPicker ? (
                          <><XIcon className="size-3" /> CLOSE</>
                        ) : selectedDataset ? (
                          "CHANGE"
                        ) : (
                          <><DatabaseIcon className="size-3" /> SELECT</>
                        )}
                      </button>
                    </div>

                    {selectedDataset && !showDatasetPicker && (
                      <div className="flex items-center gap-2 p-2.5 rounded border border-jarvis/15 bg-jarvis/5">
                        <DatabaseIcon className="size-3.5 text-jarvis/50" />
                        <span className="text-xs font-mono text-jarvis font-semibold">{selectedDataset.name}</span>
                        <Badge variant="outline" className="text-xs font-mono border-jarvis/20 text-jarvis/50">
                          {selectedDataset.trade_ids.length} trades
                        </Badge>
                        {selectedDataset.auto_sync && (
                          <Badge variant="outline" className="text-xs font-mono border-emerald-400/30 text-emerald-400/70">
                            <ZapIcon className="size-2.5 mr-0.5" /> AUTO
                          </Badge>
                        )}
                        <button onClick={() => setSelectedDatasetId(null)} className="ml-auto text-muted-foreground/50 hover:text-red-400 transition-colors">
                          <XIcon className="size-3" />
                        </button>
                      </div>
                    )}

                    {showDatasetPicker && (
                      <div className="max-h-40 overflow-y-auto rounded border border-jarvis/10 bg-background/50">
                        {datasets.length === 0 ? (
                          <div className="p-3 text-center">
                            <p className="text-xs font-mono text-muted-foreground/60">No datasets found</p>
                          </div>
                        ) : (
                          datasets.map((ds) => {
                            const isSelected = selectedDatasetId === ds.id;
                            return (
                              <button
                                key={ds.id}
                                onClick={() => { setSelectedDatasetId(ds.id); setShowDatasetPicker(false); }}
                                className={`w-full px-3 py-2 text-left text-xs font-mono flex items-center gap-3 border-b border-jarvis/5 last:border-0 transition-colors ${isSelected ? "bg-purple-400/10 text-foreground" : "hover:bg-jarvis/5 text-muted-foreground"}`}
                              >
                                <div className={`size-4 rounded border flex items-center justify-center ${isSelected ? "border-purple-400 bg-purple-400/20" : "border-jarvis/20"}`}>
                                  {isSelected && <CheckIcon className="size-3 text-purple-400" />}
                                </div>
                                <span className="font-semibold">{ds.name}</span>
                                <Badge variant="outline" className="text-xs font-mono border-jarvis/15 text-jarvis/40">
                                  {ds.trade_ids.length} trades
                                </Badge>
                                {ds.auto_sync && <ZapIcon className="size-3 text-emerald-400/50" />}
                              </button>
                            );
                          })
                        )}
                      </div>
                    )}
                  </div>

                  <Button
                    onClick={() => setNameSet(true)}
                    disabled={!signatureName.trim()}
                    className="w-full bg-purple-400/20 text-purple-400 border border-purple-400/40 hover:bg-purple-400/30 font-mono text-xs tracking-wider"
                  >
                    START BUILDING
                  </Button>
                </div>
              </div>
            )}

            {/* Chat messages */}
            {nameSet && messages.length === 0 && !sending && (
              <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
                <SparklesIcon className="size-6 text-purple-400/40" />
                <div className="space-y-1">
                  <p className="text-sm font-mono text-muted-foreground">
                    Describe your trading strategy
                  </p>
                  <p className="text-xs font-mono text-muted-foreground/50 max-w-sm">
                    Start by describing your approach, then refine through conversation
                  </p>
                </div>
                <div className="flex flex-wrap gap-1.5 justify-center max-w-md">
                  {[
                    "보수적으로 소액 단타",
                    "공격적 진입, 손절 2% 익절 6%",
                    "스윙, 안전하게 작은 포지션",
                    "스캘핑, 빠른 주기, 타이트한 손익절",
                  ].map((hint) => (
                    <button
                      key={hint}
                      onClick={() => setInput(hint)}
                      className="px-2.5 py-1 rounded border border-purple-400/15 bg-purple-400/5 text-xs font-mono text-purple-400/60 hover:text-purple-400 hover:border-purple-400/30 transition-all"
                    >
                      {hint}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[80%] rounded-lg px-4 py-2.5 ${
                  msg.role === "user"
                    ? "bg-purple-400/15 border border-purple-400/20 text-foreground"
                    : "bg-jarvis/5 border border-jarvis/10 text-foreground"
                }`}>
                  <p className="text-sm font-mono whitespace-pre-wrap">{msg.content}</p>
                </div>
              </div>
            ))}

            {sending && (
              <div className="flex justify-start">
                <div className="bg-jarvis/5 border border-jarvis/10 rounded-lg px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    <RefreshCwIcon className="size-3 animate-spin text-jarvis/50" />
                    <span className="text-xs font-mono text-jarvis/50">Thinking...</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          {nameSet && (
            <div className="border-t border-jarvis/10 px-6 py-3 shrink-0">
              <div className="flex items-end gap-2">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="전략을 설명하거나 수정 요청을 입력하세요..."
                  rows={1}
                  className="flex-1 resize-none bg-jarvis/5 border border-jarvis/15 rounded-lg px-3 py-2 text-sm font-mono placeholder:text-muted-foreground/40 focus:outline-none focus:border-purple-400/40 min-h-[38px] max-h-[120px]"
                  style={{ height: "auto", overflow: "hidden" }}
                  onInput={(e) => {
                    const t = e.currentTarget;
                    t.style.height = "auto";
                    t.style.height = Math.min(t.scrollHeight, 120) + "px";
                  }}
                />
                <Button
                  onClick={handleSend}
                  disabled={!input.trim() || sending}
                  size="sm"
                  className="bg-purple-400/20 text-purple-400 border border-purple-400/40 hover:bg-purple-400/30 h-[38px] px-3"
                >
                  <SendIcon className="size-4" />
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Strategy preview panel */}
        {nameSet && (
          <div className="w-80 border-l border-jarvis/10 overflow-y-auto shrink-0 hidden lg:block">
            <div className="p-4 space-y-4">
              <div className="flex items-center gap-2">
                <SparklesIcon className="size-3.5 text-purple-400" />
                <span className="text-xs font-mono text-purple-400 tracking-wider font-semibold">LIVE PREVIEW</span>
              </div>

              {!strategyConfig ? (
                <div className="text-center py-8">
                  <p className="text-xs font-mono text-muted-foreground/40">
                    Send your first message to see the strategy preview
                  </p>
                </div>
              ) : (
                <>
                  {/* Judgment */}
                  {judgmentParams && (
                    <div className="space-y-2">
                      <span className="text-xs font-mono text-jarvis/60 tracking-wider">JUDGMENT</span>
                      <div className="grid grid-cols-2 gap-1.5">
                        <div className="bg-jarvis/5 rounded px-2 py-1.5 border border-jarvis/10">
                          <div className="text-xs font-mono text-muted-foreground/50">BB Period</div>
                          <div className="text-sm font-mono text-jarvis font-semibold">{String(judgmentParams.bb_period)}</div>
                        </div>
                        <div className="bg-jarvis/5 rounded px-2 py-1.5 border border-jarvis/10">
                          <div className="text-xs font-mono text-muted-foreground/50">BB Std</div>
                          <div className="text-sm font-mono text-jarvis font-semibold">{String(judgmentParams.bb_std)}</div>
                        </div>
                        <div className="bg-jarvis/5 rounded px-2 py-1.5 border border-jarvis/10">
                          <div className="text-xs font-mono text-muted-foreground/50">RSI Period</div>
                          <div className="text-sm font-mono text-jarvis font-semibold">{String(judgmentParams.rsi_period)}</div>
                        </div>
                        <div className="bg-jarvis/5 rounded px-2 py-1.5 border border-jarvis/10">
                          <div className="text-xs font-mono text-muted-foreground/50">RSI OS/OB</div>
                          <div className="text-sm font-mono text-jarvis font-semibold">{String(judgmentParams.rsi_oversold)}/{String(judgmentParams.rsi_overbought)}</div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Action & Defense */}
                  <div className="grid grid-cols-3 gap-1.5">
                    {actionParams && (
                      <div className="bg-jarvis/5 rounded px-2 py-1.5 border border-jarvis/10">
                        <div className="text-xs font-mono text-muted-foreground/50">Size</div>
                        <div className="text-sm font-mono text-jarvis font-semibold">{String(actionParams.position_size_pct)}%</div>
                      </div>
                    )}
                    {defenseParams && (
                      <>
                        <div className="bg-red-400/5 rounded px-2 py-1.5 border border-red-400/10">
                          <div className="text-xs font-mono text-red-400/50">SL</div>
                          <div className="text-sm font-mono text-red-400 font-semibold">{String(defenseParams.max_loss_pct)}%</div>
                        </div>
                        <div className="bg-emerald-400/5 rounded px-2 py-1.5 border border-emerald-400/10">
                          <div className="text-xs font-mono text-emerald-400/50">TP</div>
                          <div className="text-sm font-mono text-emerald-400 font-semibold">{String(defenseParams.take_profit_pct)}%</div>
                        </div>
                      </>
                    )}
                  </div>

                  {/* Cycle */}
                  {cycleInterval && (
                    <div className="bg-jarvis/5 rounded px-2 py-1.5 border border-jarvis/10">
                      <div className="text-xs font-mono text-muted-foreground/50">Cycle Interval</div>
                      <div className="text-sm font-mono text-jarvis font-semibold">{String(cycleInterval)}s</div>
                    </div>
                  )}

                  {/* Rules */}
                  {rules.length > 0 && (
                    <div className="space-y-2">
                      <span className="text-xs font-mono text-jarvis/60 tracking-wider">전략 룰 ({rules.length})</span>
                      <div className="space-y-1.5">
                        {rules.map((rule, i) => (
                          <div key={i} className="bg-jarvis/5 rounded px-2.5 py-2 border border-jarvis/10 space-y-1">
                            <div className="flex items-center gap-1.5">
                              <RuleIcon type={String(rule.type || "")} />
                              <span className="text-xs font-mono text-jarvis/80 font-semibold uppercase">{String(rule.type || "rule")}</span>
                            </div>
                            <p className="text-xs font-mono text-muted-foreground/70 leading-relaxed">
                              {String(rule.situation || "")}
                            </p>
                            <p className="text-xs font-mono text-foreground/80">
                              → {String(rule.action || "")}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
