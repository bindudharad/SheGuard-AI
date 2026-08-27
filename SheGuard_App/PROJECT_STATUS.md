# SheGuard Project Status

## Implemented

- SOS button and silent SOS
- Emergency SMS to saved contacts with live Google Maps link
- Live GPS tracking and location freshness
- FastAPI incident/location/contact integration
- Local notifications for SOS, silent emergency, emergency mode, GPS tracking, and tracking failures
- Contact add, local edit, local delete/hide, local favorite, and backend add/list sync
- Local emergency session IDs with timestamps and incident response metadata
- Duplicate SOS throttling
- Shake detection SOS with sensitivity setting
- Fall detection using impact plus stillness and a timed safety check
- Encrypted local emergency evidence storage for audio and front-camera still capture
- Dark SheGuard UI theme preserved

## Not Implemented In This Flutter Workspace

- Offline voice wake-word detection: production offline/background support requires a native wake-word engine/model bundle or a service such as Porcupine with an access key.
- Evidence upload: no backend upload endpoint exists in the documented API contract.
- Live public tracking web page: requires backend session/location history endpoint or websocket/polling endpoint.
- Admin dashboard: requires dashboard project and backend admin APIs.
- AI CCTV pipeline: requires backend Python/OpenCV/YOLO/MediaPipe services and camera ingestion infrastructure.
- API rate limiting/JWT enforcement: backend responsibility; the Flutter app already stores and sends returned tokens.

## Release Output

Release APK target:

`build/app/outputs/flutter-apk/app-release.apk`
