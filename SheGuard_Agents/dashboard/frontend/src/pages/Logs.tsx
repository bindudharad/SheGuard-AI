import * as React from "react";
import { useEffect, useState } from "react";
import { api } from "../services/api";

interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
}

export function Logs() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filterLevel, setFilterLevel] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    let mounted = true;
    async function fetchData() {
      try {
        // Fetch logs from all agents
        const agents = ["vision_agent", "audio_agent", "context_agent", "threat_agent", "decision_agent", "x402_agent", "response_agent"];
        const allLogs: LogEntry[] = [];
        for (const agentId of agents) {
          try {
            const res = await api.getAgentLogs(agentId, 50);
            if (res.logs) allLogs.push(...res.logs);
          } catch { /* skip */ }
        }
        allLogs.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
        if (mounted) setLogs(allLogs);
      } catch (e) { /* ignore */ }
    }
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  const filteredLogs = logs.filter(log => {
    if (filterLevel !== "all" && log.level !== filterLevel) return false;
    if (searchQuery && !log.message.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">Logs</h2>
      <div className="flex gap-3">
        <input
          type="text"
          placeholder="Search logs..."
          className="px-3 py-2 rounded-lg bg-slate-900/50 border border-slate-700/50 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500/50 flex-1"
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
        />
        <select
          className="px-3 py-2 rounded-lg bg-slate-900/50 border border-slate-700/50 text-sm text-slate-200"
          value={filterLevel}
          onChange={e => setFilterLevel(e.target.value)}
        >
          <option value="all">All Levels</option>
          <option value="ERROR">Errors</option>
          <option value="WARNING">Warnings</option>
          <option value="INFO">Info</option>
        </select>
      </div>
      <div className="bg-bg-card rounded-2xl border border-slate-800/50 overflow-hidden">
        <div className="max-h-[600px] overflow-y-auto font-mono text-xs">
          {filteredLogs.length === 0 ? (
            <div className="p-8 text-center text-slate-500 font-sans">No logs available</div>
          ) : (
            filteredLogs.map((log, idx) => (
              <div key={idx} className="px-4 py-2 border-b border-slate-800/30 hover:bg-slate-900/30 flex gap-3">
                <span className="text-slate-600 whitespace-nowrap">{new Date(log.timestamp).toLocaleTimeString()}</span>
                <span className={`w-16 text-center ${log.level === "ERROR" ? "text-red-400" : log.level === "WARNING" ? "text-amber-400" : "text-green-400"}`}>
                  {log.level}
                </span>
                <span className="text-slate-300 break-all">{log.message}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
