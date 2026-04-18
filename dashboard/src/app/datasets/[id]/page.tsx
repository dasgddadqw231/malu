"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api, type ManualDatasetWithTrades, type DiyTrade } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
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
  ZapIcon,
  UploadIcon,
  Trash2Icon,
  PencilIcon,
  SaveIcon,
  XIcon,
} from "lucide-react";

export default function DatasetDetailPage() {
  const params = useParams();
  const dsId = params.id as string;

  const [dataset, setDataset] = useState<ManualDatasetWithTrades | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Edit state
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [editAutoSync, setEditAutoSync] = useState(false);
  const [editSymbol, setEditSymbol] = useState("");

  const loadData = useCallback(async () => {
    try {
      const ds = await api.getDataset(dsId);
      setDataset(ds);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [dsId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const startEditing = () => {
    if (!dataset) return;
    setEditing(true);
    setEditName(dataset.name);
    setEditDesc(dataset.description || "");
    setEditAutoSync(dataset.auto_sync);
    setEditSymbol(dataset.sync_symbol || "");
  };

  const handleSave = async () => {
    try {
      await api.updateDataset(dsId, {
        name: editName,
        description: editDesc || undefined,
        auto_sync: editAutoSync,
        sync_symbol: editSymbol || undefined,
      });
      setEditing(false);
      await loadData();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Update failed");
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      const result = await api.syncDataset(dsId);
      alert(`Synced ${result.synced} trades, ${result.added_to_dataset} new added`);
      await loadData();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const result = await api.uploadDatasetCsv(dsId, file);
      alert(`Uploaded ${result.uploaded} trades, ${result.added_to_dataset} added`);
      await loadData();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleRemoveTrade = async (tradeId: string) => {
    try {
      await api.updateDataset(dsId, { remove_trade_ids: [tradeId] });
      await loadData();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Remove failed");
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <div className="arc-spinner" />
        <p className="text-sm font-mono text-jarvis/60 tracking-widest uppercase">Loading Dataset...</p>
      </div>
    );
  }

  if (!dataset) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-6">
        <p className="text-muted-foreground font-mono">Dataset not found</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-6">
      {/* Header */}
      <header className="flex items-end justify-between mb-8">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Link href="/datasets" className="text-jarvis/50 hover:text-jarvis transition-colors">
              <ArrowLeftIcon className="size-5" />
            </Link>
            {editing ? (
              <Input
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="text-2xl font-bold font-mono text-jarvis bg-transparent border-jarvis/20 h-auto py-0.5 w-64"
              />
            ) : (
              <h1 className="text-3xl font-bold tracking-[0.2em] font-mono text-jarvis text-glow">
                {dataset.name}
              </h1>
            )}
            <div className="h-[1px] w-16 bg-gradient-to-r from-jarvis/60 to-transparent" />
          </div>
          {editing ? (
            <Input
              value={editDesc}
              onChange={(e) => setEditDesc(e.target.value)}
              placeholder="Description"
              className="text-xs font-mono text-muted-foreground bg-transparent border-jarvis/15 mt-1 w-80"
            />
          ) : (
            <p className="text-xs font-mono text-muted-foreground tracking-[0.15em] uppercase">
              {dataset.description || `${dataset.trade_ids.length} trades`}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {editing ? (
            <>
              <label className="flex items-center gap-2 text-xs font-mono text-muted-foreground cursor-pointer mr-3">
                <input
                  type="checkbox"
                  checked={editAutoSync}
                  onChange={(e) => setEditAutoSync(e.target.checked)}
                  className="accent-[var(--color-jarvis)]"
                />
                Auto-sync
              </label>
              {editAutoSync && (
                <Input
                  value={editSymbol}
                  onChange={(e) => setEditSymbol(e.target.value)}
                  placeholder="Symbol (all)"
                  className="w-32 font-mono text-xs"
                />
              )}
              <Button variant="ghost" size="sm" onClick={() => setEditing(false)} className="font-mono text-xs">
                <XIcon className="size-3 mr-1" /> CANCEL
              </Button>
              <Button size="sm" onClick={handleSave} className="bg-jarvis/20 text-jarvis border border-jarvis/40 hover:bg-jarvis/30 font-mono text-xs">
                <SaveIcon className="size-3 mr-1" /> SAVE
              </Button>
            </>
          ) : (
            <>
              {dataset.auto_sync && (
                <Badge variant="outline" className="text-xs font-mono border-emerald-400/30 text-emerald-400/70 mr-1">
                  <ZapIcon className="size-2.5 mr-0.5" /> AUTO-SYNC
                  {dataset.sync_symbol && ` (${dataset.sync_symbol})`}
                </Badge>
              )}
              <Button variant="ghost" size="sm" onClick={startEditing} className="font-mono text-xs text-jarvis/60">
                <PencilIcon className="size-3 mr-1" /> EDIT
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleSync}
                disabled={syncing}
                className="font-mono text-xs text-jarvis/60"
              >
                {syncing ? <RefreshCwIcon className="size-3 mr-1 animate-spin" /> : <RefreshCwIcon className="size-3 mr-1" />}
                SYNC
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="font-mono text-xs text-jarvis/60"
              >
                {uploading ? <RefreshCwIcon className="size-3 mr-1 animate-spin" /> : <UploadIcon className="size-3 mr-1" />}
                CSV
              </Button>
              <input ref={fileInputRef} type="file" accept=".csv" onChange={handleUpload} className="hidden" />
            </>
          )}
        </div>
      </header>

      {/* Trades table */}
      {dataset.trades.length === 0 ? (
        <div className="jarvis-card rounded-lg text-center py-12">
          <p className="text-muted-foreground text-sm font-mono mb-2">No trades in this dataset</p>
          <p className="text-xs text-muted-foreground/80 font-mono">
            SYNC를 눌러 Bybit에서 가져오거나 CSV를 업로드하세요
          </p>
        </div>
      ) : (
        <div className="jarvis-card rounded-lg border border-jarvis/10 overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="border-jarvis/10">
                <TableHead className="text-xs font-mono text-jarvis/60 tracking-wider">SYMBOL</TableHead>
                <TableHead className="text-xs font-mono text-jarvis/60 tracking-wider">SIDE</TableHead>
                <TableHead className="text-xs font-mono text-jarvis/60 tracking-wider">QTY</TableHead>
                <TableHead className="text-xs font-mono text-jarvis/60 tracking-wider">PRICE</TableHead>
                <TableHead className="text-xs font-mono text-jarvis/60 tracking-wider">PNL</TableHead>
                <TableHead className="text-xs font-mono text-jarvis/60 tracking-wider">TIME</TableHead>
                <TableHead className="text-xs font-mono text-jarvis/60 tracking-wider">TAGS</TableHead>
                <TableHead className="w-10"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {dataset.trades.map((trade: DiyTrade) => {
                const pnl = trade.pnl ? Number(trade.pnl) : null;
                return (
                  <TableRow key={trade.id} className="border-jarvis/5">
                    <TableCell className="font-mono text-xs">{trade.symbol.replace("USDT", "")}</TableCell>
                    <TableCell>
                      <span className={`font-mono text-xs font-semibold ${trade.side === "Buy" ? "text-emerald-400" : "text-red-400"}`}>
                        {trade.side.toUpperCase()}
                      </span>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">{Number(trade.qty).toFixed(4)}</TableCell>
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
                            month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
                          })
                        : "-"}
                    </TableCell>
                    <TableCell>
                      {trade.tags.length > 0 && (
                        <div className="flex gap-1 flex-wrap">
                          {trade.tags.map((tag) => (
                            <Badge key={tag} variant="outline" className="text-xs font-mono border-jarvis/20 text-jarvis/70">
                              {tag}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </TableCell>
                    <TableCell>
                      <button
                        onClick={() => handleRemoveTrade(trade.id)}
                        className="text-red-400/30 hover:text-red-400 transition-colors"
                        title="Remove from dataset"
                      >
                        <Trash2Icon className="size-3" />
                      </button>
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
