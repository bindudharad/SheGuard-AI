# DASHBOARD_API_MAP.md

## SheGuard Dashboard - Complete API & Realtime Map

**Generated:** 2026-08-22  
**Dashboard:** C:\Programs\codex\SheGuard\SheGuard_Dashboard  
**Backend:** C:\Programs\codex\SheGuard\SheGuard_Backend

---

## REST API Endpoints

### Authentication
| Method | Endpoint | Request | Response | Auth |
|--------|----------|---------|----------|------|
| POST | `/register` | `{full_name, phone_number, password, profile_photo?}` | `{user_id, full_name, phone_number, access_token, token_type}` | None |
| POST | `/login` | `{phone_number, password}` | `{status, user_id, full_name, phone_number, access_token, token_type}` | None |

### Incidents
| Method | Endpoint | Request | Response | Auth |
|--------|----------|---------|----------|------|
| POST | `/incident/create` | `IncidentCreate` (multipart) | `{incident, evidence, session?, user?, alert}` | Bearer |
| POST | `/incidents/create` | `IncidentCreate` (multipart) | `{incident, evidence, session?, user?, alert}` | Bearer |
| GET | `/incidents` | `?limit=50` | `{incidents: [...]}` | Bearer |
| GET | `/incidents/latest` | `?limit=10` | `{incidents: [...]}` | Bearer |
| GET | `/incidents/{incident_id}` | - | Incident object | Bearer |
| POST | `/incidents/link-user` | `{incident_id, user_id, distance_meters, match_method}` | Link result | Bearer |
| GET | `/incident/history/{user_id}` | - | `{incidents: [...]}` | Bearer |
| GET | `/incident/live` | - | Live incident data | Bearer |
| GET | `/incident/search` | `?q=query&limit=5` | `{incidents: [...]}` | Bearer |

### Emergency Sessions
| Method | Endpoint | Request | Response | Auth |
|--------|----------|---------|----------|------|
| POST | `/emergency/start` | `EmergencyStartRequest` | `{status, session}` | Bearer |
| GET | `/emergency/session/{session_id}` | - | `{session, incident?}` | Bearer |
| POST | `/emergency/session/{session_id}/acknowledge` | - | `{status, session}` | Bearer |
| POST | `/emergency/session/{session_id}/respond` | - | `{status, session}` | Bearer |
| POST | `/emergency/session/{session_id}/resolve` | - | `{status, session}` | Bearer |

### Location & Tracking
| Method | Endpoint | Request | Response | Auth |
|--------|----------|---------|----------|------|
| POST | `/location/update` | `LocationUpdate` | Location object | Bearer |
| GET | `/location/live/{user_id}` | - | LiveLocation object | Bearer |
| POST | `/tracking/start` | `TrackingStart` | TrackingSession object | Bearer |
| POST | `/tracking/update` | `TrackingUpdate` | Updated session | Bearer |
| GET | `/tracking/live/{session_id}` | - | Live tracking data | Bearer |
| GET | `/tracking/history/{session_id}` | - | `{locations: [...]}` | Bearer |
| GET | `/location/stream/{session_id}` | - | SSE/Stream of locations | Bearer |

### Cameras (CCTV)
| Method | Endpoint | Request | Response | Auth |
|--------|----------|---------|----------|------|
| POST | `/camera/register` | `CameraCreate` | Camera object | Bearer |
| GET | `/camera/list` | - | `{count, cameras: [...]}` | Bearer |
| GET | `/camera/health` | - | `{registered: [...], runtime: {...}}` | Bearer |

### Users & Contacts
| Method | Endpoint | Request | Response | Auth |
|--------|----------|---------|----------|------|
| GET | `/profile/{user_id}` | - | User object | Bearer |
| POST | `/contacts/add` | `ContactCreate` | Contact object | Bearer |
| GET | `/contacts/{user_id}` | - | `{count, contacts: [...]}` | Bearer |

### Evidence
| Method | Endpoint | Request | Response | Auth |
|--------|----------|---------|----------|------|
| GET | `/evidence/{incident_id}` | - | `{evidence: [...], evidence_records: [...]}` | Bearer |
| GET | `/secure/evidence/{incident_id}` | - | `{evidence: [...]}` | Bearer |
| GET | `/evidence/file` | `?path=...` | File blob | Bearer |
| POST | `/evidence/upload` | `EvidenceUpload` | Upload result | Bearer |

### System
| Method | Endpoint | Request | Response | Auth |
|--------|----------|---------|----------|------|
| GET | `/` | - | `{status: "ok", service: "SheGuard Backend", version}` | None |
| GET | `/health/gpu` | - | GPU status object | None |
| GET | `/system/local-network` | - | `{local_ip, port, base_url, tracking_base_url, wifi_accessible, warnings, required_run_command}` | None |

---

## WebSocket Endpoints

### Global Events
| Endpoint | Protocol | Auth | Events |
|----------|----------|------|--------|
| `/ws/live` | WS/WSS | `?token=JWT` | All global events |

**Connection:**
```javascript
const ws = new WebSocket(`wss://api.example.com/ws/live?token=${JWT}`);
```

**Message Format:**
```json
{
  "event": "incident.created",
  "payload": { ... }
}
```

**Events Published:**
| Event | Description | Payload |
|-------|-------------|---------|
| `incident.created` | New incident created | Incident object |
| `incident.batched` | Incidents batched | Batch info |
| `incident.merged` | Incidents merged | Merged incident |
| `emergency.started` | Emergency session started | `{session_id, user_id, user_name, phone_number, trigger_source, started_at, latitude, longitude}` |
| `tracking_update` | Location update | `{session: {...}, location: {...}}` |
| `incident.new` | New incident in session | `{incident: ..., session_id: ...}` |
| `threat_escalation` | Threat level increased | `{session_id, threat_level, ai_summary}` |
| `cctv_offline` | Camera went offline | `{session_id, camera_id}` |
| `ai_detection` | AI detection event | `{session_id, detection_type, confidence}` |
| `new_evidence` | New evidence available | `{session_id, incident_id}` |
| `emergency_resolved` | Emergency resolved | `{session_id, ...}` |
| `emergency_acknowledged` | Emergency acknowledged | `{session_id, ...}` |
| `emergency_responding` | Response started | `{session_id, ...}` |

### Session-Specific Events
| Endpoint | Protocol | Auth | Events |
|----------|----------|------|--------|
| `/ws/emergency/{session_id}` | WS/WSS | `?token=JWT` | Session-specific events |

**Connection:**
```javascript
const ws = new WebSocket(`wss://api.example.com/ws/emergency/${sessionId}?token=${JWT}`);
```

**Events:** Subset of global events filtered to the specific session.

---

## Dashboard Service Functions (src/services/api.js)

### Authentication
```javascript
// Login
login(phoneNumber, password) -> Promise<{access_token, user_id, full_name, phone_number}>

// Logout
logout() -> void

// Token management
getToken() -> string | null
setToken(token) -> void
isAuthenticated() -> boolean

// User profile
getStoredUser() -> User | null
setStoredUser(user) -> void
```

### Incidents
```javascript
getIncidents(limit = 50) -> Promise<IncidentResponse>
getLatestIncidents(limit = 10) -> Promise<IncidentResponse>
getLatestIncident() -> Promise<Incident | null>
getIncident(incidentId) -> Promise<Incident>
linkIncidentUser(incidentId, userId, distanceMeters, matchMethod) -> Promise<any>
getIncidentHistory(userId) -> Promise<any>
searchIncidents(query, limit = 5) -> Promise<any>
```

### Emergency Sessions
```javascript
startEmergencySession(payload) -> Promise<any>
getEmergencySession(sessionId) -> Promise<any>
acknowledgeEmergency(sessionId) -> Promise<any>
respondEmergency(sessionId) -> Promise<any>
resolveEmergency(sessionId) -> Promise<any>
```

### Location & Tracking
```javascript
updateLocation(payload) -> Promise<any>
getLiveLocation(userId) -> Promise<any>
startTracking(payload) -> Promise<any>
updateTracking(payload) -> Promise<any>
getLiveTracking(sessionId) -> Promise<any>
getTrackingHistory(sessionId) -> Promise<any>
getTrackingStream(sessionId) -> Promise<any>
```

### Cameras
```javascript
getCameras() -> Promise<{cameras: Camera[]}>
getCameraHealth() -> Promise<{registered: Camera[], runtime: any}>
registerCamera(payload) -> Promise<Camera>
```

### Users & Contacts
```javascript
getUserProfile(userId) -> Promise<User>
getUserContacts(userId) -> Promise<{contacts: Contact[]}>
```

### Evidence
```javascript
getEvidence(incidentId) -> Promise<any>
getSecureEvidence(incidentId) -> Promise<any>
getEvidenceFile(path) -> Promise<Blob>
uploadEvidence(payload) -> Promise<any>
```

### System
```javascript
getSystemLocalNetwork() -> Promise<any>
checkBackendHealth() -> Promise<{status, data|error}>
```

### Utilities
```javascript
getMediaUrl(path) -> string
handleApiError(error, defaultMessage) -> string
getConnectionStatus() -> string
```

---

## Frontend Hooks

### useIncidents()
```javascript
{
  incidents: Incident[],
  latestIncident: Incident | null,
  error: string,
  isLoading: boolean,
  lastUpdated: Date | null,
  refresh: () => Promise<void>,
  stats: {activeCount, resolvedCount, criticalCount},
  backendStatus: "connected" | "error"
}
```

### useRealtime(options)
```javascript
{
  status: "connected" | "connecting" | "reconnecting" | "disconnected" | "error",
  lastMessage: any,
  error: string,
  connect: () => void,
  disconnect: () => void,
  send: (data) => boolean,
  isConnected: boolean,
  isConnecting: boolean
}

// Options:
// - onMessage: (message) => void
// - sessionId: string (for session-specific WS)
// - enabled: boolean
// - autoReconnect: boolean
// - onStatusChange: (status) => void
```

### useEmergencySessions()
```javascript
{
  // Emergency sessions
  emergencySessions: EmergencySession[],
  activeCount: number,
  highRiskCount: number,
  selectedSessionId: string | null,
  selectedSession: EmergencySession | null,
  selectSession: (sessionId) => void,
  
  // Tracking sessions
  trackingSessions: TrackingSession[],
  
  // Notifications
  notifications: Notification[],
  unreadCount: number,
  clearUnread: () => void,
  
  // Status
  realtimeStatus: string,
  backendError: string | null,
  isLoading: boolean,
  
  // Actions
  refreshIncidents: () => Promise<void>
}
```

---

## EmergencySession Model (Frontend)
```typescript
interface EmergencySession {
  sessionId: string;
  userId: number;
  fullName: string;
  maskedPhone: string;
  triggerSource: "SOS" | "VOICE_HELP" | "ai_cctv" | string;
  startedAt: string;
  status: "ACTIVE" | "ACKNOWLEDGED" | "RESPONDING" | "RESOLVED";
  threatLevel: "SAFE" | "LOW" | "MEDIUM" | "WARNING" | "HIGH" | "CRITICAL" | "EMERGENCY";
  threatScore: number;
  latestLocation: {
    latitude: number | null;
    longitude: number | null;
    timestamp: string;
  };
  locationUpdatedAt: string;
  trackingStatus: "ACTIVE" | "PAUSED" | "STOPPED" | "DEGRADED" | "LOST";
  nearbyCameras: CameraWithDistance[];
  latestIncident: Incident | null;
  incidentCount: number;
  unreadAlerts: number;
  deviceStatus: "CONNECTED" | "DELAYED" | "LOST";
  emergencySession: any; // Raw backend session object
}
```

---

## Camera Model (Frontend)
```typescript
interface Camera {
  camera_id: string;
  camera_name: string;
  ip_address: string;
  rtsp_url: string;
  latitude: number;
  longitude: number;
  online_status: "online" | "offline" | "degraded" | "unknown";
  ai_enabled: boolean;
  distance?: number; // Added by frontend for nearby cameras
}
```

---

## TrackingSession Model (Frontend)
```typescript
interface TrackingSession {
  sessionId: string;
  userId: number;
  fullName: string;
  latitude: number;
  longitude: number;
  speed: number;
  threat: string;
  lastUpdate: string;
  gpsStatus: "GOOD" | "DELAYED" | "LOST";
  status: "ACTIVE" | "PAUSED" | "STOPPED" | "DEGRADED" | "LOST";
  path?: [number, number][]; // Historical route
}
```

---

## Notification Model (Frontend)
```typescript
interface Notification {
  id: number;
  type: "new_emergency" | "threat_escalation" | "tracking_lost" | "cctv_offline" | "ai_detection" | "new_evidence" | "emergency_resolved" | "default";
  sessionId: string;
  message: string;
  timestamp: string;
}
```

---

## Configuration (src/config.js)

```javascript
// Environment variables (Vite)
VITE_API_BASE_URL = "http://localhost:8000"  // Required
VITE_WS_BASE_URL = "ws://localhost:8000"     // Optional, auto-derived
VITE_MEDIA_BASE_URL = "http://localhost:8000" // Optional, defaults to API

// Derived constants
API_BASE_URL, WS_BASE_URL, MEDIA_BASE_URL
REFRESH_INTERVAL_MS = 2000
WS_RECONNECT_BASE_MS = 1000
WS_RECONNECT_MAX_MS = 30000
WS_RECONNECT_JITTER = 0.3
API_TIMEOUT_MS = 10000
BACKEND_HEALTH_CHECK_INTERVAL_MS = 10000

// Status enums
CONNECTION_STATUS = {CONNECTED, CONNECTING, RECONNECTING, DISCONNECTED, ERROR}
HEALTH_STATUS = {HEALTHY, DEGRADED, DOWN}
REALTIME_EVENTS = {...} // All event type strings
```

---

## Error Response Format (Backend)

```json
{
  "detail": "Error message",
  "status_code": 400
}
```

**Common HTTP Status Codes:**
- 200: Success
- 201: Created
- 400: Bad Request (validation error)
- 401: Unauthorized (token expired/invalid)
- 403: Forbidden (access denied)
- 404: Not Found
- 409: Conflict (duplicate)
- 422: Unprocessable Entity (validation)
- 500: Internal Server Error

---

## Frontend Error Handling

All API calls wrapped with `handleApiError()` which maps:
- 401 → "Session expired. Please login again." + logout
- 403 → "Access denied" or backend detail
- 404 → "Resource not found." or backend detail
- 500 → "Server error. Please try again later."
- Network error → "Network error. Cannot reach backend."

---

## Media URL Construction

```javascript
// Input: "/uploads/incidents/abc.jpg" or "uploads/incidents/abc.jpg" or "abc.jpg"
// Output: "http://localhost:8000/uploads/incidents/abc.jpg"

getMediaUrl(path) -> string
```

**Rules:**
- Absolute URLs passed through
- Paths starting with "uploads/" → `${MEDIA_BASE_URL}/${path}`
- Other paths → `${MEDIA_BASE_URL}/uploads/incidents/${path}`

---

## Data Flow Summary

```
MOBILE APP (SOS/HELP)
    ↓ POST /emergency/start
BACKEND
    ↓ Creates EmergencySession + TrackingSession
    ↓ Broadcasts "emergency.started" via WebSocket
    ↓ Polling /incidents/latest (2s)
DASHBOARD
    ↓ useEmergencySessions builds sessions from incidents
    ↓ Real-time updates via WebSocket
    ↓ Map shows all victims + CCTV + routes
    ↓ Police actions → POST /emergency/session/{id}/acknowledge|respond|resolve
    ↓ Backend updates session + broadcasts status change
    ↓ All dashboards receive real-time update
```

---

## Required Backend Running Commands

```bash
# Backend
cd C:\Programs\codex\SheGuard\SheGuard_Backend
.venv\Scripts\activate
pip install -r requirements-api.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Dashboard
cd C:\Programs\codex\SheGuard\SheGuard_Dashboard
npm install
npm run dev
# or
npm run build && npm run preview
```

---

## Environment Variables

### Backend (.env)
```
DATABASE_URL=sqlite:///./sheguard.db
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
SHEGUARD_CORS_ORIGINS=*
```

### Dashboard (.env)
```
VITE_API_BASE_URL=http://192.168.1.100:8000
# VITE_WS_BASE_URL=ws://192.168.1.100:8000
# VITE_MEDIA_BASE_URL=http://192.168.1.100:8000
```

---

## WebSocket Message Examples

### Emergency Started
```json
{
  "event": "emergency.started",
  "payload": {
    "session_id": "sos-a1b2c3d4",
    "user_id": 101,
    "user_name": "Jane Doe",
    "phone_number": "+919876543210",
    "trigger_source": "SOS",
    "started_at": "2026-08-22T10:30:00.000Z",
    "latitude": 28.6139,
    "longitude": 77.2090
  }
}
```

### Tracking Update
```json
{
  "event": "tracking_update",
  "payload": {
    "session": {
      "session_id": "sos-a1b2c3d4",
      "status": "ACTIVE",
      "last_latitude": 28.6140,
      "last_longitude": 77.2091
    },
    "location": {
      "latitude": 28.6140,
      "longitude": 77.2091,
      "speed": 1.5,
      "battery": 85,
      "accuracy": 10,
      "timestamp": "2026-08-22T10:30:05.000Z"
    }
  }
}
```

### Threat Escalation
```json
{
  "event": "threat_escalation",
  "payload": {
    "session_id": "sos-a1b2c3d4",
    "threat_level": "HIGH",
    "threat_score": 87,
    "ai_summary": "Possible following detected on CCTV-04",
    "confidence": 91
  }
}
```
