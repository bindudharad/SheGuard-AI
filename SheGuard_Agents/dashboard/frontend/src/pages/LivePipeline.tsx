import * as React from "react";
import { useEffect, useState, useCallback, useRef } from "react";
import { api } from "../services/api";
import type { AgentHealth, AgentEvent } from "../types";
import { PIPELINE_ORDER, AGENT_DEFINITIONS, type AgentId, getAgentStatusColor } from "../utils/agents";

type WorkflowState = "IDLE" | "WAITING" | "PROCESSING" | "SUCCESS" | "ERROR" | "SKIPPED" | "OFFLINE";

interface PipelineStage {
  agentId: AgentId;
  state: WorkflowState;
  startTime?: number;
  endTime?: number;
  duration?: number;
  input?: string;
  output?: string;
  error?: string;
  incidentId?: string;
  traceId?: string;
  riskScore?: number;
  threatLevel?: string;
  decision?: string;
  confidence?: number;
}

interface IncidentTimeline {
  incidentId: string;
  traceId: string;
  stages: PipelineStage[];
  decision: "SAFE" | "UNCERTAIN" | "CRITICAL" | "UNKNOWN";
  completedStages: number;
  totalStages: number;
  progress: number;
  startTime: number;
  endTime?: number;
  riskScore?: number;
  threatLevel?: string;
  confidence?: number;
}

export function LivePipeline() {
  const [agents, setAgents] = useState<Record<string, AgentHealth>>({});
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [activeTimeline, setActiveTimeline] = useState<IncidentTimeline | null>(null);
  const [pastTimelines, setPastTimelines] = useState<IncidentTimeline[]>([]);
  const [mode, setMode] = useState<"LIVE" | "REPLAY">("LIVE");
  const [selectedIncident, setSelectedIncident] = useState<string | null>(null);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [isPaused, setIsPaused] = useState(false);
  const eventsRef = useRef<AgentEvent[]>([]);

  // Map event types to pipeline stages
  const eventToStageMap: Record<string, { agentId: AgentId; state: WorkflowState }> = {
    FRAME_PROCESSED: { agentId: "vision_agent", state: "SUCCESS" },
    AUDIO_PROCESSED: { agentId: "audio_agent", state: "SUCCESS" },
    KEYWORD_DETECTED: { agentId: "audio_agent", state: "SUCCESS" },
    DISTRESS_AUDIO_DETECTED: { agentId: "audio_agent", state: "SUCCESS" },
    CONTEXT_UPDATED: { agentId: "context_agent", state: "SUCCESS" },
    THREAT_UPDATED: { agentId: "threat_agent", state: "SUCCESS" },
    THREAT_ESCALATED: { agentId: "threat_agent", state: "SUCCESS" },
    DECISION_MADE: { agentId: "decision_agent", state: "SUCCESS" },
    EMERGENCY_DECLARED: { agentId: "decision_agent", state: "SUCCESS" },
    INTELLIGENCE_RECEIVED: { agentId: "x402_agent", state: "SUCCESS" },
    RESPONSE_COMPLETE: { agentId: "response_agent", state: "SUCCESS" },
    INCIDENT_CREATED: { agentId: "response_agent", state: "SUCCESS" },
  };

  // Initialize pipeline stages for an incident
  const createTimeline = useCallback((incidentId: string, traceId: string): IncidentTimeline => {
    return {
      incidentId,
      traceId,
      stages: PIPELINE_ORDER.map(id => ({
        agentId: id,
        state: id === "vision_agent" ? "PROCESSING" : "WAITING",
      })),
      decision: "UNKNOWN",
      completedStages: 0,
      totalStages: 7,
      progress: 0,
      startTime: Date.now(),
    };
  }, []);

  // Process events into timeline updates
  const processEvent = useCallback((event: AgentEvent, timeline: IncidentTimeline): IncidentTimeline => {
    const mapping = eventToStageMap[event.event_type];
    if (!mapping) return timeline;

    const incidentId = event.incident_id || timeline.incidentId;
    if (incidentId !== timeline.incidentId) return timeline;

    const newStages = timeline.stages.map(stage => {
      if (stage.agentId !== mapping.agentId) return stage;
      
      const output = JSON.stringify(event.payload || {}).substring(0, 200);
      
      return {
        ...stage,
        state: mapping.state,
        endTime: Date.now(),
        duration: stage.startTime ? Date.now() - stage.startTime : 0,
        output,
        incidentId,
        traceId: event.trace_id || timeline.traceId,
      };
    });

    // Mark next agent as PROCESSING
    const completedIdx = newStages.findIndex(s => s.state === "SUCCESS" || s.state === "ERROR");
    if (completedIdx >= 0 && completedIdx < newStages.length - 1) {
      const nextIdx = completedIdx + 1;
      if (newStages[nextIdx].state === "WAITING") {
        newStages[nextIdx] = {
          ...newStages[nextIdx],
          state: "PROCESSING",
          startTime: Date.now(),
        };
      }
    }

    // Extract decision/risk info
    let decision = timeline.decision;
    let riskScore = timeline.riskScore;
    let threatLevel = timeline.threatLevel;
    let finalDecision = timeline.stages.find(s => s.agentId === "decision_agent")?.decision;
    let confidence = timeline.confidence;

    if (event.event_type === "THREAT_UPDATED" || event.event_type === "THREAT_ESCALATED") {
      const payload = event.payload || {};
      riskScore = (payload as any).risk_score;
      threatLevel = (payload as any).threat_level;
      confidence = (payload as any).confidence;
    }
    if (event.event_type === "DECISION_MADE" || event.event_type === "EMERGENCY_DECLARED") {
      const payload = event.payload || {};
      finalDecision = (payload as any).decision;
      if (finalDecision?.includes("EMERGENCY")) decision = "CRITICAL";
      else if (finalDecision?.includes("INTELLIGENCE")) decision = "UNCERTAIN";
      else if (finalDecision?.includes("MONITORING") || finalDecision?.includes("INCREASE")) decision = "SAFE";
    }

    // x402 branch: mark response as SKIPPED if decision is SAFE
    if (decision === "SAFE" && newStages[5]?.agentId === "x402_agent") {
      newStages[5] = { ...newStages[5], state: "SKIPPED" };
    }

    // x402 re-analysis: after x402 success, threat re-processes
    if (event.event_type === "INTELLIGENCE_RECEIVED") {
      const threatIdx = newStages.findIndex(s => s.agentId === "threat_agent");
      if (threatIdx >= 0) {
        newStages[threatIdx] = {
          ...newStages[threatIdx],
          state: "PROCESSING",
          startTime: Date.now(),
        };
      }
    }

    const completedCount = newStages.filter(s => s.state === "SUCCESS" || s.state === "SKIPPED").length;
    const isComplete = newStages.every(s => s.state === "SUCCESS" || s.state === "SKIPPED" || s.state === "ERROR");

    // Update risk/decision on stages
    newStages.forEach((stage, i) => {
      if (stage.agentId === "threat_agent" && riskScore !== undefined) {
        stage.riskScore = riskScore;
        stage.threatLevel = threatLevel;
      }
      if (stage.agentId === "decision_agent" && finalDecision !== undefined) {
        stage.decision = finalDecision;
      }
    });

    return {
      ...timeline,
      stages: newStages,
      decision,
      completedStages: completedCount,
      progress: Math.round((completedCount / timeline.totalStages) * 100),
      endTime: isComplete ? Date.now() : undefined,
      riskScore: riskScore ?? timeline.riskScore,
      threatLevel: threatLevel ?? timeline.threatLevel,
      confidence: confidence ?? timeline.confidence,
    };
  }, []);

  // Fetch data
  useEffect(() => {
    let mounted = true;
    const unsub = api.wsService.subscribe("*", (data: any) => {
      if (!mounted || !data?.payload) return;
      const eventType = data.type || data.event;
      if (eventType === "init" && data.payload?.events) {
        eventsRef.current = data.payload.events;
        setEvents([...eventsRef.current]);
      }
    });

    async function fetchData() {
      try {
        const [agentsRes, eventsRes] = await Promise.all([
          api.agents,
          api.getEvents({ limit: 100 }),
        ]);
        if (mounted) {
          const agentMap: Record<string, AgentHealth> = {};
          agentsRes.forEach(a => agentMap[a.agent_id] = a);
          setAgents(agentMap);
          eventsRef.current = eventsRes;
          setEvents([...eventsRes]);
        }
      } catch (e) {
        console.error("Pipeline data fetch error:", e);
      }
    }

    fetchData();
    api.wsService.connect();
    return () => { mounted = false; unsub(); };
  }, []);

  // Build active timeline from events
  useEffect(() => {
    if (events.length === 0) return;
    if (mode === "REPLAY") return;

    const incidentEvents = new Map<string, AgentEvent[]>();
    events.forEach(e => {
      const iid = e.incident_id || "unknown";
      if (!incidentEvents.has(iid)) incidentEvents.set(iid, []);
      incidentEvents.get(iid)!.push(e);
    });

    // Find the most active incident
    let mostRecentIncident = "";
    let mostRecentTime = 0;
    incidentEvents.forEach((evts, iid) => {
      const lastTime = Date.parse(evts[evts.length - 1]?.timestamp || "") || 0;
      if (lastTime > mostRecentTime) {
        mostRecentTime = lastTime;
        mostRecentIncident = iid;
      }
    });

    if (mostRecentIncident && mostRecentIncident !== "unknown") {
      let timeline = createTimeline(
        mostRecentIncident,
        incidentEvents.get(mostRecentIncident)?.[0]?.trace_id || ""
      );
      incidentEvents.get(mostRecentIncident)?.forEach(evt => {
        timeline = processEvent(evt, timeline);
      });
      setActiveTimeline(timeline);
    }
  }, [events, mode, createTimeline, processEvent]);

  const getStageDuration = (stage: PipelineStage): string => {
    if (!stage.duration) return "—";
    if (stage.duration < 1000) return `${stage.duration}ms`;
    return `${(stage.duration / 1000).toFixed(1)}s`;
  };

  const getDecisionColor = (d: string) => {
    switch (d) {
      case "CRITICAL": return "text-red-400 border-red-500/30 bg-red-500/10";
      case "UNCERTAIN": return "text-amber-400 border-amber-500/30 bg-amber-500/10";
      case "SAFE": return "text-green-400 border-green-500/30 bg-green-500/10";
      default: return "text-slate-400 border-slate-500/30 bg-slate-500/10";
    }
  };

  return (
    <div className="space-y-6">
      {/* Mode Toggle */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`px-3 py-1.5 rounded-lg text-sm font-medium border ${
            mode === "LIVE"
              ? "bg-green-500/15 border-green-500/30 text-green-400"
              : "border-slate-700 text-slate-400"
          }`} onClick={() => setMode("LIVE")} style={{ cursor: "pointer" }}>
            🟢 LIVE
          </div>
          <div className={`px-3 py-1.5 rounded-lg text-sm font-medium border ${
            mode === "REPLAY"
              ? "bg-blue-500/15 border-blue-500/30 text-blue-400"
              : "border-slate-700 text-slate-400"
          }`} onClick={() => setMode("REPLAY")} style={{ cursor: "pointer" }}>
            ▶ REPLAY
          </div>
        </div>
        {mode === "REPLAY" && (
          <div className="flex items-center gap-2">
            <button className="px-2 py-1 rounded bg-slate-700 text-slate-300 text-sm" onClick={() => setIsPaused(!isPaused)}>
              {isPaused ? "▶ Play" : "⏸ Pause"}
            </button>
            {[1, 2, 4].map(speed => (
              <button
                key={speed}
                className={`px-2 py-1 rounded text-sm ${playbackSpeed === speed ? "bg-sky-600 text-white" : "bg-slate-700 text-slate-300"}`}
                onClick={() => setPlaybackSpeed(speed)}
              >
                {speed}x
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Active Timeline */}
      {activeTimeline && (
        <section className="bg-bg-card rounded-2xl border border-slate-800/50 p-6" style={{ boxShadow: "0 8px 32px rgba(0,0,0,0.4)" }}>
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold">Active Pipeline</h2>
              <p className="text-sm text-slate-500 mt-1">
                Incident: {activeTimeline.incidentId} • Trace: {activeTimeline.traceId.substring(0, 8)}...
              </p>
            </div>
            <div className={`px-3 py-1.5 rounded-lg border text-sm font-medium ${getDecisionColor(activeTimeline.decision)}`}>
              {activeTimeline.decision}
            </div>
          </div>

          {/* Progress Bar */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-slate-400">Pipeline Progress</span>
              <span className="text-sm font-mono text-slate-300">{activeTimeline.completedStages} / {activeTimeline.totalStages} stages</span>
            </div>
            <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-sky-500 to-violet-500 rounded-full transition-all duration-700"
                style={{ width: `${activeTimeline.progress}%` }}
              />
            </div>
          </div>

          {/* Pipeline Visualization */}
          <div className="flex items-center gap-2 overflow-x-auto pb-4">
            {activeTimeline.stages.map((stage, idx) => {
              const def = AGENT_DEFINITIONS[stage.agentId];
              const stateColor = stage.state === "SUCCESS" ? "#22c55e"
                : stage.state === "PROCESSING" ? "#38bdf8"
                : stage.state === "ERROR" ? "#ef4444"
                : stage.state === "SKIPPED" ? "#6b7280"
                : "#334155";

              return (
                <React.Fragment key={stage.agentId}>
                  <div className="flex flex-col items-center min-w-[120px]">
                    {/* Node */}
                    <div
                      className="w-16 h-16 rounded-xl flex items-center justify-center text-2xl border-2 transition-all duration-500"
                      style={{
                        borderColor: stateColor,
                        background: `${stateColor}15`,
                        boxShadow: stage.state === "PROCESSING" ? `0 0 20px ${stateColor}40` : "none",
                        animation: stage.state === "PROCESSING" ? "pulse 2s infinite" : "none",
                      }}
                    >
                      {def.icon}
                    </div>
                    {/* Label */}
                    <p className="mt-2 text-xs font-semibold text-slate-200 text-center">{def.short}</p>
                    {/* State Badge */}
                    <span
                      className="mt-1 text-[10px] font-medium px-2 py-0.5 rounded-full"
                      style={{ background: `${stateColor}20`, color: stateColor }}
                    >
                      {stage.state}
                    </span>
                    {/* Duration */}
                    {stage.duration !== undefined && (
                      <p className="mt-1 text-[10px] text-slate-500 font-mono">{getStageDuration(stage)}</p>
                    )}
                    {/* Risk/Decision info */}
                    {stage.agentId === "threat_agent" && stage.riskScore !== undefined && (
                      <div className="mt-1 text-center">
                        <p className="text-xs font-mono text-amber-400">Risk: {stage.riskScore?.toFixed(1)}</p>
                        {stage.threatLevel && <p className="text-[10px] text-slate-400">{stage.threatLevel}</p>}
                      </div>
                    )}
                    {stage.agentId === "decision_agent" && stage.decision && (
                      <p className="mt-1 text-[10px] font-medium text-violet-400 text-center max-w-[120px]">{stage.decision}</p>
                    )}
                  </div>
                  {/* Connector arrow */}
                  {idx < activeTimeline.stages.length - 1 && (
                    <div className="flex items-center min-w-[40px]">
                      <div
                        className="h-0.5 flex-1 rounded"
                        style={{
                          background: stage.state === "SUCCESS"
                            ? `linear-gradient(90deg, #22c55e, ${activeTimeline.stages[idx + 1].state === "WAITING" ? "#334155" : stateColor})`
                            : "#1e293b",
                        }}
                      />
                      <svg width="12" height="12" viewBox="0 0 12 12" className="flex-shrink-0">
                        <path d="M4 2 L8 6 L4 10" fill="none" stroke={stage.state === "SUCCESS" ? "#22c55e" : "#334155"} strokeWidth="2" />
                      </svg>
                    </div>
                  )}
                </React.Fragment>
              );
            })}
          </div>

          {/* Decision Branch Visual */}
          <div className="mt-6 flex items-center justify-center gap-4">
            <div className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm ${activeTimeline.decision === "SAFE" ? "border-green-500/30 bg-green-500/10 text-green-400" : "border-slate-700 text-slate-600"}`}>
              <span>✓</span> SAFE → MONITOR
            </div>
            <div className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm ${activeTimeline.decision === "UNCERTAIN" ? "border-amber-500/30 bg-amber-500/10 text-amber-400" : "border-slate-700 text-slate-600"}`}>
              <span>⚠</span> UNCERTAIN → x402
            </div>
            <div className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm ${activeTimeline.decision === "CRITICAL" ? "border-red-500/30 bg-red-500/10 text-red-400" : "border-slate-700 text-slate-600"}`}>
              <span>🚨</span> CRITICAL → RESPONSE
            </div>
          </div>
        </section>
      )}

      {/* No active timeline */}
      {!activeTimeline && (
        <section className="bg-bg-card rounded-2xl border border-slate-800/50 p-12 text-center" style={{ boxShadow: "0 8px 32px rgba(0,0,0,0.4)" }}>
          <div className="text-4xl mb-4">🔄</div>
          <h2 className="text-lg font-semibold text-slate-200 mb-2">No Active Pipeline</h2>
          <p className="text-slate-500 max-w-md mx-auto">
            Waiting for agent events. When an incident enters the system, the pipeline visualization
            will show the real-time processing flow.
          </p>
          <div className="mt-6 p-4 rounded-lg bg-slate-900/50 border border-slate-800/50">
            <p className="text-xs text-slate-600 mb-2">Expected Pipeline Flow:</p>
            <div className="flex items-center justify-center gap-1 flex-wrap text-xs text-slate-500">
              <span>📷 Vision</span>
              <span>→</span>
              <span>🎤 Audio</span>
              <span>→</span>
              <span>📍 Context</span>
              <span>→</span>
              <span>⚠️ Threat</span>
              <span>→</span>
              <span>🧠 Decision</span>
              <span>→</span>
              <span className="text-amber-400">💳 x402</span>
              <span>→</span>
              <span className="text-red-400">🚨 Response</span>
            </div>
          </div>
        </section>
      )}

      {/* Recent Events Stream */}
      <section className="bg-bg-card rounded-2xl border border-slate-800/50 overflow-hidden" style={{ boxShadow: "0 8px 32px rgba(0,0,0,0.4)" }}>
        <div className="p-4 border-b border-slate-800/50 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Recent Events</h2>
          <span className="text-sm text-slate-500">{events.length} events</span>
        </div>
        <div className="max-h-96 overflow-y-auto">
          {events.length === 0 ? (
            <div className="p-8 text-center text-slate-500">No events recorded yet</div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="text-xs text-slate-500 uppercase tracking-wider border-b border-slate-800/50">
                  <th className="px-4 py-3 text-left">Time</th>
                  <th className="px-4 py-3 text-left">Agent</th>
                  <th className="px-4 py-3 text-left">Event</th>
                  <th className="px-4 py-3 text-left">Incident</th>
                  <th className="px-4 py-3 text-left">Trace</th>
                </tr>
              </thead>
              <tbody>
                {events.slice().reverse().map((evt, idx) => {
                  const agent = (evt.agent_id || evt.agent || "").replace("_agent", "").toUpperCase();
                  const agentColor = AGENT_DEFINITIONS[(evt.agent_id || evt.agent || "") as AgentId]
                    ? getAgentStatusColor("PROCESSING") : "#6b7280";
                  return (
                    <tr key={idx} className="border-b border-slate-800/30 hover:bg-slate-900/30 transition-colors">
                      <td className="px-4 py-2.5 text-sm font-mono text-slate-400">
                        {new Date(evt.timestamp).toLocaleTimeString()}
                      </td>
                      <td className="px-4 py-2.5 text-sm font-medium" style={{ color: agentColor }}>{agent}</td>
                      <td className="px-4 py-2.5 text-sm text-sky-400 font-mono">{evt.event_type}</td>
                      <td className="px-4 py-2.5 text-sm text-slate-400 font-mono">{evt.incident_id || "—"}</td>
                      <td className="px-4 py-2.5 text-xs text-slate-500 font-mono">{evt.trace_id?.substring(0, 8) || "—"}...</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </div>
  );
}
