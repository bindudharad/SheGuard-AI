# Context Agent - Existing System Audit Report

**Date**: 2026-08-18  
**Component**: SheGuard (Full Project)  
**Purpose**: Document existing context-relevant capabilities for Context Agent implementation

---

## 1. Existing Location System

### 1.1 Backend Location Models
**Location**: `SheGuard_Backend/app/models/entities.py`

- **LiveLocation**: User GPS tracking with latitude, longitude, speed, battery, accuracy, timestamp, session_id
- **TrackingSession**: Session-based tracking with last known coordinates, status, timestamps
- **CCTVCamera**: Camera location with latitude, longitude, camera_name, ip_address, rtsp_url, online_status
- **Incident**: Incident location with latitude, longitude, camera_id

### 1.2 Location Routes
**Location**: `SheGuard_Backend/app/routes/locations.py`

- `POST /location/update` - Update user location
- `GET /location/live/{user_id}` - Get latest user location
- `POST /tracking/start` - Start tracking session
- `POST /tracking/update` - Update tracking session location
- `GET /tracking/live/{session_id}` - Get live tracking state
- `GET /tracking/history/{session_id}` - Get tracking history
- WebSocket `/ws/tracking/{session_id}` - Real-time tracking updates

### 1.3 Smart Coordinate Resolution
**Location**: `SheGuard_Backend/app/services/incident_linking.py::SmartIncidentResponseService.resolve_coordinates()`

Resolves coordinates with priority:
1. Explicit latitude/longitude from request
2. User's latest LiveLocation
3. Camera location from CCTVCamera table

---

## 2. Existing GPS Implementation

### 2.1 Mobile App GPS
**Location**: `SheGuard_App/lib/services/location_service.dart`

- Background location tracking using `geolocator` and `flutter_background_service`
- GPS accuracy handling, battery optimization
- Sends location to backend via REST API
- SOS tracking with emergency session integration

### 2.2 Backend GPS Services
- **LiveLocation** table stores raw GPS coordinates
- **TrackingSession** manages continuous tracking sessions
- Haversine distance calculation in `app/services/geo.py`

---

## 3. Existing Camera Identifiers

### 3.1 Camera Model
**Location**: `SheGuard_Backend/app/models/entities.py::CCTVCamera`

```python
camera_id: int (PK, autoincrement)
camera_name: str
ip_address: str (optional)
rtsp_url: str (optional)
latitude: float (optional)
longitude: float (optional)
online_status: str (default: "unknown")
```

### 3.2 Camera Routes
**Location**: `SheGuard_Backend/app/routes/cameras.py`

- `POST /camera/register` - Register new camera
- `GET /camera/list` - List all cameras
- `GET /camera/health` - Camera health (registered + runtime)

### 3.3 Camera Manager
**Location**: `SheGuard_Backend/app/services/camera_manager.py`

Runtime camera management with connection status tracking.

---

## 4. Existing Incident Database

### 4.1 Incident Model
**Location**: `SheGuard_Backend/app/models/entities.py::Incident`

Key fields:
- `incident_id`, `user_id`, `incident_type`, `confidence`
- `threat_score`, `threat_level`, `kidnap_suspicion_score`
- `ai_summary`, `ai_provider`, `explanation`
- `camera_id`, `latitude`, `longitude`
- `image_path`, `video_path`, `status`
- `linked_user_id`, `matching_distance_meters`, `emergency_session_id`
- `created_at`

### 4.2 Incident Routes
**Location**: `SheGuard_Backend/app/routes/incidents.py`

- `POST /incident/create` - Create incident
- `POST /incidents/create` - Create with media upload
- `GET /incidents` - List incidents
- `GET /incidents/latest` - Latest incidents
- `GET /incidents/{incident_id}` - Get incident details
- `GET /incident/search?q=` - Semantic search via IncidentMemory
- `GET /incident/history/{user_id}` - User incident history

### 4.3 Incident Memory (Semantic Search)
**Location**: `SheGuard_Backend/app/services/incident_memory.py`

- File-based: `app/database/incident_memory.jsonl`
- Embeddings via `EmbeddingClient` (NVIDIA/HuggingFace -> deterministic fallback)

---

## 5. Existing Incident Schema

Same as Incident Model in Section 4.1.

---

## 6. Existing Timestamp Handling

### 6.1 Backend
- All timestamps use `datetime.utcnow()` (naive UTC)
- Stored as `DateTime` in SQLite
- **ISSUE**: No timezone awareness - uses naive UTC everywhere

### 6.2 Mobile App
- Sends ISO 8601 timestamps
- Background service tracks session timestamps

### 6.3 Vision Agent
- Uses `datetime.utcnow().isoformat()` in VisionOutput schema
- Frame timestamps from video source

---

## 7. Existing User Status

### 7.1 User Model
**Location**: `SheGuard_Backend/app/models/entities.py::User`

- `user_id`, `full_name`, `phone_number`, `password_hash`, `profile_photo`, `created_at`

### 7.2 User Status Indicators
- **Online/Offline**: Not explicitly tracked in DB
- **SOS Status**: Via `EmergencySession.status` (active/inactive)
- **Tracking Session**: Via `TrackingSession.status` (active/ended)
- **Live Location**: Latest `LiveLocation.timestamp` indicates recency
- **Device Status**: Battery level in `LiveLocation.battery` and `TrackingSession.last_battery`

---

## 8. Existing Emergency Status

### 8.1 EmergencySession Model
**Location**: `SheGuard_Backend/app/models/entities.py::EmergencySession`

- `session_id`, `incident_id`, `user_id`, `status`
- `trigger_source` (ai_cctv, manual, etc.)
- `started_at`, `ended_at`
- `last_latitude`, `last_longitude`, `last_update_at`
- `live_tracking_url`, `timeline_json`

### 8.2 Emergency Routes
**Location**: `SheGuard_Backend/app/routes/emergency.py`

- `POST /emergency/start` - Start emergency session
- `GET /emergency/active` - Active emergencies
- `POST /emergency/{session_id}/end` - End emergency

---

## 9. Existing Zone/Area Data

### 9.1 Zone System
**NOT FOUND** - No explicit zone/area model exists in the database.

### 9.2 Camera-based Areas
- Cameras have lat/lon but no zone assignment
- Incidents have lat/lon but no zone classification

---

## 10. Existing Map Functionality

### 10.1 Dashboard
**Location**: `SheGuard_Dashboard/src/pages/MapPage.tsx` (React + Leaflet)

- Live incident markers
- Camera markers
- User location tracking
- Emergency session tracking with routing

### 10.2 Mobile App
**Location**: `SheGuard_App/lib/screens/tracking_screen.dart`

- Leaflet map with SOS navigation
- OSRM routing for parent-to-victim path

---

## 11. Existing Historical Incident Queries

### 11.1 IncidentMemory Search
- Semantic similarity via embeddings
- Returns top-N similar incidents with metadata

### 11.2 Direct Database Queries
- By user: `Incident.user_id`
- By camera: `Incident.camera_id`
- By time: `Incident.created_at`
- By type: `Incident.incident_type`
- By status: `Incident.status`

---

## 12. Existing Nearby-Incident Queries

**NOT FOUND** - No geospatial nearby query implemented. The database has lat/lon but no spatial index or radius query.

---

## 13. Existing Backend APIs

### 13.1 FastAPI Application
**Location**: `SheGuard_Backend/app/main.py`

- CORS configured for Dashboard + Mobile
- JWT authentication
- WebSocket for real-time updates
- Service token for AI-to-Backend communication

### 13.2 Key Endpoints for Context
| Endpoint | Purpose |
|----------|---------|
| `/camera/list` | Camera metadata with locations |
| `/camera/health` | Camera online status |
| `/incidents` | All incidents with locations |
| `/incidents/latest` | Recent incidents |
| `/incident/search` | Semantic incident search |
| `/location/live/{user_id}` | User GPS |
| `/tracking/live/{session_id}` | Tracking session state |
| `/incident/history/{user_id}` | User's incidents |

---

## 14. Existing Database

### 14.1 SQLite
- **File**: `sheguard.db` (project root)
- **ORM**: SQLAlchemy 2.0
- **Migration**: Auto on startup via `init_database()`

### 14.2 Tables
All 11 tables defined in EXISTING_DATABASE_INVENTORY.md

---

## 15. Existing Reusable Utilities

### 15.1 Geo Utilities
**Location**: `SheGuard_Backend/app/services/geo.py`

```python
haversine_distance_meters(a: GeoPoint, b: GeoPoint) -> float
has_coordinates(latitude, longitude) -> bool
```

### 15.2 Incident Linking
**Location**: `SheGuard_Backend/app/services/incident_linking.py::SmartIncidentResponseService`

- `resolve_coordinates()` - Priority-based coordinate resolution
- `recent_duplicate()` - Deduplication by camera/location/time
- `auto_link_and_start_response()` - Link incidents to users

### 15.3 Incident Memory
**Location**: `SheGuard_Backend/app/services/incident_memory.py::IncidentMemory`

- Semantic search for historical context

### 15.4 Agent Framework
**Location**: `SheGuard_agents/core/`

- `BaseAgent` - Health monitoring, async processing
- `EventBus` - Pub/sub with trace_id support
- `AgentRegistry` - Agent discovery

---

## 16. Existing Bugs

### 16.1 Critical Bugs

| Bug | Location | Impact |
|-----|----------|--------|
| Naive timestamps | All datetime.utcnow() | No timezone support |
| No zone system | Database schema | Cannot do zone-based context |
| No nearby incident query | Database/API | Cannot find recent nearby incidents |
| No spatial index | SQLite schema | Slow geospatial queries |
| Camera location optional | CCTVCamera model | Many cameras may lack coordinates |

### 16.2 Integration Bugs

| Bug | Location | Impact |
|-----|----------|--------|
| Vision Agent doesn't publish to EventBus | agents/vision/agent.py | Context Agent won't receive vision events |
| No incident_id in VisionOutput | agents/vision/schemas.py | Cannot correlate context with vision |
| EventBus not used by backend | app/main.py | Agents can't communicate with backend |

---

## 17. Missing Context Information

| Missing | Required For |
|---------|--------------|
| Zone/area definitions | Location context, isolation analysis |
| Nearby incident radius queries | Proximity context |
| Historical incident time-decay | History weighting |
| Camera zone mapping | Camera context |
| Security resource locations | Security proximity |
| Weather/environmental data | Environmental context |
| Timezone-aware timestamps | Correct time analysis |
| Data quality scoring | Confidence calculation |
| Context risk formula | Context scoring |

---

## 18. Recommended Integration Strategy

### 18.1 Database Access
- **Option A**: Direct SQLAlchemy connection to existing `sheguard.db`
- **Option B**: HTTP API calls to SheGuard_Backend
- **Recommendation**: Option A for performance (read-only), Option B for writes

### 18.2 Provider Pattern
Create adapters for each data source:
- `LocationProvider` -> reads from LiveLocation, TrackingSession, CCTVCamera
- `IncidentProvider` -> reads from Incident table + IncidentMemory
- `CameraProvider` -> reads from CCTVCamera table
- `TimeProvider` -> timezone-aware time utilities
- `UserProvider` -> reads User, EmergencySession, TrackingSession
- `EnvironmentProvider` -> placeholder for future weather integration

### 18.3 Event Flow
```
Vision Agent -> PROCESS_FRAME/FRAME_PROCESSED -> EventBus
                                    |
Context Agent <- subscribes to vision events
                                    |
Context Agent -> CONTEXT_UPDATED -> EventBus
                                    |
Threat Agent <- subscribes to context events
```

### 18.4 Configuration
Extend `.env` with:
```
APP_TIMEZONE=Asia/Kolkata
CONTEXT_NEARBY_RADIUS_METERS=500
CONTEXT_LOOKBACK_HOURS=24
CONTEXT_HISTORY_TTL_SECONDS=60
CONTEXT_WEIGHT_TIME=0.15
CONTEXT_WEIGHT_LOCATION=0.20
CONTEXT_WEIGHT_HISTORICAL=0.25
CONTEXT_WEIGHT_PROXIMITY=0.20
CONTEXT_WEIGHT_ISOLATION=0.15
CONTEXT_WEIGHT_ENVIRONMENT=0.05
```
