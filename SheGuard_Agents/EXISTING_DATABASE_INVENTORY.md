# SheGuard Existing Database Inventory

**Date**: 2026-08-18
**Component**: SheGuard_Backend (SQLAlchemy 2.0 + SQLite) + SheGuard_AI (legacy sqlite3)
**Source**: `app/models/entities.py`, `app/database/session.py` (migrations), file sizes.
**Purpose**: Document schema for reuse/adaptation. The new `SheGuard_agents` will use its **own SQLite DB** (clean schema) but can reference legacy data.

---

## 1. Configuration
- **Engine**: SQLite (file-based)
- **Backend DB**: `SheGuard_Backend/sheguard.db` (1,310,720 bytes)
- **AI DB**: `SheGuard_AI/sheguard.db` (32,768 bytes — older/smaller)
- **URL**: `sqlite:///sheguard.db` (config via `SHEGUARD_DB_PATH` or `SHEGUARD_DATABASE_URL`)
- **ORM**: SQLAlchemy 2.0 `DeclarativeBase` + `Mapped` columns
- **Migration**: `init_database()` runs on startup; legacy table rename + column/index additions

---

## 2. Tables (Backend)

### 2.1 users
```sql
user_id PK, full_name, phone_number UNIQUE, password_hash, profile_photo, created_at
```
Index: phone_number

### 2.2 emergency_contacts
```sql
contact_id PK, user_id FK, relation, contact_name, phone_number
```
Index: user_id

### 2.3 live_locations
```sql
location_id PK, user_id FK, session_id, latitude, longitude, speed, battery, accuracy, timestamp
```
Indexes: user_id, session_id, timestamp. **Migrations add**: session_id, battery, accuracy.

### 2.4 tracking_sessions
```sql
session_id PK, user_id FK, status DEFAULT "active", started_at, ended_at,
last_latitude, last_longitude, last_speed, last_battery, last_accuracy, last_update_at
```
Indexes: user_id, status, started_at, last_update_at

### 2.5 incidents (core)
```sql
incident_id PK, user_id FK, incident_type, confidence, threat_score DEFAULT 0,
threat_level, kidnap_suspicion_score DEFAULT 0,
ai_summary, ai_provider, explanation,
camera_id, latitude, longitude, image_path, video_path,
status DEFAULT "new", linked_user_id FK, matching_distance_meters,
emergency_session_id, created_at
```
Indexes: user_id, incident_type, created_at, threat_level, camera_id, status, linked_user_id, emergency_session_id.
**Migrations add**: threat_level, kidnap_suspicion_score, ai_provider, explanation, camera_id, image_path, video_path, status, linked_user_id, matching_distance_meters, emergency_session_id.

### 2.6 evidence
```sql
evidence_id PK, incident_id FK, image_path, video_path, cctv_source,
metadata_path, pre_event_video_path, confidence, threat_score, created_at
```
Index: incident_id. **Migrations add**: metadata_path, pre_event_video_path, confidence, threat_score.

### 2.7 incident_victim_links
```sql
link_id PK, incident_id FK, user_id FK, emergency_session_id, distance_meters,
match_method DEFAULT "gps_radius", confidence, created_at
```
Indexes: incident_id, user_id

### 2.8 emergency_sessions
```sql
session_id PK, incident_id FK, user_id FK, status DEFAULT "active",
trigger_source DEFAULT "ai_cctv", started_at, ended_at,
last_latitude, last_longitude, last_update_at, live_tracking_url, timeline_json
```
Indexes: incident_id, user_id, status, started_at, last_update_at

### 2.9 emergency_notifications
```sql
notification_id PK, incident_id FK, emergency_session_id FK, user_id FK,
contact_id FK, channel, recipient, status DEFAULT "queued", retry_count DEFAULT 0,
message, error, created_at, sent_at
```
Indexes: incident_id, emergency_session_id, user_id, contact_id, channel, created_at

### 2.10 evidence_records
```sql
record_id PK, incident_id FK, emergency_session_id FK, evidence_type,
file_path, public_url, metadata_path, latitude, longitude, captured_at, created_at
```
Indexes: incident_id, emergency_session_id, evidence_type, created_at

### 2.11 cctv_cameras
```sql
camera_id PK, camera_name, ip_address, rtsp_url, latitude, longitude, online_status
```

---

## 3. Migration System (`app/database/session.py::_ensure_sqlite_columns()`)
Runs every startup:
1. Legacy table rename (`users` → `legacy_users`, `cctv_cameras` → `legacy_cctv_cameras`)
2. Adds missing columns to incidents/evidence/live_locations (list above)
3. Creates 14 indexes if missing (see §2)

---

## 4. Data Access
- `get_db()` — FastAPI dependency yielding `Session`
- `SessionLocal` — `sessionmaker(autoflush=False, autocommit=False)`
- Common queries: incidents by user/date, latest, with evidence join, active emergency sessions, latest location by user/session.

---

## 5. Relationships
- User → Incidents, EmergencyContacts, LiveLocations, TrackingSessions, EmergencySessions
- Incident → Evidence (cascade), IncidentVictimLinks (cascade), EvidenceRecords (cascade), EmergencySession (via emergency_session_id)
- EmergencySession → EmergencyNotifications (cascade)

---

## 6. Reuse Strategy for SheGuard_agents
**Recommendation**: Create **new SQLite** (`sheguard_agents.db`) with **clean agent-focused schema**. Do not write to the legacy DB. Read legacy data only if needed for migration/backfill.

### 6.1 New Tables (agent system)
```sql
-- Agents registry
CREATE TABLE agents (
    agent_id VARCHAR(80) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    version VARCHAR(20),
    status VARCHAR(30) DEFAULT "OFFLINE",
    config_json TEXT,
    last_heartbeat DATETIME,
    events_processed INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,
    avg_latency_ms FLOAT
);

-- Agent events / message bus
CREATE TABLE agent_events (
    event_id VARCHAR(80) PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    agent_name VARCHAR(100) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    incident_id VARCHAR(80),
    trace_id VARCHAR(80),
    confidence FLOAT,
    payload_json TEXT,
    status VARCHAR(20) DEFAULT "PROCESSED"
);
CREATE INDEX ix_agent_events_incident ON agent_events(incident_id);
CREATE INDEX ix_agent_events_trace ON agent_events(trace_id);
CREATE INDEX ix_agent_events_agent_time ON agent_events(agent_name, timestamp);

-- Incidents (agent format, string ID "SG-000001")
CREATE TABLE agent_incidents (
    incident_id VARCHAR(80) PRIMARY KEY,
    status VARCHAR(30) DEFAULT "ACTIVE",
    risk_score INTEGER,
    risk_level VARCHAR(20),
    threat_type VARCHAR(100),
    location_json TEXT,
    camera_id VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    agents_involved_json TEXT,
    evidence_json TEXT,
    notifications_json TEXT,
    payment_json TEXT,
    decision_trace_json TEXT
);

-- x402 payments
CREATE TABLE x402_payments (
    payment_id VARCHAR(80) PRIMARY KEY,
    incident_id VARCHAR(80) NOT NULL,
    service VARCHAR(100) NOT NULL,
    amount FLOAT NOT NULL,
    currency VARCHAR(10) DEFAULT "ALGO",
    network VARCHAR(30) DEFAULT "testnet",
    status VARCHAR(30) DEFAULT "REQUESTED",
    transaction_id VARCHAR(200),
    wallet_address VARCHAR(80),
    requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    confirmed_at DATETIME,
    metadata_json TEXT
);
CREATE INDEX ix_x402_incident ON x402_payments(incident_id);
CREATE INDEX ix_x402_status ON x402_payments(status);

-- Evidence (agent format)
CREATE TABLE agent_evidence (
    evidence_id VARCHAR(80) PRIMARY KEY,
    incident_id VARCHAR(80) NOT NULL,
    camera_id VARCHAR(100),
    timestamp DATETIME NOT NULL,
    video_path TEXT,
    image_path TEXT,
    sha256_hash VARCHAR(64),
    metadata_json TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_agent_evidence_incident ON agent_evidence(incident_id);
```

---

## 7. Decision (for `DATABASE_DECISION.md`)
- **SQLite is appropriate** for MVP (embedded, no infra, portable, ACID).
- Do **not** introduce PostgreSQL/Redis — no proven need yet.
- Keep legacy DB read-only; new DB is agent-owned.
- Use SQLAlchemy 2.0 + Alembic for future migrations if schema evolves.
