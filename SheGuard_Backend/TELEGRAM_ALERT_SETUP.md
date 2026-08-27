# Telegram Emergency Alerts

## What Happens

When `POST /incidents/create` or the legacy `POST /incident/create` receives an emergency incident:

1. The backend stores the incident.
2. Image/video evidence is copied into backend-owned upload folders.
3. The backend stores evidence rows and normalized evidence records.
4. `process_incident_alert()` sends Telegram automatically:
   - `sendMessage`
   - `sendLocation`
   - `sendPhoto`
   - `sendVideo`
5. The Telegram attempt is stored in `emergency_notifications` with channel `telegram`.

## Media Storage

Telegram media is sent from:

```text
uploads/
├── images/
│   └── incident_YYYYMMDD_HHMMSS.jpg
└── videos/
    └── incident_YYYYMMDD_HHMMSS.mp4
```

If the original AI media path is missing, the incident is still stored and the Telegram result includes a media error.

## Environment

Create or update `.env`:

```env
BOT_TOKEN=123456:telegram-bot-token
PARENT_CHAT_ID=123456789
```

Backward-compatible names are also supported:

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

## Create A Telegram Bot

1. Open Telegram and message `@BotFather`.
2. Send `/newbot`.
3. Choose a bot name and username.
4. Copy the bot token into `BOT_TOKEN`.
5. Send any message to your new bot.
6. Get your chat id from `https://api.telegram.org/bot<BOT_TOKEN>/getUpdates`.
7. Put the chat id into `PARENT_CHAT_ID`.

## Testing

Start backend:

```powershell
cd C:\Programs\codex\SheGuard\SheGuard_Backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Send a test incident:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/incidents/create `
  -ContentType 'application/json' `
  -Body '{"incident_type":"fall","confidence":0.95,"latitude":13.351388,"longitude":77.141865,"image_path":"C:\\path\\snapshot.jpg","video_path":"C:\\path\\clip.mp4","send_alert":true}'
```

The response includes a `telegram` object with per-step status and errors.

Multipart upload test:

```powershell
curl.exe -X POST http://localhost:8000/incidents/create `
  -F "incident_type=fall" `
  -F "confidence=0.95" `
  -F "latitude=13.351388" `
  -F "longitude=77.141865" `
  -F "image=@test.jpg" `
  -F "video=@test.mp4"
```
