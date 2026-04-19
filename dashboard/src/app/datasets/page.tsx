"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { api, type ManualDataset } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeftIcon,
  RefreshCwIcon,
  DatabaseIcon,
  FolderOpenIcon,
  Trash2Icon,
  ZapIcon,
} from "lucide-react";
import { BootSound } from "@/components/click-effects";

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<ManualDataset[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    try {
      const ds = await api.listDatasets();
      setDatasets(ds);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleDelete = async (id: string) => {
    try {
      await api.deleteDataset(id);
      setDatasets((prev) => prev.filter((d) => d.id !== id));
    } catch (e) {
      alert(e instanceof Error ? e.message : "Delete failed");
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <BootSound />
        <div className="arc-spinner" />
        <p className="text-sm font-mono text-jarvis/60 tracking-widest uppercase">Loading Datasets...</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-6">
      <header className="flex items-end justify-between mb-8">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Link href="/trades" className="text-jarvis/50 hover:text-jarvis transition-colors">
              <ArrowLeftIcon className="size-5" />
            </Link>
            <h1 className="text-3xl font-bold tracking-[0.2em] font-mono text-jarvis text-glow">
              DATASETS
            </h1>
            <div className="h-[1px] w-16 bg-gradient-to-r from-jarvis/60 to-transparent" />
          </div>
          <p className="text-xs font-mono text-muted-foreground tracking-[0.15em] uppercase">
            Curated trade collections for signature training
          </p>
        </div>
        <Button variant="ghost" size="sm" onClick={loadData} className="font-mono text-xs text-jarvis/60">
          <RefreshCwIcon className="size-3 mr-1" /> REFRESH
        </Button>
      </header>

      {datasets.length === 0 ? (
        <div className="jarvis-card rounded-lg text-center py-16">
          <DatabaseIcon className="size-8 text-jarvis/20 mx-auto mb-3" />
          <p className="text-muted-foreground text-sm font-mono mb-2">No datasets yet</p>
          <p className="text-xs text-muted-foreground/80 font-mono mb-6">
            Trades 페이지에서 매매 내역을 선택하고 데이터셋을 만들어보세요
          </p>
          <Link href="/trades">
            <Button variant="outline" className="font-mono text-xs border-jarvis/30 text-jarvis/70 hover:bg-jarvis/10">
              GO TO TRADES
            </Button>
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {datasets.map((ds) => (
            <div
              key={ds.id}
              className="jarvis-card jarvis-corners rounded-lg p-5 border border-jarvis/15 space-y-3"
            >
              <div className="flex items-center justify-between">
                <h3 className="font-mono text-sm font-semibold text-jarvis tracking-wider">
                  {ds.name}
                </h3>
                <div className="flex items-center gap-1.5">
                  {ds.auto_sync && (
                    <Badge variant="outline" className="text-xs font-mono border-emerald-400/30 text-emerald-400/70">
                      <ZapIcon className="size-2.5 mr-0.5" />
                      AUTO
                    </Badge>
                  )}
                  <Badge variant="outline" className="text-xs font-mono border-jarvis/20 text-jarvis/50">
                    {ds.trade_ids.length} trades
                  </Badge>
                </div>
              </div>

              {ds.description && (
                <p className="text-xs font-mono text-muted-foreground line-clamp-2">{ds.description}</p>
              )}

              {ds.sync_symbol && (
                <p className="text-xs font-mono text-muted-foreground/60">
                  Symbol: {ds.sync_symbol}
                </p>
              )}

              <p className="text-xs font-mono text-muted-foreground/40">
                {new Date(ds.created_at).toLocaleDateString("ko-KR")}
              </p>

              <div className="flex justify-between items-center pt-2 border-t border-jarvis/10">
                <Link
                  href={`/datasets/${ds.id}`}
                  className="text-xs font-mono text-jarvis/50 hover:text-jarvis transition-colors tracking-wider flex items-center gap-1"
                >
                  <FolderOpenIcon className="size-3" /> OPEN
                </Link>
                <button
                  onClick={() => handleDelete(ds.id)}
                  className="text-xs font-mono text-red-400/50 hover:text-red-400 transition-colors tracking-wider flex items-center gap-1"
                >
                  <Trash2Icon className="size-3" /> DELETE
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
