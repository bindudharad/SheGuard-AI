import * as React from "react";
import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { SystemHealth } from "../types";
import { StatusBadge } from "../components/StatusBadge";

interface ComponentHealth {
  status: string;
  last_check?: string;
  note?: string;
  subscribed_events?: number;
}

export function Health() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function fetchData() {
      try {
        const res = await api.systemHealth;
        if (mounted) { setHealth(res); setLoading(false); }
      } catch (e) { if (mounted) setLoading(false); }
    }
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  if (loading) return <div className="space-y-4">{[...Array(8)].map((_, i) => <div key={i} className="h-16 bg-bg-card rounded-xl animate-pulse" />)}</div>;
  if (!health) return <div className="p-8 text-center text-red-400">Failed to load health data</div>;

  const components: Array<{ name: string; data: ComponentHealth }> = [
    { name: "Event Bus", data: health.event_bus as unknown as ComponentHealth },
    { name: "Backend API", data: health.backend as unknown as ComponentHealth },
    { name: "Database", data: health.database as unknown as ComponentHealth },
    { name: "Storage", data: health.storage as unknown as ComponentHealth },
    { name: "Camera", data: health.camera as unknown as ComponentHealth },
    { name: "Microphone", data: health.microphone as unknown as ComponentHealth },
    { name: "Network", data: health.network as unknown as ComponentHealth },
    { name: "Telegram", data: health.telegram as unknown as ComponentHealth },
    { name: "x402 Payment", data: health.x402 as unknown as ComponentHealth },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">System Health</h2>
        <StatusBadge status={health.overall_status} size="md" />
      </div>

      {/* Overall Health */}
      <div className="bg-bg-card rounded-2xl border border-slate-800/50 p-6" style={{ boxShadow: "0 8px 32px rgba(0,0,0,0.4)" }}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-500 mb-1">OVERALL STATUS</p>
            <p className="text-3xl font-bold text-slate-100">{health.overall_status}</p>
          </div>
          <StatusBadge status={health.overall_status} size="xl" />
        </div>
      </div>

      {/* Components Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {components.map((comp) => (
          <div key={comp.name} className="bg-bg-card rounded-xl border border-slate-800/50 p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-medium text-slate-200">{comp.name}</h3>
              <StatusBadge status={comp.data.status} size="sm" />
            </div>
            <div className="space-y-1.5 text-xs text-slate-500">
              {comp.data.last_check && <p>Last check: {new Date(comp.data.last_check).toLocaleTimeString()}</p>}
              {comp.data.note && <p className="text-slate-400">{comp.data.note}</p>}
              {comp.data.subscribed_events !== undefined && <p>Subscribed events: {comp.data.subscribed_events}</p>}
            </div>
          </div>
        ))}
      </div>

      {/* Agent Health Grid */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Agent Health</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {health.agents.map(agent => (
            <div key={agent.agent_id} className="bg-bg-card rounded-xl border border-slate-800/50 p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-slate-200 text-sm">{agent.name.replace("_agent", "").replace("_", " ").toUpperCase()}</span>
                <StatusBadge status={agent.status} size="sm" />
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2 rounded bg-slate-900/40">
                  <p className="text-slate-500">Latency</p>
                  <p className="font-mono text-slate-200">{agent.latency?.toFixed(1) || "0.0"}ms</p>
                </div>
                <div className="p-2 rounded bg-slate-900/40">
                  <p className="text-slate-500">CPU</p>
                  <p className="font-mono text-slate-200">{agent.cpu?.toFixed(1) || "0.0"}%</p>
                </div>
                <div className="p-2 rounded bg-slate-900/40">
                  <p className="text-slate-500">Memory</p>
                  <p className="font-mono text-slate-200">{agent.memory?.toFixed(1) || "0.0"} MB</p>
                </div>
                <div className="p-2 rounded bg-slate-900/40">
                  <p className="text-slate-500">Events</p>
                  <p className="font-mono text-slate-200">{agent.events_processed?.toLocaleString() || 0}</p>
                </div>
              </div>
              <div className="mt-2 pt-2 border-t border-slate-800/50 text-xs text-slate-500">
                <p>Errors: {agent.error_count || 0} | Warnings: {agent.warning_count || 0}</p>
                <p>State: {agent.current_state || "UNKNOWN"}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
