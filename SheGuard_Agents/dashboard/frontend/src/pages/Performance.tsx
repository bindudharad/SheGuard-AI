import * as React from "react";
import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { SystemMetrics, AgentHealth } from "../types";
import { PIPELINE_ORDER, AGENT_DEFINITIONS, type AgentId } from "../utils/agents";

export function Performance() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [agents, setAgents] = useState<AgentHealth[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function fetchData() {
      try {
        const [m, a] = await Promise.all([api.systemMetrics, api.agents]);
        if (mounted) { setMetrics(m); setAgents(a); setLoading(false); }
      } catch (e) { if (mounted) setLoading(false); }
    }
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  if (loading) return <div className="space-y-4">{[...Array(4)].map((_, i) => <div key={i} className="h-24 bg-bg-card rounded-xl animate-pulse" />)}</div>;

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">Performance</h2>

      {/* System Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-bg-card rounded-xl border border-slate-800/50 p-4">
          <p className="text-xs text-slate-500 mb-1">Uptime</p>
          <p className="text-xl font-bold font-mono text-slate-100">{metrics?.uptime || "0h 0m"}</p>
        </div>
        <div className="bg-bg-card rounded-xl border border-slate-800/50 p-4">
          <p className="text-xs text-slate-500 mb-1">Events in History</p>
          <p className="text-xl font-bold font-mono text-slate-100">{metrics?.event_history_size || 0}</p>
        </div>
        <div className="bg-bg-card rounded-xl border border-slate-800/50 p-4">
          <p className="text-xs text-slate-500 mb-1">Active Incidents</p>
          <p className="text-xl font-bold font-mono text-slate-100">{metrics?.active_incidents || 0}</p>
        </div>
        <div className="bg-bg-card rounded-xl border border-slate-800/50 p-4">
          <p className="text-xs text-slate-500 mb-1">Connected Agents</p>
          <p className="text-xl font-bold font-mono text-slate-100">{metrics?.total_agents || 0}</p>
        </div>
      </div>

      {/* Per-agent metrics */}
      <div>
        <h3 className="text-md font-semibold mb-4">Agent Metrics</h3>
        <div className="space-y-3">
          {agents.map(agent => (
            <div key={agent.agent_id} className="bg-bg-card rounded-xl border border-slate-800/50 p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{AGENT_DEFINITIONS[agent.agent_id as AgentId]?.icon || "🤖"}</span>
                  <span className="font-medium text-slate-200">{agent.name.replace("_agent", "").toUpperCase()}</span>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full ${agent.status === "HEALTHY" ? "text-green-400 bg-green-500/10" : "text-amber-400 bg-amber-500/10"}`}>
                  {agent.status}
                </span>
              </div>
              <div className="grid grid-cols-5 gap-3">
                <div className="p-2 rounded bg-slate-900/40 text-center">
                  <p className="text-[10px] text-slate-500">Latency</p>
                  <p className="font-mono text-sm text-slate-200">{agent.latency?.toFixed(1) || "0.0"}ms</p>
                </div>
                <div className="p-2 rounded bg-slate-900/40 text-center">
                  <p className="text-[10px] text-slate-500">Events</p>
                  <p className="font-mono text-sm text-slate-200">{agent.events_processed}</p>
                </div>
                <div className="p-2 rounded bg-slate-900/40 text-center">
                  <p className="text-[10px] text-slate-500">Errors</p>
                  <p className="font-mono text-sm text-slate-200">{agent.error_count}</p>
                </div>
                <div className="p-2 rounded bg-slate-900/40 text-center">
                  <p className="text-[10px] text-slate-500">Warnings</p>
                  <p className="font-mono text-sm text-slate-200">{agent.warning_count}</p>
                </div>
                <div className="p-2 rounded bg-slate-900/40 text-center">
                  <p className="text-[10px] text-slate-500">State</p>
                  <p className="font-mono text-sm text-slate-200">{agent.current_state}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
