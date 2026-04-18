"use client";

import { useEffect, useRef, useState, useCallback } from "react";

interface BotEvent {
  event: string;
  bot_id?: string;
  [key: string]: unknown;
}

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/live";

// Shared singleton connection — all hooks share one WebSocket
type Listener = (event: BotEvent) => void;
let sharedWs: WebSocket | null = null;
let sharedReconnect: NodeJS.Timeout | null = null;
const listeners = new Set<Listener>();
const statusListeners = new Set<(connected: boolean) => void>();
let isConnected = false;

function ensureConnection() {
  if (sharedWs?.readyState === WebSocket.OPEN) return;

  const ws = new WebSocket(WS_URL);
  sharedWs = ws;

  ws.onopen = () => {
    isConnected = true;
    statusListeners.forEach((l) => l(true));
    if (sharedReconnect) {
      clearTimeout(sharedReconnect);
      sharedReconnect = null;
    }
  };

  ws.onmessage = (e) => {
    try {
      const event: BotEvent = JSON.parse(e.data);
      if (event.event === "pong") return;
      listeners.forEach((l) => l(event));
    } catch {}
  };

  ws.onclose = () => {
    isConnected = false;
    statusListeners.forEach((l) => l(false));
    sharedReconnect = setTimeout(ensureConnection, 3000);
  };

  ws.onerror = () => ws.close();
}

/**
 * Subscribe to WebSocket events.
 * @param botId — if provided, only events for this bot are included
 * @param maxEvents — max events to keep (default 100)
 */
export function useWebSocket(botId?: string, maxEvents = 100) {
  const [events, setEvents] = useState<BotEvent[]>([]);
  const [connected, setConnected] = useState(isConnected);

  useEffect(() => {
    ensureConnection();

    const onEvent: Listener = (event) => {
      if (botId && event.bot_id !== botId) return;
      setEvents((prev) => [event, ...prev].slice(0, maxEvents));
    };
    const onStatus = (c: boolean) => setConnected(c);

    listeners.add(onEvent);
    statusListeners.add(onStatus);

    return () => {
      listeners.delete(onEvent);
      statusListeners.delete(onStatus);
    };
  }, [botId, maxEvents]);

  const clearEvents = useCallback(() => setEvents([]), []);

  return { events, connected, clearEvents };
}
