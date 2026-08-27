# SheGuard App

Professional Flutter client for the existing `SheGuard_AI` backend.

The app now includes the Phase 1 emergency flow plus production mobile Phase 2
protection features that can run inside this Flutter project without changing
backend API contracts.

## Implemented Screens

- Splash with animated shield, backend check, session restore, and permission check
- Login and registration with validation and secure session persistence
- Home safety command center with backend, GPS, AI monitoring, location freshness, and central SOS
- Emergency contacts with backend add/list and local edit/remove/favorite metadata
- Live status with backend health, GPS freshness, retry count, and live incident feed
- Incident timeline with threat score, confidence, and lazy evidence loading
- Settings for silent mode, notifications, GPS, privacy guard, backend status, and logout
- Motion protection settings for shake SOS, fall detection, and sensitivity

## Emergency Protection Features

- SOS button sends SMS alerts to saved contacts with a Google Maps location link.
- Silent SOS works through long press, triple tap, aggressive shake, and fall escalation.
- Live GPS tracking runs with an Android foreground location notification.
- Emergency sessions are assigned local session IDs and persisted with timestamps.
- Encrypted local evidence capture starts during SOS:
  - microphone audio is recorded and stored as AES-256-GCM encrypted evidence
  - front-camera still capture is attempted when camera permission/device state allows it
- Possible falls are detected from accelerometer impact plus post-impact stillness. The user gets a timed “Are you safe?” check before silent SOS activates.

## Backend APIs

Connected to the existing `SheGuard_AI` API contract:

- `POST /register`
- `POST /login`
- `GET /profile/{user_id}`
- `POST /contacts/add`
- `GET /contacts/{user_id}`
- `POST /location/update`
- `GET /location/live/{user_id}`
- `POST /incident/create`
- `GET /incident/history/{user_id}`
- `GET /incident/live`
- `GET /evidence/{incident_id}`

Backend health uses `GET /incident/live?limit=1` because no dedicated health
endpoint exists.

## Configure Backend

Set the API base URL in `lib/core/app_config.dart`, or pass it at runtime:

```bash
flutter run
```

For real Android phone testing, the app is configured to use:

`http://10.228.102.43:8000`

Keep the phone and laptop on the same WiFi network and run the backend with:

```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

## Run

```bash
flutter pub get
flutter test
flutter run
```

## Build Release APK

```bash
flutter analyze
flutter build apk --release
```

## Notes

- Contact edit/remove/favorite are local metadata until backend update/delete
  endpoints are added.
- Silent SOS is triggered by long press on the SOS button or triple tap on the
  home header when silent mode is enabled.
- Offline wake-word detection, public live tracking pages, admin dashboards,
  CCTV AI pipelines, and backend evidence upload require backend/native/model
  surfaces that are outside this Flutter-only workspace. The app does not fake
  those APIs.
