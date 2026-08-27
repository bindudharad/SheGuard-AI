# Smart Auto SOS Integration

## Updated Mobile Structure

```text
lib/
|-- models/
|   |-- emergency_event.dart        # AI CCTV/backend emergency event DTO
|   `-- location_update.dart        # GPS payload now includes heading
|-- services/
|   |-- emergency_realtime_service.dart
|   |-- auto_sos_manager.dart
|   |-- foreground_tracking_service.dart
|   |-- location_service.dart
|   |-- notification_service.dart
|   `-- sos_service.dart
|-- screens/
|   |-- emergency_mode_screen.dart
|   `-- home_screen.dart
`-- main.dart
```

## Runtime Flow

1. User logs in and reaches `HomeScreen`.
2. `AutoSosManager.bindUser(user)` starts `WS /live/emergency`.
3. Backend sends an emergency incident for the nearest victim phone.
4. App validates user id and nearby incident coordinates.
5. App calls `POST /emergency/start`.
6. App enters Auto SOS Mode.
7. Existing SOS pipeline starts:
   - emergency call queue
   - parent SMS with incident details, evidence links, GPS, and tracking link
   - encrypted local evidence capture
   - Android foreground GPS tracking
   - offline GPS queueing
8. App continuously uploads to `POST /tracking/update`.
9. App polls `GET /emergency/status?session_id=<id>` for resolved/cancelled state.
10. `EmergencyModeScreen` shows live emergency UI.

## Backend API Contract Expected By Mobile

### Websocket

`WS /live/emergency?user_id=<user_id>&token=<auth_token>`

The client also sends an `Authorization: Bearer <token>` header when the platform supports websocket headers.

Accepted event shape:

```json
{
  "type": "emergency_incident",
  "incident": {
    "event_id": "evt-123",
    "incident_id": 42,
    "user_id": 7,
    "session_id": "auto-42",
    "session_token": "optional-session-token",
    "incident_type": "ai_cctv_attack",
    "latitude": 12.9716,
    "longitude": 77.5946,
    "confidence": 0.93,
    "tracking_url": "http://10.228.102.43:8000/track/auto-42",
    "evidence_links": ["http://10.228.102.43:8000/evidence/42/image.jpg"],
    "created_at": "2026-05-12T08:00:00Z"
  }
}
```

### Start Emergency

`POST /emergency/start`

Mobile sends:

```json
{
  "user_id": 7,
  "session_id": "auto-42",
  "incident_id": 42,
  "event_id": "evt-123",
  "incident_type": "ai_cctv_attack",
  "source": "ai_cctv",
  "session_token": "optional-session-token",
  "event_latitude": 12.9716,
  "event_longitude": 77.5946,
  "confidence": 0.93,
  "created_at": "2026-05-12T08:00:00Z",
  "current_location": {
    "user_id": 7,
    "session_id": "auto-42",
    "latitude": 12.9716,
    "longitude": 77.5946,
    "speed": 0,
    "heading": 90,
    "battery": 78,
    "timestamp": "2026-05-12T08:00:03Z"
  }
}
```

Recommended response:

```json
{
  "session_id": "auto-42",
  "tracking_url": "http://10.228.102.43:8000/track/auto-42",
  "status": "active"
}
```

### Tracking Update

`POST /tracking/update`

Mobile sends every few seconds:

```json
{
  "user_id": 7,
  "session_id": "auto-42",
  "latitude": 12.9716,
  "longitude": 77.5946,
  "speed": 1.4,
  "heading": 92,
  "accuracy": 8.5,
  "battery": 76,
  "timestamp": "2026-05-12T08:00:08Z"
}
```

### Emergency Status

`GET /emergency/status?session_id=<session_id>`

Expected active response:

```json
{ "session_id": "auto-42", "status": "active" }
```

Expected completion response:

```json
{ "session_id": "auto-42", "status": "resolved" }
```

## Android Permission Setup

Configured in `android/app/src/main/AndroidManifest.xml`:

- `ACCESS_FINE_LOCATION`
- `ACCESS_COARSE_LOCATION`
- `ACCESS_BACKGROUND_LOCATION`
- `FOREGROUND_SERVICE`
- `FOREGROUND_SERVICE_LOCATION`
- `POST_NOTIFICATIONS`
- `USE_FULL_SCREEN_INTENT`
- `SEND_SMS`
- `CALL_PHONE`
- `CAMERA`
- `RECORD_AUDIO`
- `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`
- `WAKE_LOCK`

For production, keep full-screen alerts for critical emergency use only and make cleartext HTTP debug-only.

## Startup Instructions

```bash
flutter pub get
flutter run --dart-define=SHEGUARD_API_BASE_URL=http://10.228.102.43:8000
```

For Android physical device testing:

```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8000
flutter run --dart-define=SHEGUARD_API_BASE_URL=http://10.228.102.43:8000
```

## Testing Instructions

1. Log in on a physical Android device.
2. Grant location, notification, SMS, phone, camera, microphone, and background location permissions.
3. Confirm normal manual SOS still works.
4. Send a websocket `emergency_incident` event for the logged-in `user_id`.
5. Verify:
   - `EmergencyModeScreen` opens automatically
   - full-screen/local emergency notification appears
   - foreground tracking notification stays active
   - `POST /emergency/start` is called
   - `POST /tracking/update` repeats with GPS, heading, speed, battery, timestamp
   - SMS body includes victim name, incident type, tracking URL, evidence links, and GPS
   - app queues tracking updates when backend is offline and syncs after reconnect
6. Return `{"status":"resolved"}` from `GET /emergency/status` and verify local Auto SOS mode ends.

## Notes

- The Flutter app does not modify AI models or backend detection logic.
- If `POST /emergency/start` fails, the app still starts local Auto SOS to avoid losing emergency response.
- If websocket disconnects, reconnect uses exponential backoff and local notification warns that realtime recovery is active.
