# Parent Auto-Call Emergency Demo

## What The App Does

When `WS /live/emergency` sends an emergency event for the logged-in user:

1. `AutoSosManager` opens Auto SOS mode immediately.
2. The app shows the emergency popup/screen with:
   - `Emergency Active`
   - `SOS Triggered`
   - `Calling Parent...`
3. `NotificationService` triggers one emergency vibration for that event.
4. `SosService` calls the first saved emergency contact through `EmergencyCallService`.
5. `EmergencyCallService` marks the session as called so reconnects, duplicate websocket events, or rebuilds do not call again.

## Loop Prevention

- Parent calls are guarded by `sessionId`.
- Auto SOS websocket events are guarded by `eventId`.
- Emergency vibration is guarded by `eventId`.
- Auto SOS disables fallback call chaining so the hackathon demo does not start a call loop through every contact.

## Android Permission Setup

Already configured in `android/app/src/main/AndroidManifest.xml`:

- `android.permission.CALL_PHONE`
- `android.permission.FOREGROUND_SERVICE`
- `android.permission.FOREGROUND_SERVICE_LOCATION`
- `android.permission.VIBRATE`
- `android.permission.POST_NOTIFICATIONS`

## Test Steps

1. Add one emergency contact in the app.
2. Grant Phone, Notification, SMS, and Location permissions.
3. Log in and keep the app on Home.
4. Send a websocket event:

```json
{
  "type": "emergency_incident",
  "incident": {
    "event_id": "demo-parent-call-1",
    "incident_id": 101,
    "user_id": 7,
    "session_id": "demo-session-101",
    "incident_type": "ai_cctv_emergency",
    "created_at": "2026-05-13T10:00:00Z"
  }
}
```

5. Verify:
   - Phone vibrates once.
   - Emergency screen opens.
   - UI shows `Calling Parent...` then parent call status.
   - Dialer/direct call starts for the first emergency contact.
6. Send the same event again.
7. Verify no second call, no second vibration, and no repeated notification loop.
