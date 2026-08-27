# SheGuard Existing API Inventory

**Date**: 2026-08-18
**Component**: SheGuard_Backend (FastAPI v2.0.0)
**Source**: enumerated directly from `app/routes/*.py` and `app/api/schemas.py`.
**Purpose**: Document every existing endpoint so the new `SheGuard_agents` API is additive/compatible, not a blind duplicate.

> Note: The new `SheGuard_agents` API is a SEPARATE service (per master prompt). These endpoints are reference for shape/compatibility only — the dashboard/app can later consume the new API.

---

## 1. Users & Auth (`routes/users.py`, `routes/contacts.py`)
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/register` | — | create user |
| POST | `/login` | — | returns JWT `access_token` |
| GET | `/profile/{user_id}` | user | profile |
| POST | `/contacts/add` | user | add emergency contact |
| GET | `/contacts/{user_id}` | user | list contacts |

- JWT: HS256, manual impl in `services/security.py` (`SHEGUARD_JWT_SECRET`); `services/auth.py` provides `get_current_user` (bearer) and `get_service_or_user` (bearer OR shared `SHEGUARD_SERVICE_TOKEN`). Passwords: PBKDF2-SHA256 + salt.

## 2. Incidents (`routes/incidents.py`)
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/incident/create` | service/user | create incident (JSON) |
| POST | `/incidents/create` | service/user | create incident (multipart + media) |
| GET | `/incidents` | user | list (limit) |
| GET | `/incidents/latest` | user | latest |
| GET | `/incidents/{incident_id}` | user | detail + evidence + notifications |
| POST | `/incidents/link-user` | user | link incident to user |
| GET | `/incident/history/{user_id}` | user | user history |
| GET | `/incident/live` | user | live incidents |
| GET | `/incident/search` | user | semantic search (IncidentMemory) |
| GET | `/evidence/{incident_id}` | user | evidence list |
| GET | `/evidence/file` | user | secure file (path-traversal guarded) |
| GET | `/secure/evidence/{incident_id}` | user | secure evidence list |
| POST | `/evidence/upload` | user | encrypted evidence upload (base64) |

- Incident output fields: `id, incident_id, incident_type, confidence, threat_score, threat_level, kidnap_suspicion_score, ai_summary, ai_provider, explanation, camera_id, latitude, longitude, image_path, video_path, image_url, video_url, preview_image, status, linked_user_id, matching_distance_meters, emergency_session_id, created_at`.

## 3. Locations & Tracking (`routes/locations.py`)
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/location/update` | update live location |
| GET | `/location/live/{user_id}` | latest location |
| POST | `/tracking/start` | start tracking session |
| POST | `/tracking/update` | update tracking |
| GET | `/tracking/live/{session_id}` | live tracking |
| GET | `/tracking/history/{session_id}` | history |
| GET | `/location/stream/{session_id}` | SSE/stream |
| WS | `/ws/tracking/{session_id}` | tracking socket |
| GET | `/track/{session_id}` | HTML tracking page |
| GET | `/track/{session_id}/qr` | QR |
| GET | `/live/{session_id}` | HTML live page |

## 4. Emergency, Notifications, Cameras
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/emergency/start` | start `EmergencySession`, notify contacts |
| POST | `/notifications/send` | send notification |
| POST | `/camera/register` | register CCTV camera |
| GET | `/camera/list` | list cameras |
| GET | `/camera/health` | camera health |

## 5. Realtime & System (`routes/realtime.py`, `routes/system.py`)
| Method | Path | Purpose |
|--------|------|---------|
| WS | `/ws/live` | global realtime hub |
| WS | `/ws/emergency/{session_id}` | emergency-session socket |
| GET | `/system/local-network` | local IP/port/base URL discovery |

- Broadcast events: `incident.created`, `incident.merged`, `incident.batched`, `emergency.session.*`.

## 6. Root & Health
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | health (`{status, service, version}`) |
| GET | `/health/gpu` | GPU status |

## 7. Compatibility notes for SheGuard_agents API
- Keep `/incidents`, `/incidents/{id}`, `/incidents/latest`, `/evidence/{id}`, `/health` shapes near-compatible so the existing dashboard (`normalizeIncident()`) and app (`incident.created` envelope) can later consume the new API with minimal change.
- New API adds: `/agents`, `/agents/{name}`, `/analysis/frame`, `/analysis/video`, `/simulation/incident`, `/events` (SSE), `/ws/events`, `/x402/status`, `/x402/request`, `/payments`, `/payments/{id}`.
- New API uses a **0–100** risk scale (legacy uses 0–10) — document the remap.
- New API introduces agent `decision_trace`, `x402_payments`, `safety_intelligence` surfaces absent from legacy.
