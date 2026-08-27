# Smart Emergency Response

## Architecture

```text
AI CCTV incident
-> POST /incident/create or /incidents/create
-> SmartIncidentResponseService
-> VictimMatchingEngine using Haversine distance
-> EmergencySessionManager creates SOS tracking session
-> NotificationManager creates parent/app/websocket/SMS/WhatsApp-ready notifications
-> EvidenceLinkingService stores snapshot/clip/metadata records
-> RealtimeHub publishes incident, session, notification, and tracking events
```

## Matching Logic

- Incident GPS is read from the payload first.
- If GPS is missing, the backend tries the CCTV camera record by `camera_id` or `camera_name`.
- Active users are users with recent `live_locations` rows.
- Distance is calculated with Haversine meters.
- The nearest active user within `SHEGUARD_INCIDENT_MATCH_RADIUS_METERS` is linked automatically.

Defaults:

- Radius: `75m`
- Active location age: `900s`
- Incident merge cooldown: `120s`
- Notification cooldown: `180s`

## APIs

- `POST /incidents/create`: create AI incident, match victim, activate SOS, notify contacts, link evidence.
- `GET /incidents/{id}`: incident, evidence, session, notifications.
- `POST /incidents/link-user`: manually link an incident to a user and activate SOS.
- `POST /emergency/start`: manually start an emergency session.
- `POST /notifications/send`: create app/websocket/SMS/WhatsApp/email-ready notification records.
- `GET /tracking/live/{session_id}`: existing live tracking state.
- `GET /evidence/{incident_id}`: legacy evidence plus normalized evidence records.
- `WS /ws/live`: global realtime stream.
- `WS /ws/tracking/{session_id}`: tracking stream.
- `WS /ws/emergency/{session_id}`: emergency monitoring stream.

## Integration

AI should keep sending incident payloads to:

```text
POST http://localhost:8000/incident/create
```

or the new canonical endpoint:

```text
POST http://localhost:8000/incidents/create
```

Include `latitude` and `longitude` whenever possible. If unavailable, configure cameras with GPS so `camera_id` can resolve incident coordinates.

## Testing

```powershell
cd C:\Programs\codex\SheGuard\SheGuard_Backend
python -m pytest tests -q
```

Manual smoke:

1. Register a user.
2. Add an emergency contact.
3. Send `/location/update` near the CCTV incident GPS.
4. Send `/incidents/create` with nearby GPS.
5. Confirm `linked_user`, `emergency_session`, `notifications`, and `evidence_records` in the response.
