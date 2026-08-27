import * as React from "react";
import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { TestCategory, TestSummary } from "../types";

export function Tests() {
  const [tests, setTests] = useState<TestSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function fetchData() {
      try {
        const res = await api.tests;
        if (mounted) { setTests(res); setLoading(false); }
      } catch (e) { if (mounted) setLoading(false); }
    }
    fetchData();
  }, []);

  if (loading) return <div className="h-32 bg-bg-card rounded-xl animate-pulse" />;
  if (!tests) return <div className="p-8 text-center text-slate-500">Failed to load test results</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Test Results</h2>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-green-400">{tests.summary.passed} passed</span>
          <span className="text-slate-600">•</span>
          <span className="text-red-400">{tests.summary.failed} failed</span>
          <span className="text-slate-600">•</span>
          <span className="text-slate-400">{tests.summary.skipped} skipped</span>
        </div>
      </div>

      {/* Overall Progress */}
      <div className="bg-bg-card rounded-2xl border border-slate-800/50 p-6">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm text-slate-400">Overall</span>
          <span className="text-sm font-mono text-slate-200">{tests.summary.passed}/{tests.summary.total}</span>
        </div>
        <div className="h-3 bg-slate-800 rounded-full overflow-hidden">
          <div className="h-full bg-gradient-to-r from-green-500 to-emerald-500 rounded-full" style={{ width: `${(tests.summary.passed / tests.summary.total) * 100}%` }} />
        </div>
      </div>

      {/* Test Categories */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {tests.categories.map(cat => (
          <div key={cat.name} className="bg-bg-card rounded-xl border border-slate-800/50 p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-medium text-slate-200">{cat.name}</h3>
              {cat.failed > 0 ? (
                <span className="text-xs px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/30">FAIL</span>
              ) : (
                <span className="text-xs px-2 py-0.5 rounded-full bg-green-500/10 text-green-400 border border-green-500/30">PASS</span>
              )}
            </div>
            <div className="grid grid-cols-3 gap-2 text-center text-xs">
              <div className="p-2 rounded bg-green-500/10">
                <p className="text-green-400 font-mono font-bold">{cat.passed}</p>
                <p className="text-slate-500">Passed</p>
              </div>
              <div className="p-2 rounded bg-red-500/10">
                <p className="text-red-400 font-mono font-bold">{cat.failed}</p>
                <p className="text-slate-500">Failed</p>
              </div>
              <div className="p-2 rounded bg-slate-500/10">
                <p className="text-slate-400 font-mono font-bold">{cat.skipped}</p>
                <p className="text-slate-500">Skipped</p>
              </div>
            </div>
            <p className="mt-2 text-[10px] text-slate-600">Last run: {new Date(cat.last_run).toLocaleString()}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
