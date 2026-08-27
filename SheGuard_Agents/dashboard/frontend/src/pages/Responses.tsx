import * as React from "react";
import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { ResponseRecord } from "../types";

export function Responses() {
  const [responses, setResponses] = useState<ResponseRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function fetchData() {
      try {
        const res = await api.responses;
        if (mounted) { setResponses(res); setLoading(false); }
      } catch (e) { if (mounted) setLoading(false); }
    }
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  if (loading) return <div className="space-y-4">{[...Array(3)].map((_, i) => <div key={i} className="h-24 bg-bg-card rounded-xl animate-pulse" />)}</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Responses</h2>
        <span className="text-sm text-slate-500">{responses.length} total</span>
      </div>
      {responses.length === 0 ? (
        <div className="bg-bg-card rounded-2xl border border-slate-800/50 p-12 text-center">
          <p className="text-3xl mb-3">🚑</p>
          <p className="text-slate-500">No responses recorded yet</p>
        </div>
      ) : (
        <div className="space-y-3">
          {responses.map((resp, idx) => (
            <div key={idx} className="bg-bg-card rounded-xl border border-slate-800/50 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-slate-100">Incident: {resp.incident_id}</p>
                  <p className="text-xs text-slate-500 mt-1">Timestamp: {resp.timestamp ? new Date(resp.timestamp).toLocaleString() : "—"}</p>
                </div>
                <span className={`px-3 py-1 rounded-lg text-xs font-medium ${
                  resp.status === "SUCCESS" ? "text-green-400 bg-green-500/10 border-green-500/30" :
                  resp.status === "PARTIAL" ? "text-amber-400 bg-amber-500/10 border-amber-500/30" :
                  resp.status === "FAILED" ? "text-red-400 bg-red-500/10 border-red-500/30" :
                  "text-slate-400 bg-slate-500/10 border-slate-500/30"
                }`}>{resp.status}</span>
              </div>
              <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                <div className="p-2 rounded bg-slate-900/40">
                  <p className="text-slate-500">Incident Created</p>
                  <p className="font-mono text-slate-200">{resp.incident_created ? "✓" : "✗"}</p>
                </div>
                <div className="p-2 rounded bg-slate-900/40">
                  <p className="text-slate-500">Evidence Stored</p>
                  <p className="font-mono text-slate-200">{resp.evidence_stored ? "✓" : "✗"}</p>
                </div>
                <div className="p-2 rounded bg-slate-900/40">
                  <p className="text-slate-500">Location</p>
                  <p className="font-mono text-slate-200">{resp.location_recorded ? "✓" : "✗"}</p>
                </div>
                <div className="p-2 rounded bg-slate-900/40">
                  <p className="text-slate-500">Guardian</p>
                  <p className="font-mono text-slate-200">{resp.guardian_notified ? "✓" : "✗"}</p>
                </div>
                <div className="p-2 rounded bg-slate-900/40">
                  <p className="text-slate-500">Telegram</p>
                  <p className="font-mono text-slate-200">{resp.telegram_sent ? "✓" : "✗"}</p>
                </div>
                <div className="p-2 rounded bg-slate-900/40">
                  <p className="text-slate-500">Mobile</p>
                  <p className="font-mono text-slate-200">{resp.mobile_sent ? "✓" : "✗"}</p>
                </div>
                <div className="p-2 rounded bg-slate-900/40">
                  <p className="text-slate-500">Backend</p>
                  <p className="font-mono text-slate-200">{resp.backend_updated ? "✓" : "✗"}</p>
                </div>
                <div className="p-2 rounded bg-slate-900/40">
                  <p className="text-slate-500">Dashboard</p>
                  <p className="font-mono text-slate-200">{resp.dashboard_updated ? "✓" : "✗"}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
