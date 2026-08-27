import type { AgentId, AgentNodeDef } from "../types";

// Canonical agent network topology derived from the actual SheGuard architecture.
// This is not arbitrary - it reflects the real event flow defined in core/orchestrator.py

export const AGENT_DEFINITIONS: Record<AgentId, AgentNodeDef> = {
  vision_agent: {
    id: "vision_agent",
    name: "Vision Agent",
    short: "VISION",
    x: 0,
    y: 2,
    z: 0,
    icon: "📷",
    description:
      "Analyzes CCTV/video frames to detect people, track movement, estimate poses, classify activities, and identify abnormal interactions. Produces visual risk signals and evidence.",
    inputs: ["video_frame", "camera_stream"],
    outputs: ["FRAME_PROCESSED"],
    dependencies: [],
    consumers: ["threat_agent"],
    communicatesWith: ["threat_agent"],
  },
  audio_agent: {
    id: "audio_agent",
    name: "Audio Agent",
    short: "AUDIO",
    x: 1.5,
    y: 1.2,
    z: 0.5,
    icon: "🎤",
    description:
      "Captures microphone audio, runs VAD, speech-to-text, keyword detection, and distress sound classification. Emits AUDIO_PROCESSED, KEYWORD_DETECTED, or DISTRESS_AUDIO_DETECTED events.",
    inputs: ["microphone_audio", "audio_stream"],
    outputs: ["AUDIO_PROCESSED", "KEYWORD_DETECTED", "DISTRESS_AUDIO_DETECTED"],
    dependencies: [],
    consumers: ["threat_agent"],
    communicatesWith: ["threat_agent"],
  },
  context_agent: {
    id: "context_agent",
    name: "Context Agent",
    short: "CONTEXT",
    x: 0,
    y: 0.5,
    z: 0,
    icon: "📍",
    description:
      "Enriches incidents with contextual risk factors: location safety score, time period risk, isolation status, nearby incidents, and security presence. Triggered by Vision via orchestrator.",
    inputs: ["camera_id", "persons_detected", "interaction_detected", "activity_label"],
    outputs: ["CONTEXT_UPDATED"],
    dependencies: ["vision_agent"],
    consumers: ["threat_agent"],
    communicatesWith: ["vision_agent", "threat_agent"],
  },
  threat_agent: {
    id: "threat_agent",
    name: "Threat Analysis Agent",
    short: "THREAT",
    x: 0,
    y: -0.5,
    z: 0,
    icon: "⚠️",
    description:
      "Fuses Vision, Audio, and Context signals into a unified risk score (0-100) with threat level (SAFE/WARNING/HIGH/CRITICAL) and threat type. Optionally incorporates x402 intelligence for re-analysis.",
    inputs: ["vision_signal", "audio_signal", "context_signal", "intelligence"],
    outputs: ["THREAT_UPDATED", "THREAT_ESCALATED"],
    dependencies: ["vision_agent", "audio_agent", "context_agent"],
    consumers: ["decision_agent"],
    communicatesWith: ["vision_agent", "audio_agent", "context_agent", "decision_agent", "x402_agent"],
  },
  decision_agent: {
    id: "decision_agent",
    name: "Decision Agent",
    short: "DECISION",
    x: 0,
    y: -1.5,
    z: 0,
    icon: "🧠",
    description:
      "Evaluates threat assessment and decides: CONTINUE_MONITORING, INCREASE_MONITORING, CREATE_INCIDENT, REQUEST_ADDITIONAL_INTELLIGENCE (x402), or EMERGENCY_RESPONSE. Routes to next agent.",
    inputs: ["risk_score", "threat_level", "confidence", "uncertainty", "intelligence"],
    outputs: ["DECISION_MADE", "EMERGENCY_DECLARED", "ADDITIONAL_INTELLIGENCE_REQUIRED"],
    dependencies: ["threat_agent"],
    consumers: ["response_agent", "x402_agent"],
    communicatesWith: ["threat_agent", "response_agent", "x402_agent"],
  },
  x402_agent: {
    id: "x402_agent",
    name: "x402 Agent",
    short: "x402",
    x: -1.8,
    y: -1.5,
    z: 0,
    icon: "💳",
    description:
      "Handles pay-for-intelligence flow via x402 protocol (Algorand). When Decision requests intelligence, x402 pays the safety-intelligence service and returns enhanced risk analysis for threat re-evaluation.",
    inputs: ["incident_id", "trace_id", "risk_score", "service", "reason"],
    outputs: ["INTELLIGENCE_RECEIVED"],
    dependencies: ["decision_agent"],
    consumers: ["threat_agent"],
    communicatesWith: ["decision_agent", "threat_agent"],
  },
  response_agent: {
    id: "response_agent",
    name: "Response Agent",
    short: "RESPONSE",
    x: 1.8,
    y: -1.5,
    z: 0,
    icon: "🚨",
    description:
      "Executes emergency response: creates incident record, secures video evidence, resolves location, notifies guardian via Telegram, updates dashboard, and triggers emergency dispatch if CRITICAL.",
    inputs: ["incident_id", "trace_id", "risk_score", "threat_level", "threat_type", "confidence", "vision_data", "audio_data", "context_data", "intelligence_data"],
    outputs: ["RESPONSE_COMPLETE", "INCIDENT_CREATED"],
    dependencies: ["decision_agent"],
    consumers: [],
    communicatesWith: ["decision_agent"],
  },
};

// Ordered for pipeline visualization
export const PIPELINE_ORDER: AgentId[] = [
  "vision_agent",
  "audio_agent",
  "context_agent",
  "threat_agent",
  "decision_agent",
  "x402_agent",
  "response_agent",
];

export const AGENT_ICONS: Record<AgentId, string> = {
  vision_agent: "📷",
  audio_agent: "🎤",
  context_agent: "📍",
  threat_agent: "⚠️",
  decision_agent: "🧠",
  x402_agent: "💳",
  response_agent: "🚨",
};

export const AGENT_COLORS: Record<AgentId, string> = {
  vision_agent: "#38bdf8",
  audio_agent: "#22d3ee",
  context_agent: "#4ade80",
  threat_agent: "#fbbf24",
  decision_agent: "#a78bfa",
  x402_agent: "#f472b6",
  response_agent: "#fb923c",
};

export const STATUS_COLORS: Record<string, string> = {
  HEALTHY: "#22c55e",
  DEGRADED: "#fbbf24",
  WARNING: "#f97316",
  ERROR: "#ef4444",
  OFFLINE: "#6b7280",
  PROCESSING: "#38bdf8",
  READY: "#22c55e",
  RUNNING: "#38bdf8",
  INITIALIZING: "#fbbf24",
  STOPPED: "#6b7280",
  UNKNOWN: "#6b7280",
  CRITICAL: "#ef4444",
};

// Re-export AgentId type
export type { AgentId } from "../types";

export function getAgentDef(id: AgentId): AgentNodeDef {
  return AGENT_DEFINITIONS[id];
}

export function getAgentStatusColor(status: string): string {
  return STATUS_COLORS[status] || STATUS_COLORS.UNKNOWN;
}
