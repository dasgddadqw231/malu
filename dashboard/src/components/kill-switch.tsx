"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";

export function KillSwitch({ isActive, onKilled }: { isActive: boolean; onKilled: () => void }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleKill = async () => {
    setLoading(true);
    try {
      await api.killAll();
      setOpen(false);
      onKilled();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Kill failed");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await api.resetKillSwitch();
      onKilled();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Reset failed");
    } finally {
      setLoading(false);
    }
  };

  if (isActive) {
    return (
      <Button
        size="lg"
        onClick={handleReset}
        disabled={loading}
        className="font-mono text-xs tracking-[0.15em] uppercase transition-all bg-emerald-500/10 text-emerald-400/80 border border-emerald-500/20 hover:bg-emerald-500/20 hover:text-emerald-400 hover:shadow-[0_0_20px_rgba(50,255,100,0.15)]"
      >
        <span className="flex items-center gap-2">
          {loading ? (
            <div className="w-3 h-3 rounded-full border border-emerald-400 border-t-transparent animate-spin" />
          ) : (
            <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M1 4v6h6" />
              <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
            </svg>
          )}
          RESET KILL SWITCH
        </span>
      </Button>
    );
  }

  return (
    <>
      <Button
        size="lg"
        onClick={() => setOpen(true)}
        className="font-mono text-xs tracking-[0.15em] uppercase transition-all bg-red-500/10 text-red-400/80 border border-red-500/20 hover:bg-red-500/20 hover:text-red-400 hover:shadow-[0_0_20px_rgba(255,50,50,0.15)]"
      >
        <span className="flex items-center gap-2">
          <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18.36 6.64A9 9 0 115.64 18.36 9 9 0 0118.36 6.64z" />
            <line x1="12" y1="2" x2="12" y2="12" />
          </svg>
          KILL ALL
        </span>
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="font-mono text-sm tracking-[0.15em] text-red-400 uppercase">
              Kill All Bots
            </DialogTitle>
            <DialogDescription className="font-mono text-xs">
              All running bots will be force-terminated immediately.
              Open positions will be closed at market price.
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setOpen(false)}
              disabled={loading}
              className="font-mono text-xs tracking-wider"
            >
              CANCEL
            </Button>
            <Button
              onClick={handleKill}
              disabled={loading}
              className="bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30 hover:shadow-[0_0_20px_rgba(255,50,50,0.3)] font-mono text-xs tracking-[0.15em] uppercase transition-all"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full border border-red-400 border-t-transparent animate-spin" />
                  KILLING...
                </span>
              ) : (
                "CONFIRM KILL ALL"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
