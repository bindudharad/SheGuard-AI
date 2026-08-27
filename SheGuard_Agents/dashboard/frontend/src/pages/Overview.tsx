import * as React from "react";
import { useEffect, useState } from "react";
import { AgentCard } from "../components/AgentCard";
import { StatusBadge } from "../components/StatusBadge";
import { AgentNetworkScene } from "../components/three/AgentNetworkScene";
import { api } from "../services/api";
import type { AgentHealth, SystemHealth, SystemMetrics } from "../types";
import { PIPELINE_ORDER, AGENT_DEFINITIONS, type AgentId } from "../utils/agents";

export function Overview() {
  const [agents, setAgents] = useState<Record<string, AgentHealth>>({});
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<AgentId | null>(null);
  const [recentEvents, setRecentEvents] = useState<any[]>([]);

  useEffect(() => {
    let mounted = true;
    const unsub = api.wsService.subscribe("system.metrics", (data) => {
      if (mounted && data) {
        setSystemMetrics(data as SystemMetrics);
      }
    });
    const unsubEvents = api.wsService.subscribe("*", (data: any) => {
      if (mounted && data && data.type) {
        setRecentEvents((prev) => [data.payload, ...prev].slice(0, 50));
      }
    });
    const unsubConn = api.wsService.subscribe("connection", (data: any) => {
      if (mounted) setConnected(data?.state === "LIVE");
    });

    async function fetchData() {
      try {
        const [agentsRes, healthRes, metricsRes] = await Promise.all([
          api.agents,
          api.systemHealth,
          api.systemMetrics,
        ]);
        if (mounted) {
          const agentMap: Record<string, AgentHealth> = {};
          agentsRes.forEach((a) => (agentMap[a.agent_id] = a));
          setAgents(agentMap);
          setSystemHealth(healthRes);
          setSystemMetrics(metricsRes);
          setLoading(false);
        }
      } catch (e) {
        if (mounted) {
          setError(e instanceof Error ? e.message : "Failed to load data");
          setLoading(false);
        }
      }
    }

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => { mounted = false; clearInterval(interval); unsub(); unsubEvents(); unsubConn(); };
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => <div key={i} className="h-28 bg-bg-card rounded-xl animate-pulse" />)}
        </div>
        <div className="h-96 bg-bg-card rounded-2xl animate-pulse" />
      </div>
    );
  }

  if (error) {
    return <div className="p-8 text-center text-red-400">{error}</div>;
  }

  const healthyCount = Object.values(agents).filter((a) => a.status === "HEALTHY").length;
  const degradedCount = Object.values(agents).filter((a) => a.status === "DEGRADED").length;
  const offlineCount = Object.values(agents).filter((a) => a.status === "OFFLINE").length;
  const totalEvents = Object.values(agents).reduce((sum, a) => sum + (a.events_processed || 0), 0);
  const totalErrors = Object.values(agents).reduce((sum, a) => sum + (a.error_count || 0), 0);
  const avgLatency = Object.values(agents).reduce((sum, a) => sum + (a.latency || 0), 0) / Math.max(1, Object.keys(agents).length);
  const uptime = systemMetrics?.uptime || "0h 0m";
  const activeIncidents = systemMetrics?.active_incidents || 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Overview</h1>
          <p className="text-sm text-slate-500">SheGuard AI+ Agent Operations Center</p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`flex items-center gap-1.5 text-sm ${connected ? "text-green-400" : "text-red-400"}`}>
            <span className={`w-2 h-2 rounded-full ${connected ? "bg-green-400" : "bg-red-400"}`} />
            {connected ? "LIVE" : "OFFLINE"}
          </span>
          <span className="text-xs text-slate-500">Last updated: {new Date().toLocaleTimeString()}</span>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard label="Total Agents" value={Object.keys(agents).length} icon="🤖" color="#3b82f6" />
        <SummaryCard label="Healthy" value={healthyCount} icon="✓" color="#22c55e" />
        <SummaryCard label="Degraded" value={degradedCount} icon="⚠" color="#f59e0b" />
        <SummaryCard label="Offline" value={offlineCount} icon="✕" color="#ef4444" />
        <SummaryCard label="Active Incidents" value={activeIncidents} icon="🚨" color="#ef4444" />
        <SummaryCard label="Events/sec" value={systemMetrics?.events_per_second?.toFixed(1) || "0.0"} icon="📊" color="#06b6d4" />
        <SummaryCard label="Avg Latency" value={`${avgLatency.toFixed(1)}ms`} icon="⏱" color="#8b5cf6" />
        <SummaryCard label="System Uptime" value={uptime} icon="⏰" color="#ec4899" />
      </div>

      {/* 3D Agent Network */}
      <section className="bg-bg-card rounded-2xl border border-slate-800/50 overflow-hidden" style={{ boxShadow: "0 8px 32px rgba(0,0,0,0.4)" }}>
        <div className="p-4 border-b border-slate-800/50 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Agent Network Topology</h2>
          <span className="text-xs text-slate-500">Click nodes for details • Drag to rotate • Scroll to zoom</span>
        </div>
        <div style={{ height: 400 }}>
          <AgentNetworkScene
            agentsHealth={agents}
            selectedAgent={selectedAgent}
            onSelectAgent={setSelectedAgent}
            recentEvents={recentEvents}
          />
        </div>
      </section>

      {/* Agent Health Cards */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Agent Health</h2>
          <StatusBadge status={systemHealth?.overall_status ?? "UNKNOWN"} size="md" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {PIPELINE_ORDER.map((id) => (
            <AgentCard key={id} agentId={id} health={agents[id] ?? { ...emptyHealth(id), status: "OFFLINE" }} />
          ))}
        </div>
      </section>

      {/* System Components */}
      {systemHealth && (
        <section>
          <h2 className="text-lg font-semibold mb-4">System Components</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {Object.entries({
              "Event Bus": systemHealth.event_bus,
              Backend: systemHealth.backend,
              Database: systemHealth.database,
              Storage: systemHealth.storage,
              Camera: systemHealth.camera,
              Microphone: systemHealth.microphone,
              Network: systemHealth.network,
              Telegram: systemHealth.telegram,
              x402: systemHealth.x402,
            }).map(([name, comp]) => (
              <ComponentStatusCard key={name} name={name} component={comp as any} />
            ))}
          </div>
        </section>
      )}

      {/* Live Event Stream Preview */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Recent Events</h2>
          <a href="/events" className="text-sm text-sky-400 hover:text-sky-300">View All →</a>
        </div>
        <div className="bg-bg-card rounded-2xl border border-slate-800/50 p-4 max-h-64 overflow-y-auto">
          {/* Events would be loaded from WebSocket or API */}
          <p className="text-slate-500 text-sm text-center py-8">Events stream available on Events page</p>
        </div>
      </section>
    </div>
  );
}

function SummaryCard({ label, value, icon, color }: { label: string; value: string | number; icon: string; color: string }) {
  return (
    <div className="p-5 bg-bg-card rounded-xl border border-slate-800/50 relative overflow-hidden" style={{ boxShadow: "0 4px 24px rgba(0,0,0,0.3)" }}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">{label}</p>
          <p className="text-2xl font-bold font-mono text-slate-100">{value}</p>
        </div>
        <div
          className="w-12 h-12 rounded-xl flex items-center justify-center text-xl"
          style={{ background: `linear-gradient(135deg, ${color}20, ${color}10)`, border: `1px solid ${color}40` }}
        >
          {icon}
        </div>
      </div>
    </div>
  );
}

function ComponentStatusCard({ name, component }: { name: string; component: { status: string; last_check?: string; note?: string; subscribed_events?: number } }) {
  const getColor = (s: string) => {
    if (s === "HEALTHY") return "text-green-400 bg-green-500/20 border-green-500/30";
    if (s === "DEGRADED") return "text-amber-400 bg-amber-500/20 border-amber-500/30";
    if (s === "OFFLINE") return "text-slate-500 bg-slate-500/20 border-slate-500/30";
    return "text-slate-400 bg-slate-500/20 border-slate-500/30";
  };
  const colorClass = getColor(component.status);

  return (
    <div className={`p-4 rounded-xl border ${colorClass}`}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-medium text-slate-100">{name}</h3>
        <StatusBadge status={component.status} size="sm" />
      </div>
      <p className="text-xs text-slate-500">{component.note || `Last check: ${component.last_check ? new Date(component.last_check).toLocaleTimeString() : "—"}`}</p>
      {component.subscribed_events !== undefined && <p className="text-xs text-slate-500 mt-1">Subscribed events: {component.subscribed_events}</p>}
    </div>
  );
}

function emptyHealth(id: string): AgentHealth {
  const def = AGENT_DEFINITIONS[id as AgentId];
  return {
    agent_id: id,
    name: def?.name || id,
    status: "OFFLINE",
    uptime: "0h 0m",
    latency: 0,
    cpu: 0,
    memory: 0,
    events_processed: 0,
    error_count: 0,
    warning_count: 0,
    current_state: "OFFLINE",
    version: "1.0.0",
  };
}
