# Simple Incident Feed Testing

## Backend

The Flutter app defaults to:

```text
http://10.228.102.43:8000
```

Override during a demo build if needed:

```powershell
flutter run --dart-define=SHEGUARD_API_BASE_URL=http://10.228.102.43:8000
```

## Expected Incident Endpoint

The app calls:

```http
GET /incidents
```

It accepts either a raw list:

```json
[
  {
    "id": 1,
    "incident_type": "violence",
    "confidence": 0.92,
    "timestamp": "2026-05-13T10:30:00Z",
    "image_url": "http://10.228.102.43:8000/media/frame.jpg",
    "video_url": "http://10.228.102.43:8000/media/clip.mp4"
  }
]
```

or wrapped data:

```json
{
  "incidents": []
}
```

Relative media paths such as `/media/frame.jpg` also work.

## Demo Flow

1. Start the backend on the same WiFi network.
2. Run the app:

```powershell
flutter run
```

3. Log in and add at least one emergency contact.
4. Open the `Alerts` tile to view the incident feed.
5. Create a new backend incident.
6. Confirm:
   - The new incident card appears.
   - The emergency popup says `Emergency Detected`.
   - The dialer opens for the first saved visible contact.
   - The incident details screen opens from the popup or card.

## Notes

- Websocket `/ws/live` is used when available.
- A 5 second polling fallback refreshes `GET /incidents` for reliable hackathon demos.
- Each incident is keyed once, so the app does not repeatedly pop dialogs or repeatedly call the same parent for the same incident.
