# SheGuard Architecture

## Mobile App Layers

- `lib/screens`: Flutter UI and navigation.
- `lib/widgets`: reusable UI components for SOS, metrics, status, timelines, and empty states.
- `lib/providers`: app state for auth, contacts, incidents, location, safety, and settings.
- `lib/services`: platform, backend, and emergency orchestration services.
- `lib/models`: typed API and local data models.

## Emergency Flow

1. User presses SOS, long-presses SOS, triple taps the home header, shakes aggressively, or fails the fall safety check.
2. `HomeScreen` calls `SosService.activate`.
3. `SosService` creates a session ID, throttles duplicate triggers, starts encrypted evidence capture, gets GPS, sends SMS, calls `/incident/create`, starts tracking, and stores the local session record.
4. `LocationService` posts repeated `/location/update` payloads through the existing foreground geolocator stream.
5. `IncidentProvider`, `SafetyProvider`, and `LocationProvider` update UI state and notifications.

## Smart Protection Services

- `EmergencySmsService`: sends multipart emergency SMS to all visible saved contacts.
- `SosService`: orchestrates emergency sessions and duplicate protection.
- `MotionProtectionService`: detects shake SOS and fall candidates from device sensors.
- `EvidenceCaptureService`: captures audio/front-camera evidence and stores encrypted local artifacts.
- `NotificationService`: owns Android alert notifications.

## Backend Compatibility

The Flutter app keeps the current FastAPI contract intact:

- `POST /incident/create`
- `POST /location/update`
- `GET /location/live/{user_id}`
- `GET /incident/live`
- `GET /incident/history/{user_id}`
- `GET /evidence/{incident_id}`
- `POST /contacts/add`
- `GET /contacts/{user_id}`

Features such as evidence upload, live public tracking pages, admin dashboards,
and CCTV AI pipelines need matching backend endpoints or separate applications.
