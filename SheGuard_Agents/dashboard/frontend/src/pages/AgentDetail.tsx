import * as React from "react";
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../services/api";
import type { AgentHealth, AgentEvent } from "../types";
import { AGENT_DEFINITIONS, type AgentId } from "../utils/agents";
import { StatusBadge } from "../components/StatusBadge";

export function AgentDetail() {
  const { agentId } = useParams<{ agentId: string }>();
  const navigate = useNavigate();
  const [agent, setAgent] = useState<AgentHealth | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"health" | "metrics" | "events" | "logs" | "config">("health");
  const [connected, setConnected] = useState(false);

  const def = agentId ? AGENT_DEFINITIONS[agentId as AgentId] : null;

  useEffect(() => {
    let mounted = true;
    const unsubConn = api.wsService.subscribe("connection", (data: any) => {
      if (mounted) setConnected(data?.state === "LIVE");
    });

    async function fetchData() {
      if (!agentId) return;
      try {
        setLoading(true);
        const [agentRes, eventsRes, logsRes] = await Promise.all([
          api.getAgent(agentId),
          api.getAgentEvents(agentId, 50),
          api.getAgentLogs(agentId, 50),
        ]);
        if (mounted) {
          setAgent(agentRes);
          setEvents(eventsRes || []);
          setLogs(logsRes.logs || []);
          setLoading(false);
        }
      } catch (e) {
        if (mounted) {
          setError(e instanceof Error ? e.message : "Failed to load agent data");
          setLoading(false);
        }
      }
    }

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => { mounted = false; clearInterval(interval); unsubConn(); };
  }, [agentId]);

  if (!agentId || !def) {
    return (
      <div className="space-y-6">
        <h2 className="text-lg font-semibold">Agent Not Found</h2>
        <button onClick={() => navigate("/agents")} className="px-4 py-2 rounded-lg bg-sky-600 text-white hover:bg-sky-700">
          Back to Agents
        </button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="space-y-4">
        {[...Array(6)].map((_, i) => <div key={i} className="h-20 bg-bg-card rounded-xl animate-pulse" />)}
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-bg-card rounded-2xl border border-red-500/30 p-8 text-center">
        <p className="text-red-400">{error}</p>
        <button onClick={() => navigate("/agents")} className="mt-4 px-4 py-2 rounded-lg bg-sky-600 text-white hover:bg-sky-700">
          Back to Agents
        </button>
      </div>
    );
  }

  const formatUptime = (uptime?: string) => uptime || "0h 0m";
  const formatLatency = (latency?: number) => `${latency?.toFixed(1) || "0.0"}ms`;
  const formatMemory = (memory?: number) => `${(memory || 0).toFixed(1)} MB`;
  const formatCPU = (cpu?: number) => `${(cpu || 0).toFixed(1)}%`;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-xl flex items-center justify-center text-3xl bg-slate-800/50 border border-slate-700/50">
            {def.icon}
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-100">{def.name}</h2>
            <p className="text-sm text-slate-500">{def.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={agent?.status || "OFFLINE"} size="lg" />
          <span className={`flex items-center gap-1.5 text-sm ${connected ? "text-green-400" : "text-red-400"}`}>
            <span className={`w-2 h-2 rounded-full ${connected ? "bg-green-400" : "bg-red-400"}`} />
            {connected ? "LIVE" : "OFFLINE"}
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-900/40 rounded-lg p-1 border border-slate-800/50">
        {(["health", "metrics", "events", "logs", "config"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === tab
                ? "bg-sky-600 text-white shadow-lg"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="bg-bg-card rounded-2xl border border-slate-800/50 p-6">
        {/* Health Tab */}
        {activeTab === "health" && agent && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 rounded-lg bg-slate-900/40 border border-slate-800/50">
                <p className="text-xs text-slate-500 mb-1">Status</p>
                <StatusBadge status={agent.status} size="md" />
              </div>
              <div className="p-4 rounded-lg bg-slate-900/40 border border-slate-800/50">
                <p className="text-xs text-slate-500 mb-1">Uptime</p>
                <p className="font-mono text-lg text-slate-100">{formatUptime((agent.details?.uptime as string) || agent.uptime)}</p>
              </div>
              <div className="p-4 rounded-lg bg-slate-900/40 border border-slate-800/50">
                <p className="text-xs text-slate-500 mb-1">Last Heartbeat</p>
                <p className="font-mono text-sm text-slate-300">
                  {agent.last_heartbeat ? new Date(agent.last_heartbeat).toLocaleTimeString() : "—"}
                </p>
              </div>
              <div className="p-4 rounded-lg bg-slate-900/40 border border-slate-800/50">
                <p className="text-xs text-slate-500 mb-1">Version</p>
                <p className="font-mono text-sm text-slate-300">{agent.version}</p>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 rounded-lg bg-slate-900/40 border border-slate-800/50">
                <p className="text-xs text-slate-500 mb-1">Events Processed</p>
                <p className="font-mono text-xl text-slate-100">{agent.events_processed?.toLocaleString() || 0}</p>
              </div>
              <div className="p-4 rounded-lg bg-slate-900/40 border border-slate-800/50">
                <p className="text-xs text-slate-500 mb-1">Errors</p>
                <p className="font-mono text-xl text-red-400">{agent.error_count || 0}</p>
              </div>
              <div className="p-4 rounded-lg bg-slate-900/40 border border-slate-800/50">
                <p className="text-xs text-slate-500 mb-1">Warnings</p>
                <p className="font-mono text-xl text-amber-400">{agent.warning_count || 0}</p>
              </div>
              <div className="p-4 rounded-lg bg-slate-900/40 border border-slate-800/50">
                <p className="text-xs text-slate-500 mb-1">Current State</p>
                <p className="font-mono text-sm text-slate-300">{agent.current_state || "UNKNOWN"}</p>
              </div>
            </div>

            <div className="p-4 rounded-lg bg-slate-900/40 border border-slate-800/50">
              <p className="text-xs text-slate-500 mb-2">Component Status</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(agent.component_status || {}).map(([key, value]) => (
                  <span key={key} className={`px-2 py-1 rounded text-xs font-mono ${
                    value === "HEALTHY" ? "bg-green-500/20 text-green-400 border border-green-500/30" :
                    value === "DEGRADED" ? "bg-amber-500/20 text-amber-400 border border-amber-500/30" :
                    "bg-red-500/20 text-red-400 border border-red-500/30"
                  }`}>
                    {key}: {value}
                  </span>
                ))}
                {Object.keys(agent.component_status || {}).length === 0 && (
                  <span className="text-xs text-slate-500">No component data</span>
                )}
              </div>
            </div>

            <div className="p-4 rounded-lg bg-slate-900/40 border border-slate-800/50">
              <p className="text-xs text-slate-500 mb-2">Current Task</p>
              <p className="font-mono text-sm text-slate-300">{agent.current_task || "IDLE"}</p>
            </div>
          </div>
        )}

        {/* Metrics Tab */}
        {activeTab === "metrics" && agent && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div className="p-4 rounded-lg bg-slate-900/40 border border-slate-800/50">
                <p className="text-xs text-slate-500 mb-1">Avg Latency</p>
                <p className="font-mono text-2xl text-slate-100">{formatLatency(agent.avg_latency_ms)}</p>
              </div>
              <div className="p-4 rounded-lg bg-slate-900/40 border border-slate-800/50">
                <p className="text-xs text-slate-500 mb-1">CPU Usage</p>
                <p className="font-mono text-2xl text-slate-100">{formatCPU((agent.details?.cpu as number) || 0)}</p>
              </div>
              <div className="p-4 rounded-lg bg-slate-900/40 border border-slate-800/50">
                <p className="text-xs text-slate-500 mb-1">Memory</p>
                <p className="font-mono text-2xl text-slate-100">{formatMemory((agent.details?.memory as number) || 0)}</p>
              </div>
            </div>

            <div className="p-4 rounded-lg bg-slate-900/40 border border-slate-800/50">
              <p className="text-xs text-slate-500 mb-3">Additional Metrics</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                {Object.entries(agent.details || {}).map(([key, value]) => (
                  <div key={key} className="p-3 rounded bg-slate-800/50">
                    <p className="text-slate-500">{key}</p>
                    <p className="font-mono text-slate-100">{String(value)}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Events Tab */}
        {activeTab === "events" && (
          <div className="space-y-4">
            {events.length === 0 ? (
              <div className="text-center py-12 text-slate-500">No events for this agent</div>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {events.map((evt, idx) => (
                  <div key={idx} className="p-3 rounded-lg bg-slate-900/40 border border-slate-800/50">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs text-sky-400">{evt.event_type || "EVENT"}</span>
                      <span className="text-xs text-slate-500">
                        {evt.timestamp ? new Date(evt.timestamp).toLocaleTimeString() : "—"}
                      </span>
                    </div>
                    <div className="text-xs text-slate-400 mt-1 font-mono">
                      {evt.incident_id ? `Incident: ${evt.incident_id}` : ""}
                      {evt.trace_id ? ` | Trace: ${evt.trace_id}` : ""}
                    </div>
                    {evt.data && (
                      <pre className="mt-2 text-xs text-slate-300 overflow-x-auto max-h-32">
                        {JSON.stringify(evt.data, null, 2)}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Logs Tab */}
        {activeTab === "logs" && (
          <div className="space-y-4">
            {logs.length === 0 ? (
              <div className="text-center py-12 text-slate-500">No logs available</div>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto font-mono text-sm">
                {logs.map((log, idx) => (
                  <div
                    key={idx}
                    className={`p-3 rounded-lg bg-slate-900/40 border border-slate-800/50 ${
                      log.level === "ERROR" ? "border-red-500/30" :
                      log.level === "WARNING" ? "border-amber-500/30" : ""
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        log.level === "ERROR" ? "bg-red-500/20 text-red-400" :
                        log.level === "WARNING" ? "bg-amber-500/20 text-amber-400" :
                        log.level === "INFO" ? "bg-blue-500/20 text-blue-400" :
                        "bg-slate-500/20 text-slate-400"
                      }`}>
                        {log.level}
                      </span>
                      <span className="text-slate-500">{log.timestamp}</span>
                    </div>
                    <p className="text-slate-200 mt-1">{log.message}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Config Tab */}
        {activeTab === "config" && (
          <div className="space-y-4">
            <pre className="text-xs text-slate-300 bg-slate-900/40 p-4 rounded-lg overflow-x-auto max-h-96">
              {JSON.stringify(def, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
