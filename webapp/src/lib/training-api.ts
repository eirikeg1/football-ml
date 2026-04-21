/** API client and WebSocket manager for the training server. */

import type { TrainingConfig, WSMessage } from "./training-types";

const API_BASE = "/api";

export async function startTraining(
  pipelineYaml: string,
  config: TrainingConfig
): Promise<{ status: string; run_id?: string; message?: string }> {
  const res = await fetch(`${API_BASE}/train`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      pipeline_yaml: pipelineYaml,
      training_config: config,
    }),
  });
  return res.json();
}

export async function stopTraining(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/train/stop`, { method: "POST" });
  return res.json();
}

export async function pauseTraining(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/train/pause`, { method: "POST" });
  return res.json();
}

export async function getStatus(): Promise<{
  status: string;
  epoch: number;
  total_epochs: number;
}> {
  const res = await fetch(`${API_BASE}/status`);
  return res.json();
}

export async function fetchLossOptions(): Promise<
  Record<string, { default: string; options: string[] }>
> {
  const res = await fetch(`${API_BASE}/heads/losses`);
  return res.json();
}

export async function fetchMetricOptions(): Promise<
  Record<string, string[]>
> {
  const res = await fetch(`${API_BASE}/heads/metrics`);
  return res.json();
}

// ── WebSocket manager ──────────────────────────────────────────────

let _ws: WebSocket | null = null;
let _reconnectTimer: ReturnType<typeof setTimeout> | null = null;

export function connectWebSocket(
  onMessage: (msg: WSMessage) => void,
  onConnect?: () => void,
  onDisconnect?: () => void
): void {
  if (_ws && _ws.readyState === WebSocket.OPEN) return;

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const url = `${protocol}//${window.location.host}/ws/training`;

  _ws = new WebSocket(url);

  _ws.onopen = () => {
    onConnect?.();
  };

  _ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data) as WSMessage;
      onMessage(msg);
    } catch {
      // ignore malformed messages
    }
  };

  _ws.onclose = () => {
    onDisconnect?.();
    // Auto-reconnect after 3 seconds
    _reconnectTimer = setTimeout(() => {
      connectWebSocket(onMessage, onConnect, onDisconnect);
    }, 3000);
  };

  _ws.onerror = () => {
    _ws?.close();
  };
}

export function disconnectWebSocket(): void {
  if (_reconnectTimer) {
    clearTimeout(_reconnectTimer);
    _reconnectTimer = null;
  }
  if (_ws) {
    _ws.onclose = null; // prevent auto-reconnect
    _ws.close();
    _ws = null;
  }
}
