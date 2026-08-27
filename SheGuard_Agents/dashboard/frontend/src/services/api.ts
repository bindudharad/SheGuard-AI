import type {
  AgentHealth,
  AgentEvent,
  Incident,
  IncidentDetail,
  ResponseRecord,
  X402Status,
  SystemHealth,
  SystemMetrics,
  TestSummary,
  ConnectionState,
  DashboardMode,
} from "../types";

const API_BASE = import.meta.env.VITE_API_BASE || "/api";
const WS_URL = import.meta.env.VITE_WS_URL || "/ws/monitor";
const MODE = (import.meta.env.VITE_DASHBOARD_MODE as DashboardMode) || "live";

let ws: WebSocket | null = null;
const wsListeners = new Map<string, Set<(data: unknown) => void>>();
let wsReconnectTimer: number | null = null;

function wsConnect() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;
  const url = new URL(WS_URL, window.location.origin);
  ws = new WebSocket(url.toString());
  ws.onopen = () => {
    notify("connection", { state: "LIVE" });
  };
  ws.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data);
      const type = msg.event || msg.type || "unknown";
      notify(type, msg.payload);
    } catch {
      // ignore
    }
  };
  ws.onclose = () => {
    notify("connection", { state: "OFFLINE" });
    scheduleReconnect();
  };
  ws.onerror = () => {
    notify("connection", { state: "RECONNECTING" });
  };
}

function scheduleReconnect() {
  if (wsReconnectTimer) return;
  wsReconnectTimer = window.setTimeout(() => {
    wsReconnectTimer = null;
    wsConnect();
  }, 3000);
}

function notify(type: string, payload: unknown) {
  const listeners = wsListeners.get(type);
  if (listeners) {
    listeners.forEach((cb) => cb(payload));
  }
  const all = wsListeners.get("*");
  if (all) all.forEach((cb) => cb({ type, payload }));
}

export const wsService = {
  connect() {
    wsConnect();
  },
  disconnect() {
    if (wsReconnectTimer) {
      clearTimeout(wsReconnectTimer);
      wsReconnectTimer = null;
    }
    if (ws) {
      ws.close();
      ws = null;
    }
  },
  subscribe(type: string, cb: (data: unknown) => void) {
    if (!wsListeners.has(type)) wsListeners.set(type, new Set());
    wsListeners.get(type)!.add(cb);
    return () => {
      wsListeners.get(type)?.delete(cb);
    };
  },
  send(data: unknown) {
    if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify(data));
  },
};

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  wsService,
  get health() {
    return fetchJson<{ status: string; service: string; version: string; agent_system_available: boolean; agents_connected: number; uptime: string }>("/health");
  },
  get agents() {
    return fetchJson<AgentHealth[]>("/agents");
  },
  getAgent(id: string) {
    return fetchJson<AgentHealth>(`/agents/${id}`);
  },
  getAgentMetrics(id: string) {
    return fetchJson<Record<string, unknown>>(`/agents/${id}/metrics`);
  },
  getAgentEvents(id: string, limit = 50) {
    return fetchJson<AgentEvent[]>(`/agents/${id}/events?limit=${limit}`);
  },
  getAgentLogs(id: string, limit = 100) {
    return fetchJson<{ agent_id: string; logs: Array<{ timestamp: string; level: string; message: string }>; note?: string }>(`/agents/${id}/logs?limit=${limit}`);
  },
  controlAgent(id: string, action: string) {
    return fetchJson<{ action: string; status: string; result?: Record<string, unknown> }>(`/agents/${id}/control`, {
      method: "POST",
      body: JSON.stringify({ action }),
    });
  },
  get events() {
    return fetchJson<AgentEvent[]>("/events?limit=200");
  },
  getEvents(params?: { limit?: number; agent?: string; incident_id?: string }) {
    const search = new URLSearchParams();
    if (params?.limit) search.set("limit", String(params.limit));
    if (params?.agent) search.set("agent", params.agent);
    if (params?.incident_id) search.set("incident_id", params.incident_id);
    return fetchJson<AgentEvent[]>(`/events?${search.toString()}`);
  },
  get incidents() {
    return fetchJson<Incident[]>("/incidents");
  },
  getIncident(id: string) {
    return fetchJson<IncidentDetail>(`/incidents/${id}`);
  },
  get responses() {
    return fetchJson<ResponseRecord[]>("/responses");
  },
  get x402() {
    return fetchJson<X402Status>("/x402");
  },
  get systemHealth() {
    return fetchJson<SystemHealth>("/system/health");
  },
  get systemMetrics() {
    return fetchJson<SystemMetrics>("/system/metrics");
  },
  get tests() {
    return fetchJson<TestSummary>("/tests");
  },
  get mode() {
    return MODE;
  },
  get isLive() {
    return MODE === "live";
  },
};
