import * as React from "react";
import { NavLink } from "react-router-dom";
import type { AgentHealth, AgentId } from "../types";
import { StatusBadge } from "./StatusBadge";
import { AGENT_ICONS, AGENT_COLORS, getAgentDef } from "../utils/agents";

interface AgentCardProps {
  health: AgentHealth;
  agentId: AgentId;
}

export function AgentCard({ health, agentId }: AgentCardProps) {
  const def = getAgentDef(agentId);
  const color = AGENT_COLORS[agentId] || "#38bdf8";
  const icon = AGENT_ICONS[agentId] || "🤖";

  const formatUptime = (uptime: string) => uptime || "0h 0m";
  const formatNumber = (n: number) => n.toLocaleString();

  return (
    <NavLink
      to={`/agents/${agentId}`}
      className="group relative flex flex-col p-5 bg-bg-card rounded-xl border border-slate-800/50 hover:border-accent-DEFAULT/30 transition-all duration-300"
      style={{ boxShadow: "0 4px 24px rgba(0,0,0,0.3)" }}
    >
      {/* Top: Icon + Status */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl"
            style={{ background: `linear-gradient(135deg, ${color}20, ${color}10)`, border: `1px solid ${color}40` }}
          >
            <span aria-hidden="true">{icon}</span>
          </div>
          <div>
            <h3 className="font-semibold text-slate-100">{def.short}</h3>
            <p className="text-xs text-slate-500">{def.name}</p>
          </div>
        </div>
        <StatusBadge status={health.status} size="sm" />
      </div>

      {/* Middle: Key Metrics */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800/50">
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Latency</p>
          <p className="font-mono text-lg font-semibold text-slate-100">
            {health.latency?.toFixed(1) ?? "—"} ms
          </p>
        </div>
        <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800/50">
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Uptime</p>
          <p className="font-mono text-lg font-semibold text-slate-100">{formatUptime(health.uptime)}</p>
        </div>
        <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800/50">
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">CPU</p>
          <p className="font-mono text-lg font-semibold text-slate-100">{health.cpu?.toFixed(1) ?? "—"}%</p>
        </div>
        <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800/50">
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Memory</p>
          <p className="font-mono text-lg font-semibold text-slate-100">{(health.memory / 1024 / 1024).toFixed(0)} MB</p>
        </div>
      </div>

      {/* Bottom: Events & Errors */}
      <div className="flex items-center justify-between pt-3 border-t border-slate-800/50">
        <div className="flex items-center gap-4 text-sm">
          <span className="flex items-center gap-1 text-slate-400">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
            <span className="text-slate-100 font-mono">{formatNumber(health.events_processed)}</span>
          </span>
          <span className="flex items-center gap-1 text-slate-400">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="15" y1="9" x2="9" y2="15" />
              <line x1="9" y1="9" x2="15" y2="15" />
            </svg>
            <span className="text-slate-100 font-mono">{health.error_count}</span>
          </span>
        </div>
        <div className="text-xs text-slate-500">
          {health.last_heartbeat ? `Last: ${new Date(health.last_heartbeat).toLocaleTimeString()}` : "No heartbeat"}
        </div>
      </div>

      {/* Glow accent on hover */}
      <div
        className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"
        style={{ boxShadow: `0 0 20px ${color}40` }}
      />
    </NavLink>
  );
}
