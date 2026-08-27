import html
import io
import json
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import LocationUpdate, TrackingStart, TrackingUpdate
from app.database import get_db
from app.models import EmergencySession, LiveLocation, TrackingSession, User
from app.services.auth import get_current_user
from app.services.realtime import realtime_hub


router = APIRouter(tags=["locations"])


def location_out(row: LiveLocation) -> dict:
    return {
        "location_id": row.location_id,
        "user_id": row.user_id,
        "session_id": row.session_id,
        "latitude": row.latitude,
        "longitude": row.longitude,
        "speed": row.speed,
        "battery": row.battery,
        "accuracy": row.accuracy,
        "timestamp": row.timestamp,
    }


def session_out(row: TrackingSession) -> dict:
    return {
        "session_id": row.session_id,
        "user_id": row.user_id,
        "status": row.status,
        "started_at": row.started_at,
        "ended_at": row.ended_at,
        "latitude": row.last_latitude,
        "longitude": row.last_longitude,
        "speed": row.last_speed,
        "battery": row.last_battery,
        "accuracy": row.last_accuracy,
        "last_update_at": row.last_update_at,
        "tracking_url": f"/track/{row.session_id}",
    }


def tracking_live_payload(session: TrackingSession | None, row: LiveLocation | None) -> dict:
    latitude = row.latitude if row else (session.last_latitude if session else None)
    longitude = row.longitude if row else (session.last_longitude if session else None)
    speed = row.speed if row else (session.last_speed if session else None)
    battery = row.battery if row else (session.last_battery if session else None)
    updated_at = row.timestamp if row else (session.last_update_at if session else None)
    emergency_status = session.status if session else "unknown"
    return {
        "session_id": session.session_id if session else (row.session_id if row else None),
        "latitude": latitude,
        "longitude": longitude,
        "speed": speed,
        "battery": battery,
        "updated_at": updated_at,
        "emergency_status": emergency_status,
        "status": emergency_status,
        "accuracy": row.accuracy if row else (session.last_accuracy if session else None),
    }


def tracking_point_out(row: LiveLocation) -> dict:
    return {
        "location_id": row.location_id,
        "latitude": row.latitude,
        "longitude": row.longitude,
        "speed": row.speed,
        "battery": row.battery,
        "accuracy": row.accuracy,
        "updated_at": row.timestamp,
        "timestamp": row.timestamp,
    }


def tracking_state_out(session_id: str, session: TrackingSession | None, rows: list[LiveLocation]) -> dict:
    latest_row = rows[-1] if rows else None
    latest = tracking_point_out(latest_row) if latest_row else None
    active = bool((session and session.status == "active") or latest_row)
    return {
        "session_id": session_id,
        "active": active,
        "emergency_status": session.status if session else ("active" if latest_row else "waiting"),
        "latest": latest,
        "path": [tracking_point_out(row) for row in rows],
    }


def _upsert_tracking_location(
    db: Session,
    *,
    session_id: str,
    user_id: int,
    latitude: float,
    longitude: float,
    speed: float | None = 0,
    battery: int | None = None,
    accuracy: float | None = None,
    timestamp: datetime | None = None,
) -> LiveLocation:
    if not db.get(User, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    now = timestamp or datetime.utcnow()
    session = db.get(TrackingSession, session_id)
    if not session:
        session = TrackingSession(session_id=session_id, user_id=user_id, started_at=now)
        db.add(session)
    session.status = "active"
    session.last_latitude = latitude
    session.last_longitude = longitude
    session.last_speed = speed
    session.last_battery = battery
    session.last_accuracy = accuracy
    session.last_update_at = now
    row = LiveLocation(
        user_id=user_id,
        session_id=session_id,
        latitude=latitude,
        longitude=longitude,
        speed=speed,
        battery=battery,
        accuracy=accuracy,
        timestamp=now,
    )
    emergency = db.get(EmergencySession, session_id)
    if emergency:
        emergency.status = "active"
        emergency.last_latitude = latitude
        emergency.last_longitude = longitude
        emergency.last_update_at = now
    db.add(row)
    db.commit()
    db.refresh(row)
    payload = {"session": session_out(session), "location": location_out(row)}
    realtime_hub.publish_from_sync("tracking_update", payload)
    realtime_hub.publish_session_from_sync(session_id, "tracking_update", payload)
    return row


@router.post("/location/update")
def update_location(payload: LocationUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        if payload.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Cannot update another user's location")
        if not db.get(User, payload.user_id):
            raise HTTPException(status_code=404, detail="User not found")
        if payload.session_id:
            row = _upsert_tracking_location(
                db,
                session_id=payload.session_id,
                user_id=payload.user_id,
                latitude=payload.latitude,
                longitude=payload.longitude,
                speed=payload.speed,
                battery=payload.battery,
                accuracy=payload.accuracy,
                timestamp=payload.timestamp,
            )
        else:
            row = LiveLocation(
                user_id=payload.user_id,
                session_id=payload.session_id,
                latitude=payload.latitude,
                longitude=payload.longitude,
                speed=payload.speed,
                battery=payload.battery,
                accuracy=payload.accuracy,
                timestamp=payload.timestamp or datetime.utcnow(),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
        return {"status": "updated", "location_id": row.location_id, "timestamp": row.timestamp}
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Location update failed: {exc}") from exc


@router.get("/location/live/{user_id}")
def live_location(user_id: int, db: Session = Depends(get_db)):
    row = db.scalars(select(LiveLocation).where(LiveLocation.user_id == user_id).order_by(LiveLocation.timestamp.desc())).first()
    if not row:
        raise HTTPException(status_code=404, detail="No location found")
    return location_out(row)


@router.post("/tracking/start")
async def start_tracking(payload: TrackingStart, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if payload.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Cannot start tracking for another user")
    if not db.get(User, payload.user_id):
        raise HTTPException(status_code=404, detail="User not found")
    now = payload.timestamp or datetime.utcnow()
    session_id = payload.session_id or f"sos-{uuid4().hex[:16]}"
    session = db.get(TrackingSession, session_id)
    if not session:
        session = TrackingSession(session_id=session_id, user_id=payload.user_id, started_at=now)
        db.add(session)
    session.status = "active"
    session.last_latitude = payload.latitude
    session.last_longitude = payload.longitude
    session.last_speed = payload.speed
    session.last_battery = payload.battery
    session.last_accuracy = payload.accuracy
    session.last_update_at = now if payload.latitude is not None else None
    db.commit()
    db.refresh(session)
    return session_out(session)


@router.post("/tracking/update")
async def update_tracking(payload: TrackingUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        if payload.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Cannot update another user's tracking")
        row = _upsert_tracking_location(
            db,
            session_id=payload.session_id,
            user_id=payload.user_id,
            latitude=payload.latitude,
            longitude=payload.longitude,
            speed=payload.speed,
            battery=payload.battery,
            accuracy=payload.accuracy,
            timestamp=payload.timestamp,
        )
        return {"status": "updated", "session_id": payload.session_id, "location": location_out(row)}
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Tracking update failed: {exc}") from exc


@router.get("/tracking/live/{session_id}")
def tracking_live(session_id: str, db: Session = Depends(get_db)):
    try:
        session = db.get(TrackingSession, session_id)
        rows = db.scalars(
            select(LiveLocation)
            .where(LiveLocation.session_id == session_id)
            .order_by(LiveLocation.timestamp.asc())
        ).all()
        if not session and not rows:
            raise HTTPException(status_code=404, detail="Tracking session not found")
        return tracking_state_out(session_id, session, rows)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not load live tracking session: {exc}") from exc


@router.get("/tracking/history/{session_id}")
def tracking_history(session_id: str, db: Session = Depends(get_db)):
    try:
        session = db.get(TrackingSession, session_id)
        rows = db.scalars(
            select(LiveLocation)
            .where(LiveLocation.session_id == session_id)
            .order_by(LiveLocation.timestamp.asc())
        ).all()
        if not session and not rows:
            raise HTTPException(status_code=404, detail="Tracking session not found")
        return {
            "session": session_out(session) if session else {"session_id": session_id, "status": "active"},
            "locations": [location_out(row) for row in rows],
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not load tracking history: {exc}") from exc


@router.get("/location/stream/{session_id}")
def location_stream(session_id: str, db: Session = Depends(get_db)):
    return tracking_history(session_id, db)


@router.websocket("/ws/tracking/{session_id}")
async def tracking_socket(websocket: WebSocket, session_id: str):
    await realtime_hub.connect(websocket, session_id=session_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await realtime_hub.disconnect(websocket)


@router.get("/track/{session_id}/qr")
def tracking_qr(session_id: str, request: Request):
    try:
        import qrcode
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="QR support requires qrcode[pil]. Install requirements.txt.",
        ) from exc

    url = str(request.url_for("tracking_page", session_id=session_id))
    image = qrcode.make(url)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png")


@router.get("/track/{session_id}", response_class=HTMLResponse)
def tracking_page(session_id: str):
    session_id_json = json.dumps(session_id)
    session_id_html = html.escape(session_id)
    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>SheGuard SOS Navigation</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.css" />
  <style>
    :root {{
      color-scheme: dark;
      --danger: #ef4444;
      --danger-strong: #dc2626;
      --blue: #2f80ff;
      --glass: rgba(10, 15, 27, .76);
      --glass-border: rgba(255, 255, 255, .16);
      --text: #f8fafc;
      --muted: rgba(248, 250, 252, .72);
    }}
    html, body, #map {{
      height: 100%;
      width: 100%;
      margin: 0;
      background: #050814;
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      overflow: hidden;
    }}
    #map {{ z-index: 1; }}
    .leaflet-control-container .leaflet-routing-container {{ display: none; }}
    .leaflet-control-zoom {{
      border: 0 !important;
      box-shadow: 0 14px 36px rgba(0,0,0,.38) !important;
    }}
    .shell {{
      position: fixed;
      z-index: 1000;
      left: max(14px, env(safe-area-inset-left));
      right: max(14px, env(safe-area-inset-right));
      top: max(14px, env(safe-area-inset-top));
      display: flex;
      align-items: flex-start;
      gap: 12px;
      pointer-events: none;
    }}
    .panel {{
      width: min(880px, 100%);
      padding: 14px;
      border: 1px solid var(--glass-border);
      border-radius: 8px;
      background: linear-gradient(135deg, rgba(127, 29, 29, .80), var(--glass) 46%, rgba(8, 13, 28, .84));
      box-shadow: 0 22px 70px rgba(0,0,0,.42), inset 0 1px 0 rgba(255,255,255,.08);
      backdrop-filter: blur(18px) saturate(145%);
      pointer-events: auto;
    }}
    .topline {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 10px;
    }}
    .title {{
      display: flex;
      align-items: center;
      gap: 10px;
      color: #fff;
      font-size: 14px;
      font-weight: 900;
      letter-spacing: .08em;
      text-transform: uppercase;
      white-space: nowrap;
    }}
    .pulse {{
      width: 12px;
      height: 12px;
      border-radius: 999px;
      background: var(--danger);
      box-shadow: 0 0 0 8px rgba(239, 68, 68, .18), 0 0 26px rgba(239, 68, 68, .9);
    }}
    .session {{
      color: var(--muted);
      font-size: 12px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 8px;
    }}
    .metric {{
      min-width: 0;
      padding: 10px;
      border: 1px solid rgba(255,255,255,.10);
      border-radius: 8px;
      background: rgba(255,255,255,.08);
      box-shadow: inset 0 1px 0 rgba(255,255,255,.06);
    }}
    .metric span {{
      display: block;
      color: var(--muted);
      font-size: 11px;
      line-height: 1.2;
    }}
    .metric b {{
      display: block;
      margin-top: 4px;
      color: #fff;
      font-size: clamp(13px, 1.7vw, 17px);
      line-height: 1.2;
      overflow-wrap: anywhere;
    }}
    .hint {{
      margin-top: 10px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
    }}
    .floating {{
      position: fixed;
      z-index: 1000;
      right: max(14px, env(safe-area-inset-right));
      bottom: max(14px, env(safe-area-inset-bottom));
      display: grid;
      gap: 10px;
      pointer-events: none;
    }}
    .status-card, .qr {{
      pointer-events: auto;
      border-radius: 8px;
      border: 1px solid var(--glass-border);
      background: rgba(7, 12, 24, .78);
      backdrop-filter: blur(16px) saturate(140%);
      box-shadow: 0 16px 44px rgba(0,0,0,.40);
    }}
    .status-card {{
      width: 210px;
      padding: 12px;
      font-size: 12px;
      color: var(--muted);
    }}
    .status-card b {{
      display: block;
      color: #fff;
      font-size: 14px;
      margin-top: 3px;
    }}
    .qr {{
      width: 82px;
      padding: 8px;
      justify-self: end;
      background: rgba(255,255,255,.94);
    }}
    .qr img {{ display: block; width: 100%; height: auto; border-radius: 4px; }}
    .marker {{
      position: relative;
      display: grid;
      place-items: center;
      width: 34px;
      height: 34px;
      border-radius: 999px;
      border: 3px solid #fff;
      color: #fff;
      font-weight: 900;
      font-size: 16px;
      box-shadow: 0 14px 28px rgba(0,0,0,.36);
    }}
    .marker.parent {{ background: var(--blue); }}
    .marker.victim {{
      background: var(--danger-strong);
      box-shadow: 0 0 0 12px rgba(239, 68, 68, .22), 0 14px 30px rgba(0,0,0,.40), 0 0 34px rgba(239,68,68,.9);
    }}
    .marker.victim::after {{
      content: "";
      position: absolute;
      inset: -13px;
      border: 2px solid rgba(239, 68, 68, .55);
      border-radius: 999px;
      animation: sonar 1.6s ease-out infinite;
    }}
    @keyframes sonar {{
      from {{ transform: scale(.72); opacity: .9; }}
      to {{ transform: scale(1.34); opacity: 0; }}
    }}
    @media (max-width: 840px) {{
      .shell {{
        left: 10px;
        right: 10px;
        top: 10px;
      }}
      .panel {{ padding: 12px; }}
      .topline {{ align-items: flex-start; }}
      .title {{ font-size: 12px; white-space: normal; }}
      .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .floating {{
        left: 10px;
        right: 10px;
        bottom: 10px;
        grid-template-columns: 1fr auto;
        align-items: end;
      }}
      .status-card {{ width: auto; }}
      .qr {{ width: 64px; }}
      .leaflet-control-zoom {{ display: none; }}
    }}
    @media (max-width: 420px) {{
      .grid {{ gap: 6px; }}
      .metric {{ padding: 8px; }}
      .metric b {{ font-size: 13px; }}
      .status-card {{ font-size: 11px; }}
    }}
    .tracking-widget {{
      position: fixed;
      z-index: 1000;
      left: max(14px, env(safe-area-inset-left));
      top: max(14px, env(safe-area-inset-top));
      width: min(430px, calc(100vw - 28px));
      border: 1px solid var(--glass-border);
      border-radius: 16px;
      background: linear-gradient(135deg, rgba(127, 29, 29, .82), rgba(8, 13, 28, .82) 48%, rgba(3, 7, 18, .88));
      box-shadow: 0 22px 70px rgba(0,0,0,.42), inset 0 1px 0 rgba(255,255,255,.08);
      backdrop-filter: blur(20px) saturate(150%);
      overflow: hidden;
      touch-action: none;
      transition: width .22s ease, transform .22s ease, box-shadow .22s ease;
    }}
    .tracking-widget.collapsed {{
      width: min(268px, calc(100vw - 28px));
      cursor: pointer;
    }}
    .widget-mini {{
      display: none;
      width: 100%;
      align-items: center;
      gap: 10px;
      border: 0;
      padding: 10px 12px;
      color: #fff;
      background: transparent;
      text-align: left;
      font: inherit;
      touch-action: manipulation;
    }}
    .tracking-widget.collapsed .widget-mini {{ display: flex; }}
    .sos-disc {{
      display: grid;
      place-items: center;
      width: 42px;
      height: 42px;
      border-radius: 999px;
      background: var(--danger-strong);
      color: #fff;
      font-weight: 900;
      box-shadow: 0 0 0 8px rgba(239, 68, 68, .18), 0 0 28px rgba(239, 68, 68, .70);
      flex: 0 0 auto;
    }}
    .mini-copy {{ min-width: 0; flex: 1; }}
    .mini-copy strong {{
      display: block;
      font-size: 13px;
      letter-spacing: .04em;
      text-transform: uppercase;
    }}
    .mini-copy span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .mini-badge {{
      padding: 6px 8px;
      border-radius: 999px;
      background: rgba(47,128,255,.18);
      color: #dbeafe;
      font-size: 12px;
      font-weight: 800;
      white-space: nowrap;
    }}
    .tracking-widget.collapsed .panel {{ display: none; }}
    .tracking-widget .panel {{
      width: auto;
      border: 0;
      border-radius: 0;
      background: transparent;
      box-shadow: none;
      backdrop-filter: none;
    }}
    .panel-actions {{
      display: flex;
      align-items: center;
      gap: 8px;
      flex: 0 0 auto;
    }}
    .icon-button {{
      display: grid;
      place-items: center;
      min-width: 42px;
      height: 42px;
      border: 1px solid rgba(255,255,255,.14);
      border-radius: 12px;
      color: #fff;
      background: rgba(255,255,255,.09);
      font-size: 18px;
      font-weight: 900;
      cursor: pointer;
      touch-action: manipulation;
    }}
    .icon-button:active {{ transform: scale(.98); }}
    .fab-stack {{
      position: fixed;
      z-index: 1000;
      right: max(14px, env(safe-area-inset-right));
      top: max(92px, calc(env(safe-area-inset-top) + 92px));
      display: grid;
      gap: 10px;
    }}
    .fab {{
      min-width: 48px;
      height: 48px;
      border: 1px solid var(--glass-border);
      border-radius: 14px;
      color: #fff;
      background: rgba(7, 12, 24, .82);
      backdrop-filter: blur(16px) saturate(140%);
      box-shadow: 0 16px 44px rgba(0,0,0,.34);
      font-size: 19px;
      font-weight: 900;
      cursor: pointer;
      touch-action: manipulation;
    }}
    .fab.active {{
      background: rgba(47,128,255,.88);
      border-color: rgba(191, 219, 254, .58);
    }}
    .fab span {{
      position: absolute;
      width: 1px;
      height: 1px;
      clip: rect(0 0 0 0);
      overflow: hidden;
    }}
    @media (max-width: 840px) {{
      .tracking-widget {{
        left: 10px;
        top: 10px;
        width: min(390px, calc(100vw - 20px));
        border-radius: 14px;
      }}
      .tracking-widget.collapsed {{ width: min(260px, calc(100vw - 92px)); }}
      .fab-stack {{
        right: 10px;
        top: auto;
        bottom: max(92px, calc(env(safe-area-inset-bottom) + 92px));
      }}
      .floating {{
        left: 10px;
        right: 10px;
        bottom: 10px;
      }}
    }}
  </style>
</head>
<body>
  <div class="tracking-widget collapsed" id="trackingWidget" aria-live="polite">
    <button class="widget-mini" id="widgetMini" type="button" aria-label="Expand SOS live tracking panel">
      <span class="sos-disc">SOS</span>
      <span class="mini-copy">
        <strong id="miniStatus">Connecting</strong>
        <span id="miniMeta">ETA -- / --</span>
      </span>
      <span class="mini-badge" id="miniBadge">Live</span>
    </button>
  <div class="panel" id="trackingPanel">
    <div class="topline">
      <div class="title"><span class="pulse"></span>SOS Live Navigation</div>
      <div class="panel-actions">
        <div class="session">Session: <span id="session">{session_id_html}</span></div>
        <button class="icon-button" id="collapsePanel" type="button" aria-label="Collapse tracking panel">-</button>
      </div>
    </div>
    <div class="grid">
      <div class="metric"><span>Status</span><b id="status">Connecting</b></div>
      <div class="metric"><span>ETA</span><b id="eta">--</b></div>
      <div class="metric"><span>Distance</span><b id="distance">--</b></div>
      <div class="metric"><span>Victim Speed</span><b id="speed">--</b></div>
      <div class="metric"><span>Battery</span><b id="battery">--</b></div>
      <div class="metric"><span>Last Updated</span><b id="last">--</b></div>
    </div>
    <div class="hint" id="hint">Waiting for live GPS updates from the phone...</div>
  </div>
  </div>
  <div class="fab-stack" aria-label="Map controls">
    <button class="fab" id="recenterBtn" type="button" title="Recenter map">C<span>Recenter map</span></button>
    <button class="fab" id="followBtn" type="button" title="Toggle follow mode">F<span>Toggle follow mode</span></button>
    <button class="fab" id="expandBtn" type="button" title="Expand tracking panel">i<span>Expand tracking panel</span></button>
  </div>
  <div class="floating">
    <div class="status-card">
      Parent location
      <b id="parentStatus">Requesting GPS permission</b>
    </div>
    <div class="qr"><img src="/track/{session_id_html}/qr" alt="Open live tracking QR code" /></div>
  </div>
  <div id="map"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.js"></script>
  <script>
    const sessionId = {session_id_json};
    const ROUTE_REFRESH_MS = 5000;
    const map = L.map('map', {{ zoomControl: true }}).setView([20.5937, 78.9629], 5);
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }}).addTo(map);

    const statusEl = document.getElementById('status');
    const etaEl = document.getElementById('eta');
    const distanceEl = document.getElementById('distance');
    const speedEl = document.getElementById('speed');
    const batteryEl = document.getElementById('battery');
    const lastEl = document.getElementById('last');
    const hintEl = document.getElementById('hint');
    const parentStatusEl = document.getElementById('parentStatus');
    const trackingWidget = document.getElementById('trackingWidget');
    const widgetMini = document.getElementById('widgetMini');
    const collapsePanel = document.getElementById('collapsePanel');
    const expandBtn = document.getElementById('expandBtn');
    const recenterBtn = document.getElementById('recenterBtn');
    const followBtn = document.getElementById('followBtn');
    const miniStatusEl = document.getElementById('miniStatus');
    const miniMetaEl = document.getElementById('miniMeta');
    const miniBadgeEl = document.getElementById('miniBadge');

    let parentMarker = null;
    let victimMarker = null;
    let parentLatLng = null;
    let victimLatLng = null;
    let lastLocationKey = null;
    let victimAnimFrame = null;
    let routingControl = null;
    let routeRefreshTimer = null;
    let lastRouteAt = 0;
    let routeInFlight = false;
    let lastFitAt = 0;
    let hasInitialCentered = false;
    let followMode = false;
    let userMovedMap = false;
    let widgetDrag = null;
    let suppressViewportEvents = false;

    const parentIcon = L.divIcon({{
      className: '',
      html: '<div class="marker parent" title="Parent location">P</div>',
      iconSize: [40, 40],
      iconAnchor: [20, 20]
    }});

    const victimIcon = L.divIcon({{
      className: '',
      html: '<div class="marker victim" title="Victim emergency location">!</div>',
      iconSize: [40, 40],
      iconAnchor: [20, 20]
    }});

    function formatDistance(meters) {{
      if (!Number.isFinite(meters)) return '--';
      if (meters >= 1000) return `${{(meters / 1000).toFixed(1)}} km`;
      return `${{Math.round(meters)}} m`;
    }}

    function formatEta(seconds) {{
      if (!Number.isFinite(seconds)) return '--';
      const minutes = Math.max(1, Math.round(seconds / 60));
      if (minutes >= 60) return `${{Math.floor(minutes / 60)}}h ${{minutes % 60}}m`;
      return `${{minutes}} min`;
    }}

    function setHint(message) {{
      hintEl.textContent = message;
    }}

    function setPanelExpanded(expanded) {{
      trackingWidget.classList.toggle('collapsed', !expanded);
      expandBtn.title = expanded ? 'Collapse tracking panel' : 'Expand tracking panel';
      expandBtn.querySelector('span').textContent = expanded ? 'Collapse tracking panel' : 'Expand tracking panel';
    }}

    function updateMiniPanel() {{
      miniStatusEl.textContent = statusEl.textContent || 'Live tracking';
      miniMetaEl.textContent = `ETA ${{etaEl.textContent || '--'}} / ${{distanceEl.textContent || '--'}}`;
      miniBadgeEl.textContent = followMode ? 'Follow' : 'Live';
    }}

    function setFollowMode(enabled) {{
      followMode = Boolean(enabled);
      followBtn.classList.toggle('active', followMode);
      followBtn.setAttribute('aria-pressed', String(followMode));
      updateMiniPanel();
      if (followMode) {{
        userMovedMap = false;
        recenterMap(true);
        setHint('Follow mode is on. The map will follow the victim marker until you pan or zoom manually.');
      }} else {{
        setHint('Follow mode is off. The map viewport will stay where you leave it.');
      }}
    }}

    function recenterMap(includeParent = true) {{
      suppressViewportEvents = true;
      setTimeout(() => {{ suppressViewportEvents = false; }}, 1200);
      if (includeParent && parentLatLng && victimLatLng) {{
        const bounds = L.latLngBounds([parentLatLng, victimLatLng]).pad(.22);
        map.fitBounds(bounds, {{
          animate: true,
          duration: .8,
          maxZoom: 17,
          paddingTopLeft: [18, trackingWidget.classList.contains('collapsed') ? 82 : 190],
          paddingBottomRight: [82, 110]
        }});
        return;
      }}
      if (victimLatLng) {{
        map.panTo(victimLatLng, {{ animate: true, duration: .8 }});
      }}
    }}

    function maybeAutoCenter() {{
      // Preserve the user's viewport after the first load. Later GPS updates only move markers.
      if (!hasInitialCentered && victimLatLng) {{
        hasInitialCentered = true;
        recenterMap(true);
        return;
      }}
      if (followMode && victimLatLng && !userMovedMap) {{
        suppressViewportEvents = true;
        setTimeout(() => {{ suppressViewportEvents = false; }}, 900);
        map.panTo(victimLatLng, {{ animate: true, duration: .6 }});
      }}
    }}

    function setParentLocation(latLng, accuracy) {{
      parentLatLng = L.latLng(latLng[0], latLng[1]);
      if (!parentMarker) {{
        parentMarker = L.marker(parentLatLng, {{ icon: parentIcon, zIndexOffset: 800 }}).addTo(map);
      }} else {{
        parentMarker.setLatLng(parentLatLng);
      }}
      parentStatusEl.textContent = accuracy ? `GPS ready, +/-${{Math.round(accuracy)}}m` : 'GPS ready';
      scheduleRouteRefresh(true);
      maybeAutoCenter();
    }}

    function animateVictimMarker(toLatLng) {{
      victimLatLng = L.latLng(toLatLng[0], toLatLng[1]);
      if (!victimMarker) {{
        victimMarker = L.marker(victimLatLng, {{ icon: victimIcon, zIndexOffset: 900 }}).addTo(map);
        maybeAutoCenter();
        return;
      }}

      const from = victimMarker.getLatLng();
      const start = performance.now();
      const duration = 900;
      if (victimAnimFrame) cancelAnimationFrame(victimAnimFrame);
      function step(now) {{
        const t = Math.min(1, (now - start) / duration);
        const eased = t < .5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
        const lat = from.lat + (victimLatLng.lat - from.lat) * eased;
        const lng = from.lng + (victimLatLng.lng - from.lng) * eased;
        victimMarker.setLatLng([lat, lng]);
        if (t < 1) {{
          victimAnimFrame = requestAnimationFrame(step);
        }} else {{
          maybeAutoCenter();
        }}
      }}
      victimAnimFrame = requestAnimationFrame(step);
    }}

    function asLocation(payload) {{
      if (!payload || payload.latitude == null || payload.longitude == null) return null;
      return {{
        location_id: payload.location_id,
        latitude: Number(payload.latitude),
        longitude: Number(payload.longitude),
        speed: payload.speed,
        battery: payload.battery,
        accuracy: payload.accuracy,
        timestamp: payload.timestamp || payload.updated_at,
        emergency_status: payload.emergency_status || payload.status
      }};
    }}

    function applyLocation(loc, session) {{
      if (!loc) return;
      const key = loc.location_id || loc.timestamp || `${{loc.latitude}},${{loc.longitude}}`;
      if (key === lastLocationKey) return;
      lastLocationKey = key;
      const latLng = [loc.latitude, loc.longitude];
      animateVictimMarker(latLng);
      statusEl.textContent = loc.emergency_status || session?.status || 'active';
      speedEl.textContent = `${{Number(loc.speed || 0).toFixed(1)}} m/s`;
      batteryEl.textContent = loc.battery == null ? '--' : `${{loc.battery}}%`;
      lastEl.textContent = loc.timestamp ? new Date(loc.timestamp).toLocaleTimeString() : '--';
      setHint(`Victim GPS received at ${{lastEl.textContent}}. Recalculating shortest route when parent GPS is available.`);
      updateMiniPanel();
      scheduleRouteRefresh(false);
    }}

    function applyState(data) {{
      const points = Array.isArray(data.path) ? data.path : [];
      const latest = asLocation(data.latest || points[points.length - 1]);
      if (latest) {{
        latest.emergency_status = data.emergency_status || (data.active ? 'active' : 'inactive');
        lastLocationKey = null;
        applyLocation(latest, {{ status: latest.emergency_status }});
      }} else {{
        statusEl.textContent = data.active ? 'Waiting' : 'Inactive';
        hintEl.textContent = 'No GPS point has reached the backend for this SOS session yet.';
      }}
    }}

    function setupRoutingControl() {{
      if (routingControl) return routingControl;

      routingControl = L.Routing.control({{
        waypoints: [],
        addWaypoints: false,
        draggableWaypoints: false,
        fitSelectedRoutes: false,
        routeWhileDragging: false,
        show: false,
        collapsible: true,
        createMarker: () => null,
        router: L.Routing.osrmv1({{
          serviceUrl: 'https://router.project-osrm.org/route/v1',
          profile: 'driving'
        }}),
        lineOptions: {{
          extendToWaypoints: true,
          missingRouteTolerance: 10,
          styles: [
            {{ color: '#061226', opacity: .55, weight: 9 }},
            {{ color: '#2f80ff', opacity: .95, weight: 6 }}
          ]
        }}
      }}).addTo(map);

      routingControl.on('routesfound', (event) => {{
        routeInFlight = false;
        const route = event.routes && event.routes[0];
        if (!route) return;
        distanceEl.textContent = formatDistance(route.summary.totalDistance);
        etaEl.textContent = formatEta(route.summary.totalTime);
        statusEl.textContent = 'Route live';
        setHint('Shortest road route is live and refreshes every 5 seconds.');
        updateMiniPanel();
        maybeAutoCenter();
      }});

      routingControl.on('routingerror', () => {{
        routeInFlight = false;
        statusEl.textContent = 'Routing issue';
        setHint('Could not calculate the OSRM route right now. Live victim tracking is still active.');
      }});

      return routingControl;
    }}

    function refreshRoute(force = false) {{
      if (!parentLatLng || !victimLatLng) return;
      const now = Date.now();
      if (!force && (routeInFlight || now - lastRouteAt < ROUTE_REFRESH_MS - 250)) return;
      lastRouteAt = now;
      routeInFlight = true;

      // Leaflet Routing Machine asks OSRM for the current shortest road path.
      // Waypoint 1 is the parent browser GPS position; waypoint 2 is the victim's latest backend GPS point.
      setupRoutingControl().setWaypoints([parentLatLng, victimLatLng]);
    }}

    function scheduleRouteRefresh(force = false) {{
      if (force) {{
        refreshRoute(true);
        return;
      }}
      if (!routeRefreshTimer) {{
        routeRefreshTimer = setInterval(() => refreshRoute(false), ROUTE_REFRESH_MS);
      }}
      refreshRoute(false);
    }}

    function fitBothMarkers() {{
      // Viewport changes are reserved for initial load, follow mode, and explicit recenter actions.
      recenterMap(true);
    }}

    function startParentGeolocation() {{
      if (!navigator.geolocation) {{
        parentStatusEl.textContent = 'Browser GPS unavailable';
        setHint('Parent browser geolocation is unavailable. Victim live tracking still works.');
        return;
      }}
      navigator.geolocation.watchPosition(
        (position) => {{
          setParentLocation(
            [position.coords.latitude, position.coords.longitude],
            position.coords.accuracy
          );
        }},
        (error) => {{
          parentStatusEl.textContent = 'GPS permission needed';
          setHint(`Enable location permission for navigation routing. Browser said: ${{error.message}}`);
        }},
        {{
          enableHighAccuracy: true,
          maximumAge: 4000,
          timeout: 12000
        }}
      );
    }}

    async function loadHistory() {{
      try {{
        const res = await fetch(`/tracking/history/${{sessionId}}`, {{ cache: 'no-store' }});
        if (!res.ok) return;
        const data = await res.json();
        const locations = data.locations || [];
        const latest = asLocation(locations[locations.length - 1]);
        if (latest) applyLocation(latest, data.session);
      }} catch (err) {{
        setHint('Unable to load route history yet. Retrying...');
      }}
    }}

    async function pollLatest() {{
      try {{
        const res = await fetch(`/tracking/live/${{sessionId}}`, {{ cache: 'no-store' }});
        if (res.ok) {{
          const data = await res.json();
          applyState(data);
        }} else if (res.status === 404) {{
          statusEl.textContent = 'Waiting';
          setHint('No GPS point has reached the backend for this SOS session yet.');
        }} else {{
          statusEl.textContent = 'Error';
          setHint(`Backend returned ${{res.status}} while loading location.`);
        }}
      }} catch (err) {{
        statusEl.textContent = 'Offline';
        setHint('Cannot reach the tracking backend from this browser.');
      }}
    }}

    // User pan/zoom should always win. Follow mode is optional and turns off as soon as the user moves the map.
    map.on('dragstart zoomstart', () => {{
      if (suppressViewportEvents) return;
      userMovedMap = true;
      if (followMode) setFollowMode(false);
    }});

    widgetMini.addEventListener('click', () => setPanelExpanded(true));
    collapsePanel.addEventListener('click', () => setPanelExpanded(false));
    expandBtn.addEventListener('click', () => setPanelExpanded(trackingWidget.classList.contains('collapsed')));
    recenterBtn.addEventListener('click', () => {{
      userMovedMap = false;
      recenterMap(true);
      setHint('Map recentered manually.');
    }});
    followBtn.addEventListener('click', () => setFollowMode(!followMode));

    // Lightweight drag support keeps the floating glass card out of the way on small screens.
    trackingWidget.addEventListener('pointerdown', (event) => {{
      if (event.target.closest('button')) return;
      const rect = trackingWidget.getBoundingClientRect();
      widgetDrag = {{
        pointerId: event.pointerId,
        offsetX: event.clientX - rect.left,
        offsetY: event.clientY - rect.top
      }};
      trackingWidget.setPointerCapture(event.pointerId);
    }});

    trackingWidget.addEventListener('pointermove', (event) => {{
      if (!widgetDrag || event.pointerId !== widgetDrag.pointerId) return;
      const margin = 10;
      const maxX = window.innerWidth - trackingWidget.offsetWidth - margin;
      const maxY = window.innerHeight - trackingWidget.offsetHeight - margin;
      const left = Math.max(margin, Math.min(maxX, event.clientX - widgetDrag.offsetX));
      const top = Math.max(margin, Math.min(maxY, event.clientY - widgetDrag.offsetY));
      trackingWidget.style.left = `${{left}}px`;
      trackingWidget.style.top = `${{top}}px`;
      trackingWidget.style.right = 'auto';
      trackingWidget.style.bottom = 'auto';
    }});

    trackingWidget.addEventListener('pointerup', (event) => {{
      if (!widgetDrag || event.pointerId !== widgetDrag.pointerId) return;
      widgetDrag = null;
      trackingWidget.releasePointerCapture(event.pointerId);
    }});

    updateMiniPanel();
    startParentGeolocation();
    loadHistory();
    pollLatest();
    setInterval(pollLatest, 5000);

    const wsProtocol = location.protocol === 'https:' ? 'wss' : 'ws';
    function connectSocket() {{
      const ws = new WebSocket(`${{wsProtocol}}://${{location.host}}/ws/tracking/${{sessionId}}`);
      ws.onopen = () => statusEl.textContent = 'Live';
      ws.onmessage = (event) => {{
        const msg = JSON.parse(event.data);
        if (msg.event === 'tracking_update') applyLocation(msg.payload.location, msg.payload.session);
      }};
      ws.onclose = () => {{
        statusEl.textContent = 'Reconnecting';
        setTimeout(connectSocket, 2000);
      }};
      ws.onerror = () => ws.close();
    }}
    connectSocket();
  </script>
</body>
</html>
"""


@router.get("/live/{session_id}", response_class=HTMLResponse)
def public_live_tracking_page(session_id: str):
    return tracking_page(session_id)
