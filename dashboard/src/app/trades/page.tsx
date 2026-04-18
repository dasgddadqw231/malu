"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, type DiyTrade } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
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
import {
  ArrowLeftIcon,
  RefreshCwIcon,
  XIcon,
  FolderPlusIcon,
  DatabaseIcon,
} from "lucide-react";

export default function TradesPage() {
  const router = useRouter();
  const [trades, setTrades] = useState<DiyTrade[]>([]);
  const [syncing, setSyncing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editRationale, setEditRationale] = useState("");
  const [editTags, setEditTags] = useState("");
  const [symbolFilter, setSymbolFilter] = useState("all");

  // Dataset creation
  const [showDatasetForm, setShowDatasetForm] = useState(false);
  const [dsName, setDsName] = useState("");
  const [dsDesc, setDsDesc] = useState("");
  const [dsAutoSync, setDsAutoSync] = useState(false);
  const [dsCreating, setDsCreating] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const t = await api.listDiyTrades();
      setTrades(t);
    } catch {
      // silently fail on initial load
    } finally {
      setLoading(false);
    }
  }, []);

  const symbols = [...new Set(trades.map((t) => t.symbol))].sort();
  const filteredTrades = symbolFilter === "all" ? trades : trades.filter((t) => t.symbol === symbolFilter);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const result = await api.syncDiyTrades(symbolFilter !== "all" ? symbolFilter : undefined);
      alert(`${result.synced} trades synced from Bybit`);
      await loadData();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  const handleSaveAnnotation = async (tradeId: string) => {
    try {
      const tags = editTags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      await api.updateDiyTrade(tradeId, {
        rationale: editRationale,
        tags: tags.length > 0 ? tags : undefined,
      });
      setEditingId(null);
      await loadData();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Save failed");
    }
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleCreateDataset = async () => {
    if (!dsName || selectedIds.size === 0) return;
    setDsCreating(true);
    try {
      const ds = await api.createDataset({
        name: dsName,
        description: dsDesc || undefined,
        trade_ids: Array.from(selectedIds),
        auto_sync: dsAutoSync,
        sync_symbol: symbolFilter !== "all" ? symbolFilter : undefined,
      });
      setSelectedIds(new Set());
      setDsName("");
      setDsDesc("");
      setDsAutoSync(false);
      setShowDatasetForm(false);
      router.push(`/datasets/${ds.id}`);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Dataset creation failed");
    } finally {
      setDsCreating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <div className="arc-spinner" />
        <p className="text-sm font-mono text-jarvis/60 tracking-widest uppercase">
          Loading Trade History...
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
              TRADES
            </h1>
            <div className="h-[1px] w-16 bg-gradient-to-r from-jarvis/60 to-transparent" />
          </div>
          <p className="text-xs font-mono text-muted-foreground tracking-[0.15em] uppercase">
            Your manual trade history from Bybit
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/datasets">
            <Button variant="ghost" className="font-mono text-xs text-jarvis/60 hover:text-jarvis">
              <DatabaseIcon className="size-3 mr-1.5" />
              DATASETS
            </Button>
          </Link>
          <Select value={symbolFilter} onValueChange={(v) => setSymbolFilter(v ?? "all")}>
            <SelectTrigger className="w-40 font-mono text-xs bg-jarvis/5 border-jarvis/15">
              <SelectValue placeholder="All symbols" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all" className="font-mono text-xs">ALL SYMBOLS</SelectItem>
              {symbols.map((s) => (
                <SelectItem key={s} value={s} className="font-mono text-xs">
                  {s.replace("USDT", "")}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            onClick={handleSync}
            disabled={syncing}
            className="bg-jarvis/10 text-jarvis border border-jarvis/30 hover:bg-jarvis/20 font-mono text-xs tracking-wider"
          >
            {syncing ? (
              <span className="flex items-center gap-2">
                <RefreshCwIcon className="size-3 animate-spin" />
                SYNCING...
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <RefreshCwIcon className="size-3" />
                SYNC TRADES
              </span>
            )}
          </Button>
        </div>
      </header>

      {/* Dataset creation bar */}
      {selectedIds.size > 0 && (
        <div className="jarvis-card rounded-lg p-4 mb-4 border border-jarvis/20 space-y-3">
          <div className="flex items-center gap-3">
            <FolderPlusIcon className="size-4 text-jarvis" />
            <span className="text-xs font-mono text-jarvis">
              {selectedIds.size} trades selected
            </span>
            <div className="flex-1" />
            {!showDatasetForm ? (
              <>
                <Button
                  onClick={() => setShowDatasetForm(true)}
                  className="bg-jarvis/20 text-jarvis border border-jarvis/40 hover:bg-jarvis/30 font-mono text-xs tracking-wider"
                >
                  <FolderPlusIcon className="size-3 mr-1.5" />
                  CREATE DATASET
                </Button>
                <button
                  onClick={() => setSelectedIds(new Set())}
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  <XIcon className="size-4" />
                </button>
              </>
            ) : (
              <button
                onClick={() => setShowDatasetForm(false)}
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                <XIcon className="size-4" />
              </button>
            )}
          </div>

          {showDatasetForm && (
            <div className="space-y-3 p-3 rounded border border-jarvis/15 bg-jarvis/5">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-mono text-muted-foreground">Dataset Name</label>
                  <Input
                    placeholder="예: BTC 스캘핑 데이터"
                    value={dsName}
                    onChange={(e) => setDsName(e.target.value)}
                    className="font-mono text-xs bg-jarvis/5 border-jarvis/15"
                  />
                </div>
                <div>
                  <label className="text-xs font-mono text-muted-foreground">Description (optional)</label>
                  <Input
                    placeholder="데이터셋 설명"
                    value={dsDesc}
                    onChange={(e) => setDsDesc(e.target.value)}
                    className="font-mono text-xs bg-jarvis/5 border-jarvis/15"
                  />
                </div>
              </div>
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 text-xs font-mono text-muted-foreground cursor-pointer">
                  <input
                    type="checkbox"
                    checked={dsAutoSync}
                    onChange={(e) => setDsAutoSync(e.target.checked)}
                    className="accent-[var(--color-jarvis)]"
                  />
                  Auto-sync new trades from Bybit
                  {symbolFilter !== "all" && dsAutoSync && (
                    <Badge variant="outline" className="text-xs font-mono border-jarvis/20 text-jarvis/60">
                      {symbolFilter}
                    </Badge>
                  )}
                </label>
                <div className="flex gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowDatasetForm(false)}
                    className="font-mono text-xs"
                  >
                    CANCEL
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleCreateDataset}
                    disabled={dsCreating || !dsName}
                    className="bg-jarvis/20 text-jarvis border border-jarvis/40 hover:bg-jarvis/30 font-mono text-xs"
                  >
                    {dsCreating ? (
                      <span className="flex items-center gap-1">
                        <RefreshCwIcon className="size-3 animate-spin" /> CREATING...
                      </span>
                    ) : (
                      "CREATE"
                    )}
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {filteredTrades.length === 0 ? (
        <div className="jarvis-card rounded-lg text-center py-16">
          <p className="text-muted-foreground text-sm font-mono mb-2">
            No human trades found
          </p>
          <p className="text-xs text-muted-foreground/80 font-mono">
            Click SYNC TRADES to import your manual trades from Bybit
          </p>
        </div>
      ) : (
        <div className="jarvis-card rounded-lg border border-jarvis/10 overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="border-jarvis/10">
                <TableHead className="w-10 text-xs font-mono text-jarvis/60 tracking-wider">
                  <input
                    type="checkbox"
                    checked={filteredTrades.length > 0 && filteredTrades.every((t) => selectedIds.has(t.id))}
                    onChange={() => {
                      const allSelected = filteredTrades.every((t) => selectedIds.has(t.id));
                      if (allSelected) {
                        setSelectedIds(new Set());
                      } else {
                        setSelectedIds(new Set(filteredTrades.map((t) => t.id)));
                      }
                    }}
                    className="accent-[var(--color-jarvis)]"
                  />
                </TableHead>
                <TableHead className="text-xs font-mono text-jarvis/60 tracking-wider">SYMBOL</TableHead>
                <TableHead className="text-xs font-mono text-jarvis/60 tracking-wider">SIDE</TableHead>
                <TableHead className="text-xs font-mono text-jarvis/60 tracking-wider">QTY</TableHead>
                <TableHead className="text-xs font-mono text-jarvis/60 tracking-wider">PRICE</TableHead>
                <TableHead className="text-xs font-mono text-jarvis/60 tracking-wider">PNL</TableHead>
                <TableHead className="text-xs font-mono text-jarvis/60 tracking-wider">TIME</TableHead>
                <TableHead className="text-xs font-mono text-jarvis/60 tracking-wider">RATIONALE / TAGS</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredTrades.map((trade) => {
                const isEditing = editingId === trade.id;
                const pnl = trade.pnl ? Number(trade.pnl) : null;
                return (
                  <TableRow
                    key={trade.id}
                    className={`border-jarvis/5 ${selectedIds.has(trade.id) ? "bg-jarvis/10" : ""}`}
                  >
                    <TableCell>
                      <input
                        type="checkbox"
                        checked={selectedIds.has(trade.id)}
                        onChange={() => toggleSelect(trade.id)}
                        className="accent-[var(--color-jarvis)]"
                      />
                    </TableCell>
                    <TableCell className="font-mono text-xs">{trade.symbol.replace("USDT", "")}</TableCell>
                    <TableCell>
                      <span className={`font-mono text-xs font-semibold ${trade.side === "Buy" ? "text-emerald-400" : "text-red-400"}`}>
                        {trade.side.toUpperCase()}
                      </span>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {Number(trade.qty).toFixed(4)}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {trade.avg_price ? `$${Number(trade.avg_price).toLocaleString()}` : "-"}
                    </TableCell>
                    <TableCell>
                      {pnl !== null ? (
                        <span className={`font-mono text-xs ${pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                          {pnl >= 0 ? "+" : ""}{pnl.toFixed(4)}
                        </span>
                      ) : (
                        <span className="font-mono text-xs text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {trade.filled_at
                        ? new Date(trade.filled_at).toLocaleString("ko-KR", {
                            month: "2-digit",
                            day: "2-digit",
                            hour: "2-digit",
                            minute: "2-digit",
                            second: "2-digit",
                          })
                        : "-"}
                    </TableCell>
                    <TableCell
                      className={isEditing ? "" : "cursor-pointer group/cell"}
                      onClick={() => {
                        if (!isEditing) {
                          setEditingId(trade.id);
                          setEditRationale(trade.rationale || "");
                          setEditTags(trade.tags.join(", "));
                        }
                      }}
                    >
                      {isEditing ? (
                        <div className="flex flex-col gap-1 min-w-[200px]" onClick={(e) => e.stopPropagation()}>
                          <Textarea
                            autoFocus
                            value={editRationale}
                            onChange={(e) => setEditRationale(e.target.value)}
                            placeholder="Why did you make this trade?"
                            className="text-xs font-mono min-h-[60px] bg-jarvis/5 border-jarvis/15"
                          />
                          <Input
                            value={editTags}
                            onChange={(e) => setEditTags(e.target.value)}
                            placeholder="Tags (comma separated)"
                            className="text-xs font-mono bg-jarvis/5 border-jarvis/15"
                          />
                          <div className="flex gap-2 mt-1">
                            <Button
                              onClick={() => handleSaveAnnotation(trade.id)}
                              className="h-6 px-3 bg-jarvis/20 text-jarvis border border-jarvis/30 hover:bg-jarvis/30 font-mono text-xs tracking-wider"
                            >
                              SAVE
                            </Button>
                            <button
                              onClick={() => setEditingId(null)}
                              className="text-xs font-mono text-muted-foreground hover:text-foreground transition-colors tracking-wider"
                            >
                              ESC
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="flex flex-col gap-1 max-w-[250px]">
                          {trade.rationale && (
                            <p className="text-xs font-mono text-muted-foreground truncate group-hover/cell:text-jarvis/70 transition-colors">
                              {trade.rationale}
                            </p>
                          )}
                          {trade.tags.length > 0 && (
                            <div className="flex gap-1 flex-wrap">
                              {trade.tags.map((tag) => (
                                <Badge key={tag} variant="outline" className="text-xs font-mono border-jarvis/20 text-jarvis/70">
                                  {tag}
                                </Badge>
                              ))}
                            </div>
                          )}
                          {!trade.rationale && trade.tags.length === 0 && (
                            <span className="text-xs font-mono text-muted-foreground/80 group-hover/cell:text-jarvis/50 transition-colors">
                              Click to add...
                            </span>
                          )}
                        </div>
                      )}
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
