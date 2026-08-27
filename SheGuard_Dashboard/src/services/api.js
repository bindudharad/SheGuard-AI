import axios from "axios";
import {
  API_BASE_URL,
  MEDIA_BASE_URL,
  API_TIMEOUT_MS,
  HEALTH_STATUS,
  CONNECTION_STATUS,
} from "../config";

const TOKEN_KEY = "sheguard_dashboard_token";
const USER_KEY = "sheguard_dashboard_user";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT_MS,
});

// Request interceptor to add auth header
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
  // Update axios default headers
  if (token) {
    api.defaults.headers.common.Authorization = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common.Authorization;
  }
}

export function getStoredUser() {
  try {
    const user = localStorage.getItem(USER_KEY);
    return user ? JSON.parse(user) : null;
  } catch {
    return null;
  }
}

export function setStoredUser(user) {
  if (user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  } else {
    localStorage.removeItem(USER_KEY);
  }
}

export function isAuthenticated() {
  return Boolean(getToken());
}

export async function login(phoneNumber, password) {
  const { data } = await api.post("/login", { phone_number: phoneNumber, password });
  if (!data?.access_token) {
    throw new Error("Login succeeded but no access token was returned.");
  }
  setToken(data.access_token);
  setStoredUser({
    user_id: data.user_id,
    full_name: data.full_name,
    phone_number: data.phone_number,
  });
  return data;
}

export function logout() {
  setToken(null);
  setStoredUser(null);
  localStorage.removeItem("sheguard_sessions");
  return true;
}

// Incident APIs
export async function getIncidents(limit = 50) {
  const { data } = await api.get("/incidents", { params: { limit } });
  return data;
}

export async function getLatestIncidents(limit = 10) {
  const { data } = await api.get("/incidents/latest", { params: { limit } });
  return data;
}

export async function getLatestIncident() {
  const { data } = await api.get("/incidents/latest", { params: { limit: 1 } });
  return Array.isArray(data) && data.length > 0 ? data[0] : null;
}

export async function getIncident(incidentId) {
  const { data } = await api.get(`/incidents/${incidentId}`);
  return data;
}

export async function linkIncidentUser(incidentId, userId, distanceMeters, matchMethod) {
  const { data } = await api.post("/incidents/link-user", {
    incident_id: incidentId,
    user_id: userId,
    distance_meters: distanceMeters,
    match_method: matchMethod,
  });
  return data;
}

export async function getIncidentHistory(userId) {
  const { data } = await api.get(`/incident/history/${userId}`);
  return data;
}

export async function searchIncidents(query, limit = 5) {
  const { data } = await api.get("/incident/search", { params: { q: query, limit } });
  return data;
}

// Emergency Session APIs
export async function startEmergencySession(payload) {
  const { data } = await api.post("/emergency/start", payload);
  return data;
}

export async function getEmergencySession(sessionId) {
  const { data } = await api.get(`/emergency/session/${sessionId}`);
  return data;
}

export async function acknowledgeEmergency(sessionId) {
  const { data } = await api.post(`/emergency/session/${sessionId}/acknowledge`);
  return data;
}

export async function respondEmergency(sessionId) {
  const { data } = await api.post(`/emergency/session/${sessionId}/respond`);
  return data;
}

export async function resolveEmergency(sessionId) {
  const { data } = await api.post(`/emergency/session/${sessionId}/resolve`);
  return data;
}

// Location/Tracking APIs
export async function updateLocation(payload) {
  const { data } = await api.post("/location/update", payload);
  return data;
}

export async function getLiveLocation(userId) {
  const { data } = await api.get(`/location/live/${userId}`);
  return data;
}

export async function startTracking(payload) {
  const { data } = await api.post("/tracking/start", payload);
  return data;
}

export async function updateTracking(payload) {
  const { data } = await api.post("/tracking/update", payload);
  return data;
}

export async function getLiveTracking(sessionId) {
  const { data } = await api.get(`/tracking/live/${sessionId}`);
  return data;
}

export async function getTrackingHistory(sessionId) {
  const { data } = await api.get(`/tracking/history/${sessionId}`);
  return data;
}

export async function getTrackingStream(sessionId) {
  const { data } = await api.get(`/location/stream/${sessionId}`);
  return data;
}

// Camera/CCTV APIs
export async function getCameras() {
  const { data } = await api.get("/camera/list");
  return data;
}

export async function getCameraHealth() {
  const { data } = await api.get("/camera/health");
  return data;
}

export async function registerCamera(payload) {
  const { data } = await api.post("/camera/register", payload);
  return data;
}

// User/Profile APIs
export async function getUserProfile(userId) {
  const { data } = await api.get(`/profile/${userId}`);
  return data;
}

export async function getUserContacts(userId) {
  const { data } = await api.get(`/contacts/${userId}`);
  return data;
}

// Evidence APIs
export async function getEvidence(incidentId) {
  const { data } = await api.get(`/evidence/${incidentId}`);
  return data;
}

export async function getSecureEvidence(incidentId) {
  const { data } = await api.get(`/secure/evidence/${incidentId}`);
  return data;
}

export async function getEvidenceFile(path) {
  const { data } = await api.get("/evidence/file", { params: { path }, responseType: "blob" });
  return data;
}

export async function uploadEvidence(payload) {
  const { data } = await api.post("/evidence/upload", payload);
  return data;
}

// System APIs
export async function getSystemLocalNetwork() {
  const { data } = await api.get("/system/local-network");
  return data;
}

export async function checkBackendHealth() {
  try {
    const { data } = await api.get("/");
    return { status: HEALTH_STATUS.HEALTHY, data };
  } catch (err) {
    return { status: HEALTH_STATUS.DOWN, error: err };
  }
}

// Media URL helper
export function getMediaUrl(path) {
  if (!path) return null;
  if (/^https?:\/\//i.test(path)) return path;
  const normalized = String(path).replace(/^\/+/, "");
  if (normalized.startsWith("uploads/")) {
    return `${MEDIA_BASE_URL}/${normalized}`;
  }
  return `${MEDIA_BASE_URL}/uploads/incidents/${normalized}`;
}

// Error handling helper
export function handleApiError(error, defaultMessage = "Request failed") {
  if (error.response) {
    const { status, data } = error.response;
    switch (status) {
      case 401:
        return "Session expired. Please login again.";
      case 403:
        return data?.detail || "Access denied";
      case 404:
        return data?.detail || "Resource not found.";
      case 500:
        return "Server error. Please try again later.";
      default:
        return data?.detail || `${defaultMessage} (${status})`;
    }
  } else if (error.request) {
    return "Network error. Cannot reach backend.";
  }
  return error.message || defaultMessage;
}

// Connection status helper
export function getConnectionStatus() {
  return api.defaults.headers.common.Authorization ? CONNECTION_STATUS.CONNECTED : CONNECTION_STATUS.DISCONNECTED;
}

export default api;
