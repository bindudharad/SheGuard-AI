# Realtime Reconnect Notification Lifecycle

## Reconnect Flow

`EmergencyRealtimeService` now treats a websocket outage as one lifecycle:

1. First disconnect/error transitions to `disconnected`.
2. One reconnect notification is shown and vibrates once.
3. Reconnect attempts continue silently with exponential backoff:
   - 2 seconds
   - 5 seconds
   - 10 seconds
   - 20 seconds
   - 40 seconds
   - 60 seconds for later attempts
4. Duplicate `onError`/`onDone` callbacks cannot schedule duplicate timers.
5. After repeated failures the state becomes `failed`, but retries still continue quietly.
6. On successful reconnect, the reconnect notification is cancelled and one quiet restored notification may be shown.

## Notification Debounce Logic

`NotificationService` tracks active notification IDs and last shown times.

- Reconnect notification ID: `30`
- Restored notification ID: `31`
- Reconnect notification cooldown: 5 minutes
- Reconnect notification uses `onlyAlertOnce`
- Reconnect notification vibrates only on the first outage alert
- Restored notification does not vibrate

This prevents the same reconnect notification from alerting repeatedly while the websocket is retrying in the background.

## Foreground Tracking Notification

The Android foreground GPS service now avoids updating its notification for every internal log line. It updates immediately for major state changes such as tracking started/stopped/backend missing, and throttles routine GPS/retry text updates.

## Testing Instructions

1. Start the app and log in.
2. Start the backend websocket server and confirm realtime state becomes connected.
3. Stop the backend or disable WiFi.
4. Verify only one "Realtime emergency link reconnecting" notification appears.
5. Leave the backend offline for at least 60 seconds.
6. Verify no repeated notification sounds or vibration occur during retries.
7. Restart the backend.
8. Verify the reconnect notification is removed and at most one quiet restored notification appears.
9. Trigger a real emergency event and verify full emergency alert vibration still works.
