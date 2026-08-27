import * as React from "react";
import { useEffect, useState, useMemo } from "react";
import { api } from "../services/api";
import type { AgentEvent } from "../types";
import { AGENT_DEFINITIONS, type AgentId } from "../utils/agents";

export function Events() {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [filterAgent, setFilterAgent] = useState<string>("all");
  const [filterIncident, setFilterIncident] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [isPaused, setIsPaused] = useState(false);
  const [limit, setLimit] = useState(200);

  useEffect(() => {
    let mounted = true;
    async function fetchData() {
      try {
        const res = await api.getEvents({ limit });
        if (mounted) setEvents(res);
      } catch (e) { /* ignore */ }
    }
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => { mounted = false; clearInterval(interval); };
  }, [limit]);

  const filteredEvents = useMemo(() => {
    let result = events;
    if (filterAgent !== "all") result = result.filter(e => (e.agent_id || e.agent) === filterAgent);
    if (filterIncident) result = result.filter(e => e.incident_id?.includes(filterIncident));
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      result = result.filter(e =>
        e.event_type?.toLowerCase().includes(q) ||
        e.incident_id?.toLowerCase().includes(q) ||
        e.trace_id?.toLowerCase().includes(q)
      );
    }
    return result;
  }, [events, filterAgent, filterIncident, searchQuery]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Event Stream</h2>
        <div className="flex items-center gap-3">
          <button className={`px-3 py-1.5 rounded-lg text-sm border ${isPaused ? "border-amber-500/30 text-amber-400 bg-amber-500/10" : "border-green-500/30 text-green-400 bg-green-500/10"}`}
            onClick={() => setIsPaused(!isPaused)}>
            {isPaused ? "⏸ Paused" : "▶ Live"}
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Search events..."
          className="px-3 py-2 rounded-lg bg-slate-900/50 border border-slate-700/50 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500/50 flex-1 min-w-[200px]"
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
        />
        <select
          className="px-3 py-2 rounded-lg bg-slate-900/50 border border-slate-700/50 text-sm text-slate-200"
          value={filterAgent}
          onChange={e => setFilterAgent(e.target.value)}
        >
          <option value="all">All Agents</option>
          {Object.entries(AGENT_DEFINITIONS).map(([id, def]) => (
            <option key={id} value={id}>{def.short}</option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Filter by incident ID..."
          className="px-3 py-2 rounded-lg bg-slate-900/50 border border-slate-700/50 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500/50 w-64"
          value={filterIncident}
          onChange={e => setFilterIncident(e.target.value)}
        />
      </div>

      {/* Events Table */}
      <div className="bg-bg-card rounded-2xl border border-slate-800/50 overflow-hidden" style={{ boxShadow: "0 8px 32px rgba(0,0,0,0.4)" }}>
        {filteredEvents.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            <p className="text-3xl mb-3">📡</p>
            <p>No events match your filters</p>
          </div>
        ) : (
          <div className="max-h-[600px] overflow-y-auto">
            <table className="w-full">
              <thead className="sticky top-0 bg-bg-card border-b border-slate-800/50 z-10">
                <tr className="text-xs text-slate-500 uppercase tracking-wider">
                  <th className="px-4 py-3 text-left">Timestamp</th>
                  <th className="px-4 py-3 text-left">Agent</th>
                  <th className="px-4 py-3 text-left">Event Type</th>
                  <th className="px-4 py-3 text-left">Incident ID</th>
                  <th className="px-4 py-3 text-left">Trace ID</th>
                  <th className="px-4 py-3 text-left">Payload</th>
                </tr>
              </thead>
              <tbody>
                {filteredEvents.slice().reverse().map((evt, idx) => {
                  const agentId = (evt.agent_id || evt.agent || "") as AgentId;
                  const def = AGENT_DEFINITIONS[agentId];
                  return (
                    <tr key={idx} className="border-b border-slate-800/30 hover:bg-slate-900/30 transition-colors">
                      <td className="px-4 py-2.5 text-sm font-mono text-slate-400 whitespace-nowrap">
                        {new Date(evt.timestamp).toLocaleTimeString()}
                      </td>
                      <td className="px-4 py-2.5 text-sm font-medium text-slate-200">
                        <span className="flex items-center gap-2">
                          {def?.icon} {def?.short || agentId}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-sm text-sky-400 font-mono">{evt.event_type}</td>
                      <td className="px-4 py-2.5 text-sm text-slate-300 font-mono">{evt.incident_id || "—"}</td>
                      <td className="px-4 py-2.5 text-xs text-slate-500 font-mono">{evt.trace_id?.substring(0, 8) || "—"}...</td>
                      <td className="px-4 py-2.5 text-xs text-slate-500 font-mono max-w-[200px] truncate">
                        {evt.payload ? JSON.stringify(evt.payload).substring(0, 100) : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
