// API Configuration
import { getEnv } from './lib/env';

export const API_BASE_URL = getEnv('VITE_API_BASE_URL', 'http://localhost:8000');
export const WS_BASE_URL = getEnv('VITE_WS_BASE_URL', deriveWsUrl(API_BASE_URL));
export const MEDIA_BASE_URL = getEnv('VITE_MEDIA_BASE_URL', API_BASE_URL);

// Polling interval for fallback (2 seconds)
export const REFRESH_INTERVAL_MS = 2000;

// WebSocket reconnection settings
export const WS_RECONNECT_BASE_MS = 1000;
export const WS_RECONNECT_MAX_MS = 30000;
export const WS_RECONNECT_JITTER = 0.3;

// Connection timeout
export const API_TIMEOUT_MS = 10000;

// Backend health check interval
export const BACKEND_HEALTH_CHECK_INTERVAL_MS = 10000;

// Helper to derive WebSocket URL from HTTP URL
function deriveWsUrl(httpUrl) {
  try {
    const url = new URL(httpUrl);
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    return url.toString().replace(/\/$/, '');
  } catch {
    return 'ws://localhost:8000';
  }
}

// Connection status constants
export const CONNECTION_STATUS = {
  CONNECTED: 'connected',
  CONNECTING: 'connecting',
  RECONNECTING: 'reconnecting',
  DISCONNECTED: 'disconnected',
  ERROR: 'error',
};

// Event types for realtime system
export const REALTIME_EVENTS = {
  INCIDENT_CREATED: 'incident.created',
  INCIDENT_UPDATED: 'incident.updated',
  POLICE_ALERT: 'police_alert',
  INCIDENT_BATCHED: 'incident.batched',
  INCIDENT_MERGED: 'incident.merged',
  EMERGENCY_STARTED: 'emergency.started',
  TRACKING_UPDATE: 'tracking_update',
  INCIDENT_NEW: 'incident.new',
  THREAT_ESCALATION: 'threat_escalation',
  CCTV_OFFLINE: 'cctv_offline',
  AI_DETECTION: 'ai_detection',
  NEW_EVIDENCE: 'new_evidence',
  EMERGENCY_RESOLVED: 'emergency_resolved',
  EMERGENCY_ACKNOWLEDGED: 'emergency_acknowledged',
  EMERGENCY_RESPONDING: 'emergency_responding',
};

// Health check status
export const HEALTH_STATUS = {
  HEALTHY: 'healthy',
  DEGRADED: 'degraded',
  DOWN: 'down',
  UNKNOWN: 'unknown',
};

export default {
  API_BASE_URL,
  WS_BASE_URL,
  MEDIA_BASE_URL,
  REFRESH_INTERVAL_MS,
  WS_RECONNECT_BASE_MS,
  WS_RECONNECT_MAX_MS,
  WS_RECONNECT_JITTER,
  API_TIMEOUT_MS,
  BACKEND_HEALTH_CHECK_INTERVAL_MS,
  CONNECTION_STATUS,
  REALTIME_EVENTS,
  HEALTH_STATUS,
};