// Canonical monitoring types for the SheGuard Agent Operations Dashboard.
// These mirror the backend monitoring API (monitor.py) and the agent core schemas.

export type AgentId =
  | "vision_agent"
  | "audio_agent"
  | "context_agent"
  | "threat_agent"
  | "decision_agent"
  | "x402_agent"
  | "response_agent";

export type AgentStatus =
  | "HEALTHY"
  | "DEGRADED"
  | "WARNING"
  | "ERROR"
  | "OFFLINE"
  | "PROCESSING"
  | "UNKNOWN"
  | "READY"
  | "RUNNING"
  | "INITIALIZING"
  | "STOPPED";

export interface AgentHealth {
  agent_id: string;
  name: string;
  status: AgentStatus;
  uptime: string;
  last_heartbeat?: string | null;
  latency?: number;
  cpu: number;
  memory: number;
  events_processed: number;
  error_count: number;
  warning_count: number;
  current_state: string;
  version: string;
  details?: Record<string, unknown>;
  component_status?: Record<string, string>;
  current_task?: string;
  avg_latency_ms?: number;
}

export interface ComponentStatus {
  name: string;
  status: string;
}

export interface AgentEvent {
  event_id?: string;
  incident_id?: string | null;
  trace_id?: string | null;
  agent_id?: string;
  agent?: string;
  event_type: string;
  severity?: string;
  timestamp: string;
  payload?: Record<string, unknown>;
  data?: Record<string, unknown>;
  // For websocket broadcast envelope
  event?: string;
}

export interface Incident {
  incident_id: string;
  trace_id?: string | null;
  severity: string;
  threat_level: string;
  confidence: number;
  status: string;
  created_at: string;
  updated_at: string;
  current_agent?: string | null;
}

export interface IncidentDetail {
  incident_id: string;
  trace_id?: string | null;
  state: string;
  created_at: string;
  updated_at: string;
  last_decision?: string | null;
  pending_intelligence?: boolean;
  vision_data?: Record<string, unknown> | null;
  audio_data?: Record<string, unknown> | null;
  context_data?: Record<string, unknown> | null;
  threat_data?: Record<string, unknown> | null;
  decision_data?: Record<string, unknown> | null;
  response_data?: Record<string, unknown> | null;
  intelligence_data?: Record<string, unknown> | null;
}

export interface ResponseRecord {
  incident_id: string;
  trace_id?: string | null;
  timestamp: string;
  status: string;
  incident_created: boolean;
  evidence_stored: boolean;
  location_recorded: boolean;
  guardian_notified: boolean;
  telegram_sent: boolean;
  mobile_sent: boolean;
  backend_updated: boolean;
  dashboard_updated: boolean;
  details: Record<string, unknown>;
}

export interface X402Status {
  mode: "simulation" | "testnet" | "mainnet";
  status: AgentStatus;
  wallet_address?: string;
  network?: string;
  last_payment?: Record<string, unknown> | null;
  intelligence_requests: number;
  successful_payments: number;
  failed_payments: number;
}

export interface SystemHealth {
  overall_status: AgentStatus;
  agents: AgentHealth[];
  event_bus: Record<string, unknown>;
  backend: Record<string, unknown>;
  database: Record<string, unknown>;
  storage: Record<string, unknown>;
  camera: Record<string, unknown>;
  microphone: Record<string, unknown>;
  network: Record<string, unknown>;
  telegram: Record<string, unknown>;
  x402: Record<string, unknown>;
}

export interface SystemMetrics {
  uptime: string;
  total_agents: number;
  active_incidents: number;
  events_per_second: number;
  cpu: number;
  memory: number;
  event_history_size: number;
}

export interface TestSummary {
  summary: {
    total: number;
    passed: number;
    failed: number;
    skipped: number;
  };
  categories: TestCategory[];
}

export interface TestCategory {
  name: string;
  passed: number;
  failed: number;
  skipped: number;
  last_run: string;
}

export type ConnectionState = "LIVE" | "RECONNECTING" | "OFFLINE";

export type DashboardMode = "live" | "demo";

export interface AgentNodeDef {
  id: AgentId;
  name: string;
  short: string;
  x: number;
  y: number;
  z: number;
  icon: string;
  description: string;
  inputs: string[];
  outputs: string[];
  dependencies: string[];
  consumers: string[];
  communicatesWith: AgentId[];
}
