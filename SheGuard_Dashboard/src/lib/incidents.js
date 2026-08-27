import { MEDIA_BASE_URL } from "../config";

const numberLike = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const firstDefined = (...values) => values.find((value) => value !== undefined && value !== null && value !== "");

export function toIncidentArray(payload) {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.incidents)) return payload.incidents;
  if (Array.isArray(payload?.data)) return payload.data;
  if (payload && typeof payload === "object") return [payload];
  return [];
}

export function mediaUrl(value) {
  if (!value) return "";
  if (/^https?:\/\//i.test(value)) return value;
  const normalized = String(value).replace(/^\/+/, "");
  if (normalized.startsWith("uploads/")) return `${MEDIA_BASE_URL}/`;
  return `${MEDIA_BASE_URL}/uploads/incidents/`;
}

export function normalizeIncident(raw, index = 0) {
  const latitude = numberLike(firstDefined(raw.latitude, raw.lat, raw.gps_lat, raw.location?.latitude, raw.location?.lat));
  const longitude = numberLike(firstDefined(raw.longitude, raw.lng, raw.lon, raw.gps_lng, raw.location?.longitude, raw.location?.lng, raw.location?.lon));
  const confidence = numberLike(firstDefined(raw.confidence, raw.score, raw.prediction_confidence));
  const status = String(firstDefined(raw.status, raw.emergency_status, raw.state, "active")).toLowerCase();
  const id = firstDefined(raw.id, raw.incident_id, raw.session_id, `incident-${index}`);
  const timestamp = firstDefined(raw.timestamp, raw.created_at, raw.updated_at, raw.time, raw.detected_at);
  const thumbnail = firstDefined(
    raw.thumbnail,
    raw.thumbnail_url,
    raw.image,
    raw.image_url,
    raw.frame_path,
    raw.frame_1,
    raw.frames?.[0],
    raw.media?.thumbnail,
    raw.media?.image,
  );
  const video = firstDefined(raw.video, raw.video_url, raw.video_path, raw.clip, raw.incident_video, raw.media?.video);

  // Phase F: Extract new fields
  const following = raw.following_relationship || raw.following || {};
  const riskScore = numberLike(firstDefined(raw.risk_score, raw.threat_score)) || 0;
  const riskLevel = firstDefined(raw.risk_level, raw.threat_level, "SAFE");
  const behaviors = raw.behaviors || [];
  const agentTimeline = raw.agent_timeline || [];
  const x402Meta = raw.x402_metadata || null;
  const intelligenceResult = raw.intelligence_result || null;

  return {
    ...raw,
    id,
    title: firstDefined(raw.title, raw.type, raw.event, raw.alert_type, "SOS Emergency"),
    description: firstDefined(raw.description, raw.message, raw.summary, "Possible emergency incident detected."),
    confidence: confidence ?? 0,
    timestamp: timestamp || new Date().toISOString(),
    latitude,
    longitude,
    address: firstDefined(raw.address, raw.place, raw.location?.address, "GPS coordinates pending"),
    status,
    emergencyStatus: firstDefined(raw.emergency_status, raw.status, "ACTIVE"),
    userId: firstDefined(raw.user_id, raw.userId, raw.user?.id),
    sessionId: firstDefined(raw.session_id, raw.sessionId, raw.session?.id, id),
    thumbnailUrl: mediaUrl(thumbnail),
    videoUrl: mediaUrl(video),
    frameUrl: mediaUrl(firstDefined(raw.frame_1, raw.frame1, raw.frames?.[0])),
    isResolved: ["resolved", "closed", "complete", "completed"].includes(status),
    severity: String(firstDefined(raw.severity, raw.priority, "critical")).toLowerCase(),
    raw,
    // Phase F new fields
    following_relationship: following,
    risk_score: riskScore,
    risk_level: riskLevel,
    behaviors,
    agent_timeline: agentTimeline,
    x402_metadata: x402Meta,
    intelligence_result: intelligenceResult,
  };
}

export function formatTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown time";
  return new Intl.DateTimeFormat("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    day: "2-digit",
    month: "short",
  }).format(date);
}

export function confidenceLabel(value) {
  const confidence = Number(value);
  if (!Number.isFinite(confidence)) return "0%";
  return `${Math.round(confidence <= 1 ? confidence * 100 : confidence)}%`;
}
