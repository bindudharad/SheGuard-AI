import * as React from "react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";
import type { Incident } from "../types";

export function Incidents() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    let mounted = true;
    async function fetchData() {
      try {
        const res = await api.incidents;
        if (mounted) { setIncidents(res); setLoading(false); }
      } catch (e) { if (mounted) setLoading(false); }
    }
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  const getSeverityColor = (s: string) => {
    if (s === "CRITICAL" || s === "HIGH") return "text-red-400 bg-red-500/10 border-red-500/30";
    if (s === "WARNING") return "text-amber-400 bg-amber-500/10 border-amber-500/30";
    if (s === "SAFE") return "text-green-400 bg-green-500/10 border-green-500/30";
    return "text-slate-400 bg-slate-500/10 border-slate-500/30";
  };

  if (loading) return <div className="space-y-4">{[...Array(5)].map((_, i) => <div key={i} className="h-20 bg-bg-card rounded-xl animate-pulse" />)}</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Incidents</h2>
        <span className="text-sm text-slate-500">{incidents.length} total</span>
      </div>

      {incidents.length === 0 ? (
        <div className="bg-bg-card rounded-2xl border border-slate-800/50 p-12 text-center">
          <p className="text-3xl mb-3">🚨</p>
          <p className="text-slate-500">No incidents recorded yet</p>
        </div>
      ) : (
        <div className="space-y-3">
          {incidents.map((inc) => (
            <div
              key={inc.incident_id}
              className="bg-bg-card rounded-xl border border-slate-800/50 p-4 hover:border-sky-500/30 transition-colors cursor-pointer"
              onClick={() => navigate(`/incidents/${inc.incident_id}`)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-lg">🚨</span>
                  <div>
                    <p className="font-medium text-slate-100">{inc.incident_id}</p>
                    <p className="text-xs text-slate-500 font-mono">Trace: {inc.trace_id?.substring(0, 12) || "—"}...</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-xs font-medium px-2.5 py-1 rounded-full border ${getSeverityColor(inc.severity)}`}>
                    {inc.severity}
                  </span>
                  <span className="text-xs text-slate-400 font-mono">{new Date(inc.created_at).toLocaleTimeString()}</span>
                </div>
              </div>
              <div className="mt-2 flex items-center gap-4 text-xs text-slate-500">
                <span>Confidence: {inc.confidence.toFixed(2)}</span>
                <span>Status: {inc.status}</span>
                {inc.current_agent && <span>Current Agent: {inc.current_agent}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function IncidentDetail() {
  return <div className="p-8 text-center text-slate-500">Incident detail view - coming soon</div>;
}
