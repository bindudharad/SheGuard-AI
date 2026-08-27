import * as React from "react";
import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { X402Status } from "../types";
import { StatusBadge } from "../components/StatusBadge";

export function X402Page() {
  const [x402, setX402] = useState<X402Status | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function fetchData() {
      try {
        const res = await api.x402;
        if (mounted) { setX402(res); setLoading(false); }
      } catch (e) { if (mounted) setLoading(false); }
    }
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  if (loading) return <div className="h-32 bg-bg-card rounded-xl animate-pulse" />;
  if (!x402) return <div className="p-8 text-center text-slate-500">Failed to load x402 data</div>;

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">x402 Agent Status</h2>
      <div className="bg-bg-card rounded-2xl border border-slate-800/50 p-6">
        <div className="flex items-center gap-4 mb-4">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl bg-pink-500/10 border border-pink-500/30">💳</div>
          <div>
            <p className="text-xl font-bold text-slate-100">{x402.mode?.toUpperCase() || "UNKNOWN"} Mode</p>
            <StatusBadge status={x402.status} size="md" />
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
          <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800/50">
            <p className="text-xs text-slate-500 mb-1">Network</p>
            <p className="font-mono text-slate-200">{x402.mode === "simulation" ? "Simulated" : "Algorand Testnet"}</p>
          </div>
          <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800/50">
            <p className="text-xs text-slate-500 mb-1">Intelligence Requests</p>
            <p className="font-mono text-slate-200">{x402.intelligence_requests || 0}</p>
          </div>
          <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800/50">
            <p className="text-xs text-slate-500 mb-1">Successful Payments</p>
            <p className="font-mono text-green-400">{x402.successful_payments || 0}</p>
          </div>
          <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800/50">
            <p className="text-xs text-slate-500 mb-1">Failed Payments</p>
            <p className="font-mono text-red-400">{x402.failed_payments || 0}</p>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
          <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800/50">
            <p className="text-xs text-slate-500 mb-1">Wallet</p>
            <p className="font-mono text-slate-200 text-xs">{x402.wallet_address || "Not configured"}</p>
          </div>
          <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800/50">
            <p className="text-xs text-slate-500 mb-1">Network</p>
            <p className="font-mono text-slate-200">{x402.network || "—"}</p>
          </div>
          <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800/50">
            <p className="text-xs text-slate-500 mb-1">Last Payment</p>
            <p className="font-mono text-slate-200 text-xs">{x402.last_payment ? "Completed" : "None"}</p>
          </div>
          <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800/50">
            <p className="text-xs text-slate-500 mb-1">Status</p>
            <p className="font-mono text-green-400">{x402.status}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
