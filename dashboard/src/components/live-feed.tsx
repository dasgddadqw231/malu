"use client";

import { useWebSocket } from "@/hooks/use-websocket";
import { Button } from "@/components/ui/button";

export function LiveFeed() {
  const { events, connected, clearEvents } = useWebSocket();

  return (
    <div className="jarvis-card jarvis-corners rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-jarvis/10">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <svg viewBox="0 0 24 24" className="w-4 h-4 text-jarvis/50" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <h3 className="text-xs font-mono font-semibold tracking-[0.15em] text-foreground uppercase">
              Live Stream
            </h3>
          </div>
          <div className="flex items-center gap-1.5">
            <div
              className={`w-1.5 h-1.5 rounded-full ${
                connected ? "bg-emerald-400 status-dot" : "bg-red-500"
              }`}
            />
            <span className="text-xs font-mono text-muted-foreground tracking-wider">
              {connected ? "CONNECTED" : "DISCONNECTED"}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-jarvis/30">
            {events.length} events
          </span>
          {events.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearEvents}
              className="text-xs font-mono text-muted-foreground hover:text-jarvis h-6 px-2 tracking-wider"
            >
              CLEAR
            </Button>
          )}
        </div>
      </div>

      {/* Feed */}
      <div className="px-4 py-2 max-h-72 overflow-y-auto jarvis-scroll">
        {events.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 gap-2">
            <div className="w-8 h-8 rounded-full border border-jarvis/10 flex items-center justify-center">
              <div className="w-2 h-2 rounded-full bg-jarvis/20 jarvis-pulse" />
            </div>
            <p className="text-xs font-mono text-muted-foreground/80 tracking-wider">
              Awaiting data stream...
            </p>
          </div>
        ) : (
          <div className="space-y-0.5">
            {events.map((event, i) => (
              <div
                key={i}
                className="data-row feed-row-interactive flex items-center gap-2 text-xs font-mono py-1.5 px-2 rounded"
              >
                {/* Timestamp dot */}
                <div className="w-1 h-1 rounded-full bg-jarvis/30 shrink-0" />

                {/* Bot ID */}
                <span className="text-jarvis/50 shrink-0 w-16 truncate">
                  {event.bot_id?.slice(0, 8) || "system"}
                </span>

                {/* Separator */}
                <span className="text-jarvis/15">|</span>

                {/* Event type */}
                <span className="text-jarvis/70 shrink-0">{event.event}</span>

                {/* Data */}
                <span className="text-muted-foreground/80 truncate">
                  {Object.entries(event)
                    .filter(([k]) => !["event", "bot_id"].includes(k))
                    .map(([k, v]) => `${k}=${v}`)
                    .join(" ")}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer scan line */}
      <div className="h-[1px] bg-gradient-to-r from-transparent via-jarvis/15 to-transparent" />
    </div>
  );
}
