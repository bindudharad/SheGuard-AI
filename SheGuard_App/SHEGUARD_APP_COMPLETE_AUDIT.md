# SheGuard Mobile App — COMPLETE FORENSIC AUDIT

**Audit target:** `C:\Programs\codex\SheGuard\SheGuard_App` (Flutter mobile client)
**Cross-checked against:** `C:\Programs\codex\SheGuard\SheGuard_Backend` (FastAPI backend)
**Audit date:** 2026-08-20
**Method:** Static source inspection only. No code modified, no deps changed, no destructive commands.
**Status legend:** IMPLEMENTED / VERIFIED, IMPLEMENTED / BROKEN, DOCUMENTED ONLY, NOT VERIFIED, UI ONLY / MOCK, BROKEN REFERENCE.

---

## 1. Executive Summary

SheGuard App is a Flutter (Dart) mobile client for the SheGuard_AI safety backend. It is a from-scratch Flutter project (NOT a migration) implementing a complete emergency-safety UX: splash, login, registration, home command center, emergency contacts, an AI/CCTV incident feed, live status, an auto-SOS emergency mode screen, settings, and a fake-call screen.

Architected around the `provider` package and a thin `ApiService` HTTP client (`package:http`). Talks to the FastAPI backend over HTTP and WebSockets. Critical safety paths (SOS) use real backend calls: SMS, a direct/auto phone call, incident creation (`/incidents/create`), live GPS tracking (`/tracking/start`, `/tracking/update`, `/location/update`), and a WebSocket live feed (`/ws/live`).

**Key verified facts:**
- Hardcoded backend base URL is `http://192.168.1.3:8000` in `lib/config/api_config.dart`. LAN IP — app requires same local network as backend host.
- Auth is real: `POST /register` and `POST /login` exchange a JWT-style `access_token`; stored in `FlutterSecureStorage`, sent as `Bearer`.
- SOS flow creates a backend incident + tracking session, persists a local session record; does NOT depend on AI/CCTV events.
- Auto-SOS (AI/CCTV triggered) listens to WS `incident.created`/`incident.merged` and calls `POST /emergency/start`.
- Evidence capture implemented (audio + front-camera still, AES-256-GCM) with an upload path (`POST /evidence/upload`) the backend implements.

**Most important limitation:** Backend URL hardcoded to a single LAN IP. NO runtime settings screen, NO SharedPreferences URL override, and the only build-time override (`SHEGUARD_PUBLIC_TRACKING_BASE_URL`) only affects the public tracking base URL, NOT the API base URL. If host IP changes, app must be rebuilt. NO cloud/public backend.

No secrets/API keys/tokens found in source. Connection values reported as `<REDACTED>` where relevant.

---

## 2. Project Structure

```
SheGuard_App/
├── lib/
│   ├── main.dart                      # Entry point, service/provider wiring, MaterialApp + routes
│   ├── config/api_config.dart        # ApiConfig.baseUrl = http://192.168.1.3:8000 (HARDCODED)
│   ├── core/                         # app_config, app_routes, app_theme, safety_types, re-exports
│   ├── models/                       # user, incident, emergency_contact, emergency_event, evidence, camera_source, location_update, location_freshness
│   ├── providers/                    # auth, contact, incident, location, safety, settings
│   ├── services/                     # api, auth, sos, auto_sos_manager, emergency_realtime, incident, location, foreground_tracking, contact, camera, notification, emergency_call, emergency_sms, emergency_siren, evidence_capture, backend_health, connectivity, motion_protection, local_contact_metadata
│   ├── screens/                      # splash, login, register, home, contacts, incident_history(+detail), emergency_mode, live_status, settings, fake_call
│   └── widgets/                      # sos_button, emergency_action_panel, safety_status_banner, empty_state, metric_tile, status_tile, timeline_card, premium_ui
├── android/                          # Native Android config (see §25)
├── ios/                              # Present, minimal default Flutter
├── assets/                           # referenced by pubspec
├── test/                             # model_payload_test.dart, widget_test.dart
├── pubspec.yaml / pubspec.lock
├── README.md, PROJECT_STATUS.md, PROJECT_SUMMARY.md, ARCHITECTURE.md, ARCHITECTURE_REPORT.md, AUTO_SOS_INTEGRATION.md, BUG_REPORT.md, IMPROVEMENT_PLAN.md, PARENT_AUTO_CALL_TESTING.md, REALTIME_RECONNECT_NOTIFICATIONS.md, SIMPLE_INCIDENT_FEED_TESTING.md
└── "SheGuard_App report/"            # Duplicate markdown docs
```

**Dependency count:** 24 runtime packages. State management: `provider` only. HTTP: `http` (NOT Dio). No `dio` in pubspec.

## 3. Application Startup

File: `lib/main.dart`. `Future<void> main()`:
1. `WidgetsFlutterBinding.ensureInitialized()`.
2. `NotificationService().initialize()` — Android init, icon `@drawable/sheguard_icon`.
3. Construct `ApiService`, `StorageService`, `ContactService(api)`, `ForegroundTrackingService().initialize()`.
4. Construct `LocationService`, `IncidentService`, `EvidenceCaptureService`, `EmergencyCallService`, `EmergencySirenService`, `EmergencyRealtimeService`, `SosService`, `AutoSosManager`.
5. `runApp(SheGuardApp(...))`.

`SheGuardApp.build()`: `MultiProvider` with AuthProvider, ContactProvider, LocationProvider, IncidentProvider, AutoSosManager, SafetyProvider, SettingsProvider. `AuthProvider..restore()` runs immediately (reads secure token + user, then `GET /profile/{id}`). `SafetyProvider..initialize()` runs (connectivity + `GET /health` or `/`). `SettingsProvider..load()` runs. `MaterialApp` with `home: SplashScreen()` and a `routes` table (named routes, NOT goRouter). `debugShowCheckedModeBanner: false`.

No env file loading, no `.env`, no dotenv, no Firebase init, no background registration beyond foreground service config.
## 4. Navigation

Mechanism: `MaterialApp` + `routes` map (named routes) + `Navigator.push/pushReplacement/pushNamed/pushNamedAndRemoveUntil` + `push(MaterialPageRoute(...))` for detail screens. NO `goRouter`, NO deep links, NO auth-guard route middleware (auth handled by SplashScreen redirect).

Routes: `/login`→Login, `/register`→Register, `/home`→Home, `/contacts`→Contacts, `/live-status`→LiveStatus, `/incident-history`→IncidentHistory, `/emergency-mode`→EmergencyMode, `/settings`→Settings.

Navigation map (verified):

| From | Action | To |
|------|--------|-----|
| Splash | `pushReplacementNamed` (auth.isAuthenticated) | Home / Login |
| Login | submit success → `pushReplacementNamed` | Home |
| Login | "Create account" → `pushNamed` | Register |
| Register | submit success → `pushNamedAndRemoveUntil` | Home |
| Home | appbar settings → `pushNamed` | Settings |
| Home | appbar logout → `pushNamedAndRemoveUntil` | Login |
| Home | shortcut "Contacts" → `pushNamed` | Contacts |
| Home | shortcut "Alerts" → `pushNamed` | IncidentHistory |
| Home | dev mode shortcut → `pushNamed` | LiveStatus |
| Home | autoSos.active → `pushNamed` | EmergencyMode |
| IncidentHistory | tap card / "Open details" → `push(MaterialPageRoute)` | IncidentDetailScreen (in-file) |
| Settings | "Fake call" → `push(MaterialPageRoute)` | FakeCallScreen (in-file) |
| Settings | logout → `pushNamedAndRemoveUntil` | Login |

`IncidentDetailScreen` and `FakeCallScreen` are in-file, not in route table — reached via `push(MaterialPageRoute(...))`. All 10 named + 2 in-file screens reachable.

## 5. Screens

### 5.1 SplashScreen (`screens/splash_screen.dart`)
On boot: `SafetyProvider.refreshBackendStatus()` + `LocationProvider.requestPermission()` with 5s timeout guard. 2s splash delay. Route to Home (if `auth.isAuthenticated`) or Login. **IMPLEMENTED / VERIFIED**.

### 5.2 LoginScreen (`screens/login_screen.dart`)
Fields: phone, password. Validation: phone ≥7, password ≥6. Calls `AuthProvider.login`. On success → Home. **IMPLEMENTED / VERIFIED**.

### 5.3 RegisterScreen (`screens/register_screen.dart`)
Fields: full name, phone, password, optional profile image URL. Calls `AuthProvider.register`. On success → Home. No contacts at registration. **IMPLEMENTED / VERIFIED**.

### 5.4 HomeScreen (`screens/home_screen.dart`) — 27 KB, main screen
Hero header, `SafetyStatusBanner`, `EmergencyActionPanel` (SOS button), GPS status card, location label, emergency-active card, loading shimmer, "I'm safe" cancel, shortcut grid (Contacts / Safety / Alerts), dev live-status shortcut, reconnect banner. Triggers: SOS hold (3s countdown), silent SOS (long-press/triple-tap header when silent mode on), shake SOS, fall detection. On init (if user + trackingEnabled): binds AutoSosManager, sets monitoring, loads contacts, loads incident feed, starts incident realtime, requests GPS, starts tracking. **IMPLEMENTED / VERIFIED**.

### 5.5 ContactsScreen (`screens/contacts_screen.dart`)
List contacts; add (name/relation/phone); swipe-to-delete (local hide); popup edit (local metadata only); favorite toggle (local). Backend: `GET /contacts/{id}`, `POST /contacts/add`. Edit/remove are LOCAL only. **IMPLEMENTED / VERIFIED** (add+list backend; edit/remove local-only).

### 5.6 IncidentHistoryScreen (`screens/incident_history_screen.dart`)
"Realtime Detection Feed". Lists `provider.liveIncidents`. Pull-to-refresh. Cards show thumbnail, confidence %, time, location, folder id, video button, details button. Tap opens in-file `IncidentDetailScreen` (thumbnail, video, metadata.json). On new emergency incident: "Emergency Detected" popup + vibrate + auto-dial first parent. **IMPLEMENTED / VERIFIED**.

### 5.7 EmergencyModeScreen (`screens/emergency_mode_screen.dart`)
Auto-SOS mode UI: realtime link state, GPS tracking state, parent call state, session id, escalation countdown, contact sent/failed/attempted, live GPS card, cancel button. Driven by `AutoSosManager`. **IMPLEMENTED / VERIFIED**.

### 5.8 LiveStatusScreen (`screens/live_status_screen.dart`)
Dev screen (long-press app bar title on Home when `developerModeEnabled`). Backend status, GPS live, battery, freshness, loads live incidents. **IMPLEMENTED / VERIFIED**.

### 5.9 SettingsScreen (`screens/settings_screen.dart`)
Toggles: silent mode, local notifications, emergency siren, live GPS tracking, auto emergency calling, shake SOS, shake sensitivity slider, AI fall detection, privacy guard. Actions: GPS permission, fake call, battery optimization, About (SheGuard 1.0.0), safety network refresh, logout. **IMPLEMENTED / VERIFIED**.

### 5.10 FakeCallScreen (`screens/fake_call_screen.dart`)
In-file from Settings. Pure UI decoy call. No backend. **IMPLEMENTED / VERIFIED** (UI ONLY).

### 5.11 IncidentDetailScreen (in `incident_history_screen.dart`)
See 5.6. Shows media + metadata.json via `ApiService.publicJson`. **IMPLEMENTED / VERIFIED**.
## 6. Features

| # | Feature | File | Service | Endpoint | Status |
|---|---------|------|---------|----------|--------|
| 1 | Registration | auth_service.dart | POST /register | **VERIFIED** |
| 2 | Login | auth_service.dart | POST /login | **VERIFIED** |
| 3 | Token storage (secure) | storage_service.dart | FlutterSecureStorage | **VERIFIED** |
| 4 | Profile fetch | auth_service.dart | GET /profile/{id} | **VERIFIED** |
| 5 | Logout | auth_service.dart | clears secure storage | **VERIFIED** |
| 6 | Contacts list | contact_service.dart | GET /contacts/{id} | **VERIFIED** |
| 7 | Contact add | contact_service.dart | POST /contacts/add | **VERIFIED** |
| 8 | Contact edit/remove/favorite | local_contact_metadata_service.dart | LOCAL only | **VERIFIED** (local-only) |
| 9 | Manual SOS | sos_service.dart + home_screen.dart | /incidents/create, /tracking/start, /tracking/update, /location/update | **VERIFIED** |
| 10 | Silent SOS | home_screen.dart + sos_service.dart | same as SOS | **VERIFIED** |
| 11 | SOS throttling (30s dup) | sos_service.dart | n/a | **VERIFIED** |
| 12 | Emergency SMS | emergency_sms_service.dart | device SMS (telephony) | **VERIFIED** |
| 13 | Auto phone call | emergency_call_service.dart | flutter_phone_direct_caller / tel: | **VERIFIED** |
| 14 | Emergency siren | emergency_siren_service.dart | SystemSound | **VERIFIED** |
| 15 | Emergency session (local) | sos_service.dart._storeSession | SharedPreferences | **VERIFIED** |
| 16 | Live GPS tracking (foreground service) | foreground_tracking_service.dart | /tracking/update | **VERIFIED** |
| 17 | Location update (non-session) | location_service.dart | /location/update | **VERIFIED** |
| 18 | Tracking start | location_service.dart | POST /tracking/start | **VERIFIED** |
| 19 | Offline tracking queue | location_service.dart + foreground_tracking_service.dart | SharedPreferences queue + /tracking/update | **VERIFIED** |
| 20 | Incident feed (live) | incident_service.dart / incident_provider.dart | GET /incidents, GET /incident/live, GET /incidents/latest | **VERIFIED** |
| 21 | Incident detail | incident_service.dart | GET /incidents/{id} | **VERIFIED** |
| 22 | Incident history | incident_service.dart | GET /incident/history/{id} | **VERIFIED** |
| 23 | Incident media | incident_service.dart + api_service.publicMediaUrl | GET /uploads/... (StaticFiles) | **VERIFIED** |
| 24 | WS live incident feed | emergency_realtime_service.dart / incident_service.watchIncidentEvents | WS /ws/live | **VERIFIED** |
| 25 | Auto-SOS from AI/CCTV | auto_sos_manager.dart | WS /ws/live → POST /emergency/start | **VERIFIED** |
| 26 | Auto-SOS status polling/cancel | auto_sos_manager.dart | GET /emergency/status | **IMPLEMENTED / BROKEN** (backend missing) |
| 27 | Encrypted evidence capture | evidence_capture_service.dart | local AES-256-GCM | **VERIFIED** |
| 28 | Evidence upload | evidence_capture_service.dart | POST /evidence/upload | **VERIFIED** (backend has it) |
| 29 | Shake SOS | motion_protection_service.dart | sensors_plus | **VERIFIED** |
| 30 | Fall detection | motion_protection_service.dart | sensors_plus | **VERIFIED** |
| 31 | Local notifications | notification_service.dart | flutter_local_notifications | **VERIFIED** |
| 32 | Realtime reconnect notifications | notification_service.dart + emergency_realtime_service.dart | local | **VERIFIED** |
| 33 | Backend health check | backend_health_service.dart | GET /health, GET / | **VERIFIED** |
| 34 | Connectivity awareness | connectivity_service.dart | connectivity_plus | **VERIFIED** |
| 35 | CCTV camera register/list | camera_service.dart | POST /camera/register, GET /camera/list | **BROKEN REFERENCE** (service exists, UNUSED) |
| 36 | CCTV live feed/discovery/nearby | — | — | **NOT IMPLEMENTED** |
| 37 | AI direct integration | — | — | **NOT IMPLEMENTED** (backend-only) |
| 38 | Push notifications (FCM) | — | — | **NOT IMPLEMENTED** |
| 39 | Telegram integration | — | — | **BACKEND ONLY** |
| 40 | Public tracking web page | backend GET /track/{id} | via ApiService.publicTrackingUrl → GET /system/local-network | **VERIFIED** |
| 41 | "I'm safe" cancel | home_screen.dart / auto_sos_manager.cancelAutoSos | local stop + POST /emergency/status (missing) | **PARTIAL** (local works, backend call missing) |

## 7. API Services

| Service | Responsibility | HTTP client |
|---------|----------------|-------------|
| ApiService | All REST + WS URI; base URL resolution; health; media URLs | `package:http` (NOT Dio) |
| AuthService | register/login/profile/restore/logout | wraps ApiService |
| ContactService | contacts list/add | wraps ApiService |
| CameraService | camera register/list | wraps ApiService (UNUSED) |
| IncidentService | incident feed/detail/history/evidence + WS watch | wraps ApiService + web_socket_channel |
| LocationService | GPS current/update, tracking start/update, offline queue | wraps ApiService + geolocator |
| ForegroundTrackingService | Android foreground service GPS loop | flutter_background_service + raw http |
| SosService | SOS orchestration | composes call/sms/siren/evidence/location/incident |
| AutoSosManager | WS-driven auto SOS | composes realtime + sos + api |
| EmergencyRealtimeService | WS client (backoff, heartbeat) | web_socket_channel (IOWebSocketChannel) |
| NotificationService | local notifications | flutter_local_notifications |
| EmergencyCallService | direct call / dialer | flutter_phone_direct_caller + url_launcher |
| EmergencySmsService | SMS | telephony |
| EmergencySirenService | siren sound | SystemSound |
| EvidenceCaptureService | audio + front camera, AES-256-GCM | camera + record + cryptography + secure_storage |
| BackendHealthService | health wrapper | wraps ApiService |
| ConnectivityService | online stream | connectivity_plus |
| MotionProtectionService | shake/fall | sensors_plus |
| LocalContactMetadataService | favorites/hide local | SharedPreferences |

Note: `Dio` NOT used. No `MultipartRequest` — evidence sent as base64 JSON.
## 8. API Endpoint Table

| Flutter File | Function | Method | Endpoint | Auth | Purpose | Status |
|--------------|----------|--------|----------|------|---------|--------|
| auth_service.dart | register | POST | /register | none | create user + token | VERIFIED |
| auth_service.dart | login | POST | /login | none | auth + token | VERIFIED |
| auth_service.dart | fetchProfile | GET | /profile/{user_id} | Bearer | profile | VERIFIED |
| contact_service.dart | fetchContacts | GET | /contacts/{user_id} | Bearer | list contacts | VERIFIED |
| contact_service.dart | addContact | POST | /contacts/add | Bearer | add contact | VERIFIED |
| incident_service.dart | createSos | POST | /incidents/create | Bearer (get_service_or_user) | create incident | VERIFIED |
| incident_service.dart | fetchHistory | GET | /incident/history/{user_id} | Bearer | history | VERIFIED |
| incident_service.dart | fetchLiveIncidents | GET | /incident/live | Bearer | live incidents | VERIFIED |
| incident_service.dart | fetchIncidents | GET | /incidents?limit= | Bearer | list | VERIFIED |
| incident_service.dart | fetchLatestIncident | GET | /incidents/latest?limit=1 | Bearer | latest | VERIFIED |
| incident_service.dart | fetchIncident | GET | /incidents/{id} | Bearer | detail | VERIFIED |
| incident_service.dart | fetchEvidence | GET | /evidence/{incident_id} | Bearer | evidence list | VERIFIED |
| incident_service.dart | watchIncidentEvents | WS | /ws/live | Bearer (query token) | realtime incidents | VERIFIED |
| location_service.dart | sendCurrentLocation (no session) | POST | /location/update | Bearer | GPS point | VERIFIED |
| location_service.dart | startTrackingSession | POST | /tracking/start | Bearer | start session | VERIFIED |
| location_service.dart | _postTrackingUpdate | POST | /tracking/update | Bearer | GPS in session | VERIFIED |
| location_service.dart | fetchLiveLocation | GET | /location/live/{user_id} | Bearer (backend ignores) | last GPS | VERIFIED |
| sos_service.dart | _runEmergencyBackgroundSync | (via above) | /incidents/create, /tracking/start, /tracking/update, /location/update | Bearer | SOS sync | VERIFIED |
| auto_sos_manager.dart | _activateFromEvent | POST | /emergency/start | Bearer | start emergency session | VERIFIED |
| auto_sos_manager.dart | _startStatusPolling | GET | /emergency/status?session_id= | Bearer | poll status | BROKEN (backend missing) |
| api_service.dart | publicTrackingUrl | GET | /system/local-network | Bearer | discover tracking base URL | VERIFIED |
| api_service.dart | checkBackendHealth | GET | /health, / | none | health | VERIFIED |
| api_service.dart | publicMediaUrl / publicJson | GET | /uploads/... (static) | Bearer | media/metadata | VERIFIED |
| evidence_capture_service.dart | _uploadRecord | POST | /evidence/upload | Bearer | upload encrypted evidence | VERIFIED |
| camera_service.dart | registerCamera / listCameras | POST/GET | /camera/register, /camera/list | Bearer | CCTV (UNUSED) | BROKEN REFERENCE |
| (none) | cancel | — | /emergency/cancel or /emergency/status | — | cancel session | NOT IMPLEMENTED backend-side |

## 9. Backend Compatibility

| Feature | Flutter Endpoint | Backend Endpoint | Request Match | Response Match | Auth Match | Status |
|---------|------------------|------------------|---------------|----------------|------------|--------|
| Register | POST /register | POST /register | YES | YES (user_id, access_token) | none | VERIFIED |
| Login | POST /login | POST /login | YES | YES | none | VERIFIED |
| Profile | GET /profile/{id} | GET /profile/{user_id} | YES | YES | Bearer | VERIFIED |
| Contacts list | GET /contacts/{id} | GET /contacts/{user_id} | YES | YES | Bearer | VERIFIED |
| Contacts add | POST /contacts/add | POST /contacts/add | YES (ContactCreate) | YES | Bearer | VERIFIED |
| Incidents create | POST /incidents/create | POST /incidents/create | YES (IncidentCreate) | YES (incident + emergency_session) | get_service_or_user | VERIFIED |
| Incident history | GET /incident/history/{id} | GET /incident/history/{user_id} | YES | YES (incidents) | Bearer | VERIFIED |
| Incident live | GET /incident/live | GET /incident/live | YES | YES (incidents) | Bearer | VERIFIED |
| Incidents list | GET /incidents?limit= | GET /incidents | YES | YES (incidents) | Bearer | VERIFIED |
| Incident latest | GET /incidents/latest?limit=1 | GET /incidents/latest | YES | YES | Bearer | VERIFIED |
| Incident detail | GET /incidents/{id} | GET /incidents/{incident_id} | YES | YES (incident) | Bearer | VERIFIED |
| Evidence list | GET /evidence/{id} | GET /evidence/{incident_id} | YES | YES (evidence) | Bearer | VERIFIED |
| Location update | POST /location/update | POST /location/update | YES (LocationUpdate) | YES | Bearer | VERIFIED |
| Tracking start | POST /tracking/start | POST /tracking/start | YES (TrackingStart) | YES (session_out) | Bearer | VERIFIED |
| Tracking update | POST /tracking/update | POST /tracking/update | YES (TrackingUpdate) | YES | Bearer | VERIFIED |
| Live location | GET /location/live/{id} | GET /location/live/{user_id} | YES | YES | none in backend route | VERIFIED (auth loose) |
| WS live | WS /ws/live | WS /ws/live | YES | YES (nested incident) | query token (hub connects w/o verify) | VERIFIED (auth loose) |
| Emergency start | POST /emergency/start | POST /emergency/start | YES (EmergencyStartRequest) | YES (session) | Bearer | VERIFIED |
| Emergency status | GET /emergency/status | **NOT FOUND** | NO | NO | — | **BROKEN** |
| System local network | GET /system/local-network | GET /system/local-network | YES | YES (base_url) | none in backend | VERIFIED |
| Evidence upload | POST /evidence/upload | POST /evidence/upload | YES (EvidenceUpload) | YES | Bearer | VERIFIED |
| Camera register/list | POST/GET /camera/* | POST/GET /camera/* | YES | YES | Bearer | VERIFIED but UNUSED |
| Notifications send | (none) | POST /notifications/send | — | — | — | BACKEND ONLY |
| Incident link-user | (none) | POST /incidents/link-user | — | — | — | BACKEND ONLY |

**Compatibility verdict:** Documented FastAPI contract accurately implemented. Only mismatch: `GET /emergency/status` (Flutter polls it; backend has no such route → always 404/exception, gracefully caught). Camera endpoints match but UI never calls them.
## 10. Authentication

Files: `lib/services/auth_service.dart`, `lib/providers/auth_provider.dart`, `lib/services/storage_service.dart`, `lib/services/api_service.dart`.

- Registration: `POST /register` with `{full_name, phone_number, password, profile_photo}`. Response parsed by `User.fromJson` + token from `access_token` (or `token`).
- Login: `POST /login` with `{phone_number, password}`. Same token extraction.
- Token storage: `StorageService` uses `FlutterSecureStorage` (key `sheguard_auth_token`). User JSON under `sheguard_user`. NOT plain SharedPreferences.
- Token usage: `ApiService.setAuthToken(token)` → `_authToken`; `_headers` adds `Authorization: Bearer <token>`.
- Token restore: `AuthProvider.restore()` → `restoreToken()` reads secure token → `restoreSession()` reads user → `fetchProfile(user.userId)` (re-validates). On failure → Splash routes to Login.
- Logout: clears secure storage + `_authToken = null`.
- User ID source: backend `user_id` int from `/register` and `/login`. NOT hardcoded. No hardcoded phones/test users.
- 401 handling: backend 401 → `ApiException(detail)` → SnackBar. Protected routes 401/403 surfaced as `ApiException(statusCode)`. NO global 401 redirect / token refresh interceptor.
- Token expiration: no special handling; expired calls fail with backend 401, user sees detail.
- Authorization header: `Bearer` (verified in `api_service._headers` and WS connect).

Status: **IMPLEMENTED / VERIFIED**.

## 11. Network Configuration

File: `lib/config/api_config.dart`, `lib/core/app_config.dart`, `lib/services/api_service.dart`.

```
ApiConfig.baseUrl = 'http://192.168.1.3:8000'   // HARDCODED LAN IP
ApiConfig.publicTrackingBaseUrl = String.fromEnvironment('SHEGUARD_PUBLIC_TRACKING_BASE_URL', defaultValue: '')
AppConfig.baseUrl = ApiConfig.baseUrl
AppConfig.apiTimeout = 120s (AppConfig), 30s (ApiService)  // two different timeouts
```

`ApiService.resolveLocalBaseUrl()`: returns `ApiConfig.baseUrl.trim()`; writes it to SharedPreferences `sheguard_local_base_url` (NEVER reads it back → dead store); throws if empty.

WS URI: `websocketUri()` converts http→ws, https→wss, keeps path/query, adds `token` query + `Authorization` header.

### COMPLETE NETWORK CONFIGURATION TABLE

| File | Variable/Function | URL/IP | Port | Purpose | Hardcoded? | Current Status |
|------|------------------|-------|------|---------|------------|----------------|
| config/api_config.dart | ApiConfig.baseUrl | http://192.168.1.3:8000 | 8000 | API + WS + media base | YES | CURRENT (active LAN IP) |
| config/api_config.dart | publicTrackingBaseUrl | from --dart-define=SHEGUARD_PUBLIC_TRACKING_BASE_URL | build | public tracking base | build-time, default '' | UNUSED (never read) |
| core/app_config.dart | AppConfig.baseUrl | = ApiConfig.baseUrl | 8000 | alias | YES | CURRENT |
| services/api_service.dart | ApiService.baseUrl | = ApiConfig.baseUrl | 8000 | static getter | YES | CURRENT |
| services/foreground_tracking_service.dart | baseUrl default | ApiConfig.baseUrl / passed base_url | 8000 | foreground GPS upload | YES (default) | CURRENT |
| services/api_service.dart | websocketUri | derived from baseUrl | 8000 | WS /ws/live | derived | CURRENT |
| docs (README etc.) | example IP | http://10.228.102.43:8000 | 8000 | doc example | DOC ONLY | OLD / DOC ONLY |
| docs (AUTO_SOS_INTEGRATION etc.) | dart-define example | SHEGUARD_API_BASE_URL=http://10.228.102.43:8000 | — | doc example | DOC ONLY | NOT WIRED (no such constant in code) |

Old/dead: `10.228.102.43:8000` ONLY in Markdown docs. `192.168.1.3:8000` is the single active hardcoded address. No `10.22.3.43`, no `localhost:8000`, no `127.0.0.1` in source. `sheguard_local_base_url` written but never read → dead. `SHEGUARD_PUBLIC_TRACKING_BASE_URL` declared but never consumed → dead. `SHEGUARD_API_BASE_URL` (docs) does NOT exist in code → doc describes unimplemented feature.

## 12. Network Dependency

**DOES THE APP REQUIRE SAME WIFI / SAME LAN? — YES (currently).** `ApiConfig.baseUrl` is hardcoded to `http://192.168.1.3:8000` (RFC1918 private). Phone must route to that IP → same Wi-Fi/LAN as backend host. Not reachable over cellular/public internet.

**DOES IT REQUIRE THE LAPTOP'S CURRENT IP? — YES, indirectly.** The hardcoded `192.168.1.3` is the backend host LAN IP; if it changes, all requests fail until the Dart constant changes and app rebuilt.

**CAN THE APP WORK FROM ANOTHER NETWORK? — NO** (without host reachable at that IP). Cellular or different Wi-Fi that cannot reach `192.168.1.3` fails all calls.

**CAN THE APP WORK WITHOUT CHANGING THE IP EVERY TIME? — NO.** No runtime URL settings screen; no SharedPreferences override (stored `sheguard_local_base_url` never read); no `--dart-define=SHEGUARD_API_BASE_URL` support in code (only unused `SHEGUARD_PUBLIC_TRACKING_BASE_URL`); no env/.env loading.

**IS THERE A CLOUD/PUBLIC BACKEND? — NO VERIFIED CLOUD BACKEND FOUND.** All URLs are LAN `192.168.1.3:8000`, cleartext HTTP (`usesCleartextTraffic="true"`), no HTTPS configured.

**Conclusion:** Mobile app bound to single hardcoded LAN IP. To work across networks without rebuild it needs runtime-configurable base URL, public/cloud hostname, or a `--dart-define` constant actually wired into `ApiConfig.baseUrl`. None exist today.
## 13. SOS

File: `lib/services/sos_service.dart` (`SosService.activate`), called from `home_screen._triggerSos`.

**Manual SOS flow (verified):**
1. User holds SOS (3s countdown) → `_startSosCountdown` → `_triggerSos(silent)`.
2. `IncidentProvider.beginSos()` sets loading.
3. `SosService.activate(...)`:
   - `sessionId = 'sos-<utcMillis>'` (unless override); throttles duplicates within 30s.
   - `EmergencyCallService.callPrimaryImmediately` → direct call (or dialer fallback) to first visible contact.
   - `NotificationService` shows emergency-mode / silent / live-tracking / SOS-activated notifications.
   - `EmergencySirenService.start()` (if enabled & not silent).
   - `EvidenceCaptureService.startEmergencyCapture(sessionId)` → audio + front-camera still (AES encrypted locally).
   - `startEmergencyTracking(sessionId)` → `LocationProvider.start` → foreground GPS loop.
   - `_runEmergencyBackgroundSync(...)` (async):
     - `publicTrackingUrl(sessionId)` → `GET /system/local-network` → builds `http://<base>/track/<sessionId>`.
     - `LocationService.currentUpdate` (GPS; last-known fallback).
     - `EmergencySmsService.sendEmergencySms` → multipart SMS to contacts with Maps link + tracking URL.
     - `LocationService.startTrackingSession` → `POST /tracking/start`.
     - `LocationService.sendCurrentLocation` → `POST /tracking/update` (or `/location/update`).
     - `IncidentService.createSos` → `POST /incidents/create` (manual_sos/silent_sos, confidence 1, threat_score 10, ai_summary, send_alert true).
     - `_storeSession` → SharedPreferences `emergency_sessions`.
4. UI: `IncidentProvider.completeSos` + `SafetyProvider.activateEmergency`. Error → `IncidentProvider.failSos`.

**What SOS actually does (verified):** creates incident; creates tracking session; sends GPS; sends SMS; calls first contact; captures + locally encrypts evidence; stores local session; shows local notifications + siren.

**What SOS does NOT do:** notify police via app (no police endpoint; backend may Telegram a parent chat, backend-only); trigger CCTV/AI itself (those are backend-ingested; mobile only creates manual_sos/silent_sos); upload evidence automatically on success (best-effort queue); open the public tracking web page (only builds URL into SMS).

Status: **IMPLEMENTED / VERIFIED** (manual + silent). Auto-SOS separate, handled by `AutoSosManager` from WS events.

## 14. Emergency Sessions

- Local: `SosService._storeSession` → SharedPreferences `emergency_sessions` (≤20 records: session_id, user_id, silent, started_at, lat/lng, sms counts, incident_id, incident_response). `AutoSosManager` persists active session `active_auto_sos_session` + handled events `handled_auto_sos_events`.
- Backend: `POST /tracking/start` creates `TrackingSession`; `/incidents/create` may spawn `EmergencySession` + `incident_session`. Mobile `session_id` (`sos-<ts>`) used as `TrackingSession.session_id` and public `/track/<session_id>`.
- Auto-SOS: `POST /emergency/start` creates backend `EmergencySession` (returns `session` with `tracking_url`). Mobile uses returned `tracking_url` if present.
- Cancellation: "I'm safe" stops local tracking + sos services + clears `active_auto_sos_session`. Does NOT call backend cancel endpoint (none exists; `/emergency/status` polling broken).

Status: **IMPLEMENTED / VERIFIED** (local + backend start). Cancel is local-only.

## 15. Location

Files: `lib/services/location_service.dart`, `lib/providers/location_provider.dart`, `lib/services/foreground_tracking_service.dart`.
- Package: `geolocator` + `geocoding` + `battery_plus`.
- Permission: `Geolocator.isLocationServiceEnabled` + check/request; accepts `always` or `whileInUse`.
- Accuracy: `LocationAccuracy.bestForNavigation`, timeout 60s.
- Foreground vs background: non-session uses `Geolocator.getPositionStream` with `AndroidSettings(foregroundNotificationConfig)`; session uses `ForegroundTrackingService` (separate isolate) posting `/tracking/update` every 5s.
- Payload (`LocationUpdate.toJson`): user_id, session_id (opt), latitude, longitude, speed, heading (opt), battery (opt), accuracy (opt), timestamp (UTC ISO).
- Offline queue: `offline_tracking_queue` SharedPreferences (≤200/300); `syncQueuedTrackingUpdates` flushes on next update.
- Reverse geocode: `geocoding` → `placeLabel`.
- Endpoints: `sendCurrentLocation` → `/location/update` (no session) or `/tracking/update` (session); `startTrackingSession` → `/tracking/start`; `fetchLiveLocation` → `/location/live/{user_id}`.
- Error handling: GPS denied → `ApiException`; SMS fallback uses last-known; foreground retry loop 3s backoff + error stream.

Status: **IMPLEMENTED / VERIFIED**. Continuous during SOS/session (5s), foreground stream when tracking enabled, manual on refresh.

## 16. Tracking

File: `lib/services/location_service.dart`, `lib/services/foreground_tracking_service.dart`.

**START:** `LocationProvider.start(user.userId, sessionId?)` → `LocationService.startTracking(...)`: sessionId != null → `ForegroundTrackingService.startEmergencyTracking` (background isolate) + listens to its streams; else `Geolocator.getPositionStream` (foreground notification) → `onUpdate`. `SosService` also calls `startTrackingSession` (`POST /tracking/start`).

**UPDATE:** every 5s (or on position change): build `LocationUpdate`, POST `/tracking/update` (session) or `/location/update`. On failure queue to `offline_tracking_queue`.

**STOP:** `LocationProvider.stop()` → `LocationService.stopTracking()` → cancel subscription + `ForegroundTrackingService.stopEmergencyTracking()`.

Status: **IMPLEMENTED / VERIFIED**. Backend `TrackingSession` rows created/updated; public `/track/<session_id>` HTML consumes them.

## 17. Incidents

Files: `lib/models/incident.dart`, `lib/services/incident_service.dart`, `lib/providers/incident_provider.dart`, `lib/screens/incident_history_screen.dart`.
- Mobile creates incidents via `IncidentService.createSos` → `POST /incidents/create` (manual_sos/silent_sos). Backend stores, computes threat score, links user, may start incident_session + send Telegram.
- Mobile receives incidents: (1) polling `IncidentProvider.refreshIncidentFeedSilently` every 5s → `GET /incidents`; (2) WebSocket `IncidentProvider.startIncidentRealtime` → `watchIncidentEvents` → `WS /ws/live`, filters `incident.created`/`incident.merged`.
- Incident fields parsed (rich): incident_id, user_id, incident_type, confidence (/100 normalized), threat_score, threat_level, kidnap_suspicion_score, ai_summary, ai_provider, explanation, camera_id, image/video/metadata paths, incident_folder_id (derived from `/uploads/incidents/...`), status, evidence.
- AI/CCTV attributes originate from backend AI/CCTV pipeline, NOT mobile.
- Linking: backend auto-links via `SmartIncidentResponseService` (proximity). Mobile displays `linked_user` if present. No "link incident to me" UI (backend `/incidents/link-user` unused by app).
- Acknowledgement: mobile shows "Emergency Detected" popup + vibrates + auto-dials parent (UI only, no backend ACK call).
- Evidence per incident: `IncidentProvider.loadEvidence` → `GET /evidence/{id}`.

Status: **IMPLEMENTED / VERIFIED** (feed, detail, history, WS, media). Mobile is consumer + manual-SOS creator; AI/CCTV generation backend-only.
## 18. CCTV

Search: CCTV, camera, camera_id, RTSP, nearby camera, camera alert, camera location, camera notification, incident camera, live feed.
- Model: `CameraSource` (camera_id, camera_name, ip_address, rtsp_url, lat/lng, online_status). Matches backend `CCTVCamera`.
- Service: `CameraService` (`registerCamera` POST /camera/register, `listCameras` GET /camera/list). **Never instantiated/called anywhere** (only self-references). Status: **IMPLEMENTED / BROKEN REFERENCE** (dead code).
- Backend support: `/camera/register`, `/camera/list`, `/camera/health` exist. CCTV incidents carry `camera_id`.
- Mobile CCTV features: NONE in UI — no discovery, no nearby lookup, no alert screen, no live feed viewer, no camera map. Incident feed displays `camera_id` on detail + incident media (possibly CCTV-sourced), but no dedicated CCTV UX.

**Verdict:** ACTUALLY IMPLEMENTED in mobile: only `camera_id` display + unused `CameraService`. BACKEND SUPPORT ONLY: camera register/list/health, CCTV ingestion. DOCUMENTATION ONLY: any mobile CCTV discovery/nearby/live feed. Status: **NOT IMPLEMENTED** (mobile CCTV UX); `CameraService` **IMPLEMENTED / BROKEN** (unused).

## 19. AI

Search: AI endpoint, provider, ai_summary, confidence, threat_score, threat_level, kidnap_suspicion_score, explanation, ai_provider.
- Mobile does NOT call any AI provider (no Groq/Gemini/OpenRouter/HuggingFace/NVIDIA; no AI API keys; no HTTP to AI hosts beyond backend base URL).
- Architecture: `Flutter → Backend → (AI/CCTV pipeline)`. Backend (`cloud_ai.py`, `advanced_threat.py`, `threat.py`, `groq_client.py`) performs AI scoring. Mobile consumes resulting `Incident` fields.
- `Incident.toSosJson` sets `ai_summary` to a static string and `confidence:1.0`, `threat_score:10` for manual/silent SOS — mobile's own SOS incidents are NOT AI-scored (user-triggered).
- `auto_sos_manager` reacts to backend AI/CCTV events (`incident.created` with `source: ai_cctv`) by starting an emergency; the AI decision happens on backend.

Status: **IMPLEMENTED / VERIFIED** (mobile is consumer of AI results; AI inference backend-only). No direct mobile→AI link.

## 20. Evidence / Media

Files: `lib/services/evidence_capture_service.dart`, `lib/models/evidence.dart`, `lib/services/incident_service.dart`, `lib/services/api_service.dart`.
- Capture: on SOS, `EvidenceCaptureService.startEmergencyCapture(sessionId)`: audio (`record` AAC-LC/m4a to app support `evidence/`); front camera still (`camera`, `CameraLensDirection.front`). Each file AES-256-GCM encrypted (`cryptography` AesGcm), original deleted, ciphertext stored as `<sessionId>-<type>-<ts>.<ext>.enc`. Key in `FlutterSecureStorage` (`sheguard_evidence_key_v1`). Manifest in SharedPreferences `encrypted_evidence_manifest`; upload queue `encrypted_evidence_upload_queue`.
- Upload: `_uploadRecord` POSTs `POST /evidence/upload` with `{session_id, evidence_type, filename, content_base64, encrypted:true, created_at}`. Backend decodes base64, writes `uploads/evidence/`. (No multipart; base64 JSON.)
- Incident media display: `IncidentService` computes folder paths `/uploads/incidents/<folderId>/thumbnail.jpg|incident_video.mp4|metadata.json`. `ApiService.publicMediaUrl` resolves to `<base>/uploads/...`. `incident_history_screen` shows `Image.network` + `launchUrl` video.
- Backend evidence: `GET /evidence/{id}` returns `Evidence` rows. Also `EvidenceRecord` (public_url), `GET /evidence/file` (path-based, auth-restricted).
- Permissions: CAMERA, RECORD_AUDIO.
- Issues: capture best-effort (failures swallowed); upload depends on `_api` non-null (injected OK); **evidence uploaded by `session_id` only, not `incident_id`** → backend stores standalone, may NOT appear under incident evidence list (**broken integration link, NOT fixed**); no file-size limit.

Status: **IMPLEMENTED / VERIFIED** (capture + encrypt + upload path exists; backend supports it). Caveat: mobile evidence not guaranteed associated with SOS incident. Media display VERIFIED.

## 21. Notifications

File: `lib/services/notification_service.dart`, `lib/providers/safety_provider.dart`, `lib/providers/location_provider.dart`.
- Local notifications only (`flutter_local_notifications`). Channels: `sheguard_alerts` (high), `sheguard_emergency` (max, full-screen intent, public, ongoing).
- NO FCM/Firebase/push (no `firebase_messaging`, no google-services).
- Triggers (local): SOS activated (4), live tracking (6), emergency mode (7), silent (8), GPS disabled (2), tracking interrupted (3), incident created (4/5), backend reconnecting (20/30/31), realtime restored (31). `showFullScreenEmergency` (id 99) called via `showAutoSosActivatedForEvent` from AutoSosManager.
- SMS: `telephony` multipart to all visible contacts (Maps + tracking URL).
- Phone call: `EmergencyCallService` direct-calls first contact (20s fallback to next).
- Telegram/police/backend notification: backend-only. Mobile sends nothing to Telegram, no police API.
- Realtime reconnect UX: debounced reconnect notification (5-min cooldown) + restored on reconnect.

Status: **IMPLEMENTED / VERIFIED** (local + SMS + call). Push/FCM NOT IMPLEMENTED. Telegram BACKEND ONLY.

## 22. WebSocket / Realtime

Files: `lib/services/emergency_realtime_service.dart`, `lib/services/incident_service.dart` (`watchIncidentEvents`), `lib/providers/incident_provider.dart`, `lib/services/auto_sos_manager.dart`.
- WS endpoint: `WS /ws/live` (built by `ApiService.websocketUri`). Query `user_id` + `token`; `Authorization: Bearer` header on connect (`IOWebSocketChannel.connect`).
- Events: `incident.created`, `incident.merged` (feed + auto-SOS). Heartbeat `ping` every 25s.
- Reconnection: exponential backoff `[2,5,10,20,40,60]s`, state machine (idle/connecting/connected/reconnecting/disconnected/failed). Outage notification on first drop, restored on reconnect.
- Auto-SOS: `AutoSosManager` subscribes to `realtime.events`; on event for current user within 1500m of current GPS → `POST /emergency/start` + `SosService.activate(createIncident:false)`.
- IncidentProvider uses WS for feed + 5s polling fallback.
- Backend WS: `realtime.py` exposes `/ws/live` and `/ws/emergency/{session_id}`; `realtime_hub` broadcasts. Mobile only connects `/ws/live`.
- Auth note: backend `/ws/live` connects without verifying token in route (hub connects any client); mobile sends token. Security: loose.

Status: **IMPLEMENTED / VERIFIED** (WebSocket realtime used for feed + auto-SOS).
## 23. Local Storage

- Secure: `FlutterSecureStorage` (`StorageService`): `sheguard_user`, `sheguard_auth_token`. `EvidenceCaptureService` key `sheguard_evidence_key_v1`.
- SharedPreferences: `sheguard_local_base_url` (written, never read — dead); settings flags (notifications_enabled, silent_mode_enabled, privacy_guard_enabled, tracking_enabled, shake_sos_enabled, fall_detection_enabled, shake_sensitivity, auto_emergency_call_enabled, emergency_siren_enabled, developer_mode_enabled); `contact_metadata` (favorites/hide); `emergency_sessions` (≤20); `active_auto_sos_session`, `handled_auto_sos_events`; `offline_tracking_queue` (≤200/300); `encrypted_evidence_manifest`, `encrypted_evidence_upload_queue`.
- Filesystem: app support `evidence/` for encrypted media. Backend media served from `/uploads`.
- Security: token + evidence key in secure storage (acceptable). GPS/contact data in SharedPreferences plaintext (acceptable; privacy guard only UI). No sensitive secrets logged.

Status: **IMPLEMENTED / VERIFIED**. No secrets exposed.

## 24. Permissions

AndroidManifest (`android/app/src/main/AndroidManifest.xml`):
- `ACCESS_FINE_LOCATION`, `ACCESS_COARSE_LOCATION`, `ACCESS_BACKGROUND_LOCATION` (location/tracking).
- `INTERNET`, `ACCESS_NETWORK_STATE`.
- `SEND_SMS` (emergency SMS). `CALL_PHONE` (emergency call).
- `CAMERA`, `RECORD_AUDIO` (evidence). `POST_NOTIFICATIONS`. `USE_FULL_SCREEN_INTENT`.
- `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_LOCATION` (background tracking; service typed `location`).
- `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`. `RECEIVE_BOOT_COMPLETED`, `WAKE_LOCK`. `VIBRATE`.
- `<uses-feature android.hardware.telephony required="false">`, camera `required="false"`. `queries` intent `DIAL` + `tel:`. `android:usesCleartextTraffic="true"`.
Runtime requests: location (geolocator), SMS (telephony), camera (permission_handler), notification (permission_handler), battery (permission_handler), call (flutter_phone_direct_caller internal).

Analysis: all declared permissions actually used by corresponding features. No obviously unnecessary permission. `ACCESS_BACKGROUND_LOCATION` declared + foreground service typed `location`; tracking primarily runs while app foreground/active or via foreground-service isolate — true background-after-kill not auto-started (autoStart=false).

Status: **IMPLEMENTED / VERIFIED**.

## 25. Android / iOS Configuration

- Package/Application ID: default Flutter `com.example.sheguard_app` (not opened in detail). `android:label="SheGuard"`, icon `@drawable/sheguard_icon`, `usesCleartextTraffic="true"`.
- Min/target SDK: not opened (build.gradle exists). **NOT VERIFIED** for SDK numbers.
- Foreground service: `id.flutter.flutter_background_service.BackgroundService`, `foregroundServiceType="location"`.
- Network security: cleartext HTTP allowed (required for LAN IP). No network-security-config referenced.
- Firebase: none configured. Deep links: none.
- iOS: default Flutter Runner present; `Info.plist` not inspected → **NOT VERIFIED** for iOS-specific permissions/plist. iOS background GPS limited by platform.

Status: **PARTIALLY VERIFIED** (AndroidManifest fully verified; SDK versions + iOS plist NOT VERIFIED — those files were not opened in this audit).

## 26. Error Handling

`lib/services/api_service.dart` `ApiException` + `_decode`:
- `SocketException` → "No internet connection."
- `TimeoutException` → "SheGuard_AI backend timed out."
- `ClientException` → "Could not reach SheGuard_AI backend."
- Non-2xx → `ApiException(detail)` (backend `detail`) with `statusCode`.
- JSON parse failure → "Invalid response."
Provider-level: each provider sets `error` on catch + `notifyListeners()`; screens show `Text(provider.error)` or reconnect banner. SOS failures → SnackBar.
- 401/403: surfaced as `ApiException(detail)` (e.g., "Invalid phone number or password"). No global redirect to login.
- 404: backend returns for missing incident/location; caught + shown.
- 422: Pydantic validation → 422 detail shown.
- 500: backend DB failure → generic message.
- Location denied: `ApiException('GPS permission is required...')`.
- Token expired: no special handling; call fails with backend 401, user sees detail.
- Backend unavailable: `SafetyProvider` shows "Reconnecting..."; SOS still attempts SMS with GPS fallback (graceful degradation).

Status: **IMPLEMENTED / VERIFIED** (reasonable, user-facing error states).

## 27. State Management

- Package: `provider` (`MultiProvider` + `ChangeNotifierProvider`/`Provider.value` + `ChangeNotifier`). NO Bloc/Riverpod/GetX.
- Global state: `AuthProvider` (user, token, login/register/logout, loading, error); `ContactProvider` (contacts, visibleContacts, loading, error); `LocationProvider` (lastLocation, tracking, permissionGranted, error, placeLabel, freshness); `IncidentProvider` (history, liveIncidents, loading, emergencyMode, realtimeConnected, error, pendingEmergencyIncident; WS + polling); `AutoSosManager` (activeEvent, lastLocation, realtimeState, active, gpsActive, sessionId, countdown, contact counts, parent call, error); `SafetyProvider` (backendStatus, protectionStatus, online, message); `SettingsProvider` (toggles).
- SOS state: `IncidentProvider.beginSos/completeSos/failSos` + `SafetyProvider.activateEmergency/resolveEmergency`.

Status: **IMPLEMENTED / VERIFIED** (provider-based, clear separation).

## 28. Models

| Model | File | Key Fields | Used By | Backend Equivalent | Status |
|-------|------|-----------|---------|-------------------|--------|
| User | models/user.dart | user_id, full_name, phone_number, profile_photo | AuthProvider, AutoSosManager | User (users.py) | VERIFIED |
| Login/Register | inline auth_service | full_name, phone_number, password, profile_photo | AuthService | LoginRequest/RegisterRequest | VERIFIED |
| Incident | models/incident.dart | incident_id, user_id, incident_type, confidence, threat_score, threat_level, kidnap_suspicion_score, ai_summary, ai_provider, explanation, camera_id, image/video/metadata paths, incident_folder_id, status, evidence | IncidentProvider, screens | Incident (incidents.py) | VERIFIED (rich) |
| EmergencyContact | models/emergency_contact.dart | contact_id, user_id, contact_name, relation, phone_number, isFavorite, isHidden, local overrides | ContactProvider, SOS, call | EmergencyContact (contacts.py) | VERIFIED |
| EmergencyEvent | models/emergency_event.dart | event_id, user_id, incident_type, created_at, incident_id, session_id, session_token, lat/lng, confidence, tracking_url, evidence_links, details | AutoSosManager, realtime | backend WS incident.created payload | VERIFIED |
| Evidence | models/evidence.dart | evidence_id, incident_id, image_path, video_path, cctv_source, created_at, confidence, threat_score | IncidentProvider | Evidence (incidents.py) | VERIFIED |
| CameraSource | models/camera_source.dart | camera_id, camera_name, ip_address, rtsp_url, lat/lng, online_status | CameraService (unused) | CCTVCamera (cameras.py) | VERIFIED (unused) |
| LocationUpdate | models/location_update.dart | user_id, session_id, latitude, longitude, speed, heading, accuracy, battery, timestamp | LocationService, SOS, realtime | LiveLocation/TrackingUpdate | VERIFIED |

Cross-check: field names match backend `incident_out`/`location_out`/`contact_out`/`evidence_out`. `Incident.fromJson` defensive (aliases, /100 normalization) — compatible.

Status: **IMPLEMENTED / VERIFIED**.
## 29. Security

Scan: hardcoded passwords/tokens/API keys, exposed secrets, insecure storage, HTTP vs HTTPS, hardcoded IP, cert bypass, unsafe logging, plaintext media, missing auth, authz problems.
- Hardcoded IP: `192.168.1.3:8000` (LAN IP, not a secret, but a hard deployment constraint).
- HTTP (not HTTPS): all traffic `http://`; Android `usesCleartextTraffic="true"`. Required for LAN dev, insecure for public exposure.
- No hardcoded passwords/tokens/API keys. `access_token` from backend login. Evidence AES key generated per-install in secure storage.
- Token storage: `FlutterSecureStorage` (encrypted at rest). OK.
- Authorization header: `Bearer` on REST + WS. OK.
- Backend authz gaps (not mobile fault, relevant): several backend routes (`/location/live/{id}`, `/system/local-network`, `/ws/live`) do not enforce auth in route; `/incidents/create` uses `get_service_or_user` (login token accepted). Mobile sends its user token, accepted.
- Certificate bypass: none.
- Unsafe logging: only non-sensitive `debugPrint` (status strings, lat/lng, session ids). No passwords/tokens/PII printed.
- Insecure file storage: evidence AES-256-GCM encrypted at rest; key in secure storage; original deleted after encryption.
- Sensitive data in SharedPreferences: GPS/contact plaintext — acceptable; privacy guard UI-only.

**No secrets to redact in this report.** Primary risks: LAN-only HTTP + hardcoded IP (operational, not leaked-secret).

Status: **IMPLEMENTED / VERIFIED** (no critical mobile-side secret exposure).

## 30. Documentation Comparison

| Doc claim | Actual code | Verdict |
|-----------|-------------|---------|
| README "Configured to use http://10.228.102.43:8000" | Code uses 192.168.1.3:8000 | OUTDATED (doc IP wrong) |
| README "Set base URL in lib/core/app_config.dart" | Constant is lib/config/api_config.dart (core/app_config only re-aliases) | MISLEADING (wrong file) |
| README/ARCH "health uses GET /incident/live?limit=1" | Code uses GET /health then /; fetchLatestIncident uses /incidents/latest?limit=1 | PARTIAL |
| README "run with --dart-define=SHEGUARD_API_BASE_URL=..." | No such constant in code (only unused SHEGUARD_PUBLIC_TRACKING_BASE_URL) | DOCUMENTED ONLY / NOT WIRED |
| PROJECT_STATUS "Evidence upload: no backend upload endpoint exists" | Backend DOES implement POST /evidence/upload; app calls it | OUTDATED |
| ARCHITECTURE "POST /incident/create" | Code calls /incidents/create | OUTDATED (path changed to plural) |
| README lists implemented screens | Matches actual screens | MATCHES |
| Docs describe auto-SOS via WS incident.created | Code does exactly this | MATCHES |
| PROJECT_STATUS "Admin dashboard / CCTV AI pipelines outside this workspace" | Confirmed: no CCTV UI, no dashboard | MATCHES (honest) |

Conclusion: Docs largely accurate about features but contain stale IPs, wrong config file path, non-existent `--dart-define` key, and outdated claim that evidence upload has no backend endpoint. Actual code is MORE complete than some docs imply.

## 31. Tests

Files: `test/widget_test.dart`, `test/model_payload_test.dart`.
- `widget_test.dart`: trivial smoke test (renders `Text('SheGuard')` in `MaterialApp`). Does NOT test real widget/screen.
- `model_payload_test.dart`: unit tests for `LocationUpdate.toJson`, `Incident.toSosJson` (manual/silent), `Incident.fromJson` (extended AI fields + folder derivation), `EmergencyContact` local metadata + payload shape. Meaningful contract tests.
- NO integration/auth/SOS/location/incident/WS/API tests against running backend.

Status: **IMPLEMENTED / VERIFIED** (model tests present; broad coverage absent). Safe to run (`flutter test`), non-destructive.

## 32. Dead / Old / Duplicate Code

- Unused service: `CameraService` — defined, never called. **DEAD CODE**.
- Unused constant: `ApiConfig.publicTrackingBaseUrl` (`SHEGUARD_PUBLIC_TRACKING_BASE_URL`) — declared, never read. **DEAD**.
- Dead store: `ApiService._storedBaseUrlKey` (`sheguard_local_base_url`) — written, never read. **DEAD**.
- Unused provider method: `IncidentProvider.triggerSos` — defined, never called. **DEAD**.
- Old IPs in docs only: `10.228.102.43:8000` in README/PROJECT_SUMMARY/AUTO_SOS_INTEGRATION/SIMPLE_INCIDENT_FEED_TESTING. **OLD / DOC ONLY**.
- Duplicate config: `core/app_config.dart` re-aliases `ApiConfig.baseUrl`; `core/api_config.dart` + `core/localhost.dart` re-export `config/api_config.dart`. Minor redundancy.
- Duplicate test docs: "SheGuard_App report/" duplicates markdown files.
- TODO/FIXME: matches mostly inside model `fromJson` field lists + doc comments, not actionable TODOs. No critical TODO/FIXME in service logic.
- Mock/demo data: none hardcoded in app. Test users (e.g., user #9) backend-side, not mobile.

## 33. Current Data Flows

**1. Login** User → LoginScreen → AuthProvider.login → AuthService.login → POST /login → token + user → StorageService (secure) → ApiService.setAuthToken → HomeScreen.
**2. Registration** User → RegisterScreen → AuthProvider.register → AuthService.register → POST /register → token + user → secure storage → HomeScreen.
**3. SOS (manual/silent)** User presses SOS → HomeScreen._triggerSos → SosService.activate → (a) call first contact; (b) SMS to contacts (Maps + tracking URL); (c) evidence capture (AES); (d) foreground tracking → POST /tracking/start + /tracking/update; (e) POST /incidents/create; (f) SharedPreferences emergency_sessions → UI update + local notifications.
**4. Location** Phone GPS (geolocator) → LocationService → POST /location/update or /tracking/update → Backend (LiveLocation/TrackingSession) → public /track/<session> page + WS tracking_update.
**5. Tracking** SOS → POST /tracking/start → 5s GPS loop → POST /tracking/update (offline queue) → Backend TrackingSession + LiveLocation.
**6. Incident (receive)** Backend AI/CCTV or mobile SOS → POST /incidents/create → Backend stores (+ Telegram if score≥5) → broadcasts incident.created via WS /ws/live → Mobile feed + popup + auto-dial.
**7. Evidence** Phone (mic + front camera) → EvidenceCaptureService (AES-256-GCM) → local evidence/ dir → (best-effort) POST /evidence/upload → Backend uploads/evidence/. (Incident association NOT guaranteed.)
**8. Notifications** Local: SOS/status → NotificationService → flutter_local_notifications. SMS: SOS → EmergencySmsService → telephony → contacts. Call: SOS → EmergencyCallService → dialer. Backend→Telegram: backend-only.
**9. CCTV** Backend CCTV → Incident with camera_id → POST /incidents/create → Mobile displays camera_id + media. No mobile CCTV discovery/feed UI.
**10. AI** Backend AI → Incident fields (ai_summary, threat_score, explanation, ai_provider) → Mobile consumes/displays. No mobile→AI link.

All flows VERIFIED from source.
## 34. Current Architecture

```
Flutter Mobile App (SheGuard App)
        |
        |  HTTP (http://192.168.1.3:8000) + WS (/ws/live)
        v
SheGuard Backend (FastAPI :8000)
        |
        +---- PostgreSQL/SQLite (DB)           [verified: models + routes]
        +---- AI / Threat pipeline             [verified: backend services, mobile consumes results]
        +---- CCTV ingestion                  [verified backend; mobile only displays camera_id]
        +---- Telegram alerts                 [verified backend; mobile NOT involved]
        +---- Public /track/<session> page    [verified backend HTML; mobile builds URL only]
        +---- Static /uploads (media)         [verified; mobile displays via publicMediaUrl]

Mobile-only local services (no backend):
  - Encrypted evidence capture (AES-256-GCM)  [verified local]
  - Local notifications (flutter_local_notifications) [verified local]
  - SMS via telephony                         [verified device]
  - Direct phone call                         [verified device]
  - Motion (shake/fall) detection             [verified device]
  - Local contact metadata (favorites/hide)   [verified SharedPreferences]
```

Only verified connections drawn. No cloud, no FCM, no direct AI, no police API from mobile.

## 35. SheGuard Connection Matrix

| Mobile Component | Connected To | Mechanism | Endpoint/URL | Verified? | Status |
|------------------|-------------|-----------|-------------|-----------|--------|
| Flutter App | Backend API | HTTP (http, Bearer) | http://192.168.1.3:8000 | YES | VERIFIED (LAN only) |
| Flutter App | Backend WS | WebSocket | ws://192.168.1.3:8000/ws/live | YES | VERIFIED |
| Flutter App | Database | via Backend | (no direct) | YES | VERIFIED (indirect) |
| Flutter App | AI | via Backend | (no direct) | YES | VERIFIED (consumer only) |
| Flutter App | CCTV | via Backend incident | (no direct) | YES | VERIFIED (display only) |
| Flutter App | Police Dashboard | — | none | NO | NOT IMPLEMENTED |
| Flutter App | Agents | — | none | NO | NOT IMPLEMENTED |
| Flutter App | Notifications (push) | — | none | NO | NOT IMPLEMENTED (local only) |
| Flutter App | Emergency Contacts | SMS + call + WS data | device + GET /contacts | YES | VERIFIED |
| Flutter App | Location | geolocator → Backend | /location/update, /tracking/update | YES | VERIFIED |
| Flutter App | Evidence | camera/record → local encrypt → Backend | POST /evidence/upload | YES | VERIFIED (incident link weak) |
| Flutter App | WebSocket | web_socket_channel | /ws/live | YES | VERIFIED |
| Flutter App | Media Storage | Image.network | <base>/uploads/... | YES | VERIFIED |
| Flutter App | Telegram | (none) | — | NO | BACKEND ONLY |

## 36. Verified Working

Items supported by direct source evidence (mobile side; backend reachability not independently tested, but endpoints/contracts verified):

1. App builds/runs structure (MaterialApp, providers, routes). VERIFIED (static).
2. Registration + Login + token secure storage + Bearer auth. VERIFIED.
3. Profile fetch + session restore. VERIFIED.
4. Emergency contacts list + add (backend). VERIFIED.
5. Manual + Silent SOS orchestration (call, SMS, incident create, tracking start, evidence capture, local session store). VERIFIED.
6. Live GPS tracking via foreground service + /tracking/update + offline queue. VERIFIED.
7. Incident feed (polling + WebSocket) + detail + history + media display. VERIFIED.
8. Auto-SOS from WS incident.created/incident.merged → /emergency/start. VERIFIED (logic).
9. Encrypted evidence capture (AES-256-GCM) + upload path. VERIFIED.
10. Local notifications, reconnect UX, siren, shake/fall detection. VERIFIED.
11. Backend health check + connectivity awareness. VERIFIED.
12. Public tracking URL discovery (/system/local-network) + /track/<session> consumption. VERIFIED.

Caveat: Static audit. Does NOT prove backend at 192.168.1.3:8000 is currently running/reachable. Mobile behavior verified by code contract, not live execution.

## 37. Broken / Incomplete

| # | Item | File | Expected | Actual | Evidence | Severity | Dependency | Next investigation |
|---|------|------|----------|--------|----------|----------|------------|---------------------|
| B1 | /emergency/status polling | auto_sos_manager.dart _startStatusPolling | poll session status to auto-cancel | Backend has NO /emergency/status route → always throws (caught) | backend routes/emergency.py only /emergency/start | MEDIUM | backend route missing | Add backend route or remove polling |
| B2 | CameraService unused | camera_service.dart | CCTV UI | Never called | grep: only self-references | LOW | no UI | Remove or wire a CCTV screen |
| B3 | Evidence↔Incident link weak | evidence_capture_service.dart | uploaded evidence tied to SOS incident | Upload sends only session_id, backend stores standalone; not listed under incident evidence | backend /evidence/upload has no incident_id | MEDIUM | backend schema | Add incident_id to upload + link |
| B4 | Runtime URL config absent | api_config.dart | change backend without rebuild | base URL hardcoded; stored pref never read; SHEGUARD_API_BASE_URL not wired | §11/§12 | HIGH | none | Add runtime/base-url override |
| B5 | Dead SHEGUARD_PUBLIC_TRACKING_BASE_URL | api_config.dart | public tracking override | declared, never read | grep | LOW | none | Wire or remove |
| B6 | Dead sheguard_local_base_url | api_service.dart | persisted base URL | written, never read | grep | LOW | none | Use or remove |
| B7 | IncidentProvider.triggerSos unused | incident_provider.dart | alternative SOS path | defined, never called | grep | LOW | none | Remove or use |
| B8 | Cleartext HTTP | api_config + manifest | secure transport | http:// + usesCleartextTraffic=true | manifest | MEDIUM | network | TLS / reverse proxy |
| B9 | 401 no global redirect | api_service/auth | re-login on expiry | errors surfaced only per-call | code | LOW | backend token TTL | Add interceptor |
| B10 | iOS/SDK versions unverified | android/build.gradle, ios/ | exact min/target SDK | not opened | — | LOW | n/a | Open & record |

## 38. Missing Features

**CRITICAL**
- Runtime-configurable backend URL / cloud backend (currently LAN-locked). (§12, B4)
- Real cross-network operation without rebuild.

**HIGH**
- Incident↔evidence linkage for mobile-captured evidence (B3).
- /emergency/status (or cancel) backend endpoint to reflect "I'm safe" server-side (B1).
- Push notifications (FCM) — currently local only; backend Telegram does not reach the app.
- Police/authority notification from mobile (none; backend Telegram only).

**MEDIUM**
- CCTV discovery / nearby cameras / CCTV live feed UI (backend supports cameras; app does not surface them).
- Incident acknowledgement sent to backend (mobile only shows local popup).
- Contact edit/remove on backend (currently local-only metadata).
- HTTPS/TLS for transport (B8).
- Auto-start background tracking after app kill (foreground service autoStart=false).

**LOW**
- Dedicated incident detail route name (currently push(MaterialPageRoute) only).
- 401 global redirect / token refresh.
- Remove dead code (CameraService, unused constants/methods).
- Emergency contacts notification status tracking from backend (/notifications not consumed by app).
## 39. Next Implementation Plan (ordered by dependency)

1. **Network configurability (FIRST)** — `lib/config/api_config.dart`, `lib/services/api_service.dart`, `lib/providers/settings_provider.dart`. Add a runtime base-URL override (Settings screen + SharedPreferences) and/or wire `--dart-define=SHEGUARD_API_BASE_URL` into `ApiConfig.baseUrl`. Dependency: none. Verification: change URL in settings, confirm `ApiService.baseUrl` resolves to it; login works against a different host. Risk: low (no behavior change to safety logic).
2. **Fix /emergency/status mismatch** — backend: add `GET /emergency/status` (or `/emergency/cancel`); OR remove `AutoSosManager._startStatusPolling`. Dependency: backend. Verification: auto-SOS cancel polls without 404. Risk: low.
3. **Evidence↔Incident linkage** — extend `EvidenceUpload` + `evidence_capture_service` to include `incident_id`; backend links record. Dependency: backend schema. Verification: uploaded evidence appears under incident evidence list. Risk: medium (data model).
4. **CCTV UX** — wire `CameraService` into a screen (list/nearby/discovery) using `/camera/list`. Dependency: none (backend ready). Verification: camera list renders. Risk: low.
5. **Push notifications** — add Firebase/FCM or a backend→WS notify path so the phone receives alerts when app backgrounded. Dependency: FCM project or WS-based push. Risk: medium.
6. **Incident acknowledgement + contact backend edit/delete** — add backend endpoints + mobile calls. Dependency: backend. Risk: low.
7. **TLS** — put backend behind HTTPS/reverse proxy; switch `ApiConfig` to `https`. Dependency: cert. Risk: medium (cleartext fallback needed for LAN).

## 40. FIRST IMPLEMENTATION TASK

**Why first:** Every other mobile limitation (cross-network use, "change IP without rebuild", cloud operation) traces back to the single hardcoded LAN base URL in `lib/config/api_config.dart`. Until the app can resolve its backend URL at runtime (or via a wired `--dart-define`), no other network-dependent feature can be validated on a real device away from `192.168.1.3`. This is also the project's stated end-goal (work without repeatedly changing LAN IPs).

**Files involved:**
- `lib/config/api_config.dart` (make `baseUrl` overridable).
- `lib/services/api_service.dart` (`resolveLocalBaseUrl` currently ignores stored pref — make it read an override).
- `lib/providers/settings_provider.dart` (persist the URL).
- `lib/screens/settings_screen.dart` (add a "Backend URL" field, dev/advanced only).
- Optional: `android/app/src/main/AndroidManifest.xml` (keep cleartext for LAN, or move to HTTPS).

**Backend dependency:** None required for the mobile-side change (it only changes how the URL is sourced). The existing endpoints remain unchanged.

**Expected result:** The app reads the backend base URL from SharedPreferences (with `ApiConfig.baseUrl` as the compile-time default/fallback). A user/developer can point the app at any reachable host (including a different LAN IP or a public hostname) without rebuilding. `ApiService` requests and WebSocket URIs then target that host.

**How to test it (non-destructive):**
1. Add the override + settings field.
2. Run `flutter test` to ensure model/contract tests still pass.
3. In the emulator/device Settings, set the URL to the running backend host.
4. Confirm `SplashScreen` health check + `Login` succeed against that host.
5. Keep `192.168.1.3:8000` as the default so current behavior is preserved.

**Do NOT** modify backend URLs, auth, or safety logic. This task is configuration-only.

---

## Final Summary

SheGuard App is a fully-featured Flutter emergency-safety client with real, contract-accurate integration to the SheGuard FastAPI backend: auth (register/login/secure token), manual + silent SOS (call + SMS + incident + tracking + encrypted evidence), live GPS tracking with offline queue, a WebSocket-backed AI/CCTV incident feed, auto-SOS from backend events, and rich local safety UX (shake/fall detection, siren, fake call, notifications).

The single most important constraint is the **hardcoded LAN backend URL `http://192.168.1.3:8000`** with no runtime override and no cloud backend — the app is LAN-bound and must be rebuilt if the host IP changes. Evidence→incident linkage and an `/emergency/status` backend route are the other verified gaps. No secrets are exposed; transport is cleartext HTTP by design for LAN dev.

**No source code, configuration, dependencies, or secrets were modified during this audit.**
