import html
import io
import json
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.schemas import LocationUpdate, TrackingStart, TrackingUpdate
from backend.database import get_db
from backend.models import LiveLocation, TrackingSession, User
from backend.services.realtime import realtime_hub


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
    db.add(row)
    db.commit()
    db.refresh(row)
    payload = {"session": session_out(session), "location": location_out(row)}
    realtime_hub.publish_from_sync("tracking_update", payload)
    realtime_hub.publish_session_from_sync(session_id, "tracking_update", payload)
    return row


@router.post("/location/update")
def update_location(payload: LocationUpdate, db: Session = Depends(get_db)):
    try:
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
async def start_tracking(payload: TrackingStart, db: Session = Depends(get_db)):
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
async def update_tracking(payload: TrackingUpdate, db: Session = Depends(get_db)):
    try:
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
  <title>SheGuard Live Tracking</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>
    html, body, #map {{ height: 100%; margin: 0; background: #071426; color: #fff; font-family: Arial, sans-serif; }}
    .panel {{ position: fixed; z-index: 1000; left: 16px; right: 16px; top: 16px; padding: 14px; background: rgba(7,20,38,.92); border: 1px solid rgba(229,57,53,.6); border-radius: 10px; box-shadow: 0 16px 40px rgba(0,0,0,.35); max-width: 860px; }}
    .title {{ color: #ff5a55; font-weight: 800; letter-spacing: .04em; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; margin-top: 10px; }}
    .metric {{ background: rgba(255,255,255,.08); padding: 8px; border-radius: 8px; font-size: 12px; }}
    .metric b {{ display: block; font-size: 15px; margin-top: 3px; }}
    .hint {{ margin-top: 8px; color: rgba(255,255,255,.72); font-size: 12px; }}
    .qr {{ position: fixed; z-index: 1000; right: 16px; bottom: 16px; width: 92px; padding: 8px; background: #fff; border-radius: 8px; box-shadow: 0 12px 32px rgba(0,0,0,.3); }}
    .qr img {{ display: block; width: 100%; height: auto; }}
    @media(max-width: 720px) {{ .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
    @media(max-width: 720px) {{ .qr {{ width: 72px; right: 10px; bottom: 10px; }} }}
  </style>
</head>
<body>
  <div class="panel">
    <div class="title">SOS LIVE TRACKING</div>
    <div>Session: <span id="session">{session_id_html}</span></div>
    <div class="grid">
      <div class="metric">Status<b id="status">Connecting</b></div>
      <div class="metric">Speed<b id="speed">--</b></div>
      <div class="metric">Lat / Lng<b id="coords">--</b></div>
      <div class="metric">Battery<b id="battery">--</b></div>
      <div class="metric">Last seen<b id="last">--</b></div>
    </div>
    <div class="hint" id="hint">Waiting for live GPS updates from the phone...</div>
  </div>
  <div class="qr"><img src="/track/{session_id_html}/qr" alt="Open live tracking QR code" /></div>
  <div id="map"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const sessionId = {session_id_json};
    const map = L.map('map').setView([20.5937, 78.9629], 5);
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{ maxZoom: 19 }}).addTo(map);
    let marker = null;
    let route = L.polyline([], {{ color: '#e53935', weight: 5, opacity: .9 }}).addTo(map);
    const statusEl = document.getElementById('status');
    const speedEl = document.getElementById('speed');
    const coordsEl = document.getElementById('coords');
    const batteryEl = document.getElementById('battery');
    const lastEl = document.getElementById('last');
    const hintEl = document.getElementById('hint');

    let lastLocationKey = null;
    let animFrame = null;
    const sosIcon = L.divIcon({{
      className: 'sos-marker',
      html: '<div style="width:22px;height:22px;background:#e53935;border:3px solid #fff;border-radius:50%;box-shadow:0 0 0 10px rgba(229,57,53,.25),0 0 28px rgba(229,57,53,.9);"></div>',
      iconSize: [28, 28],
      iconAnchor: [14, 14]
    }});

    function animateMarker(toLatLng) {{
      if (!marker) {{
        marker = L.marker(toLatLng, {{ icon: sosIcon }}).addTo(map);
        map.setView(toLatLng, 17);
        return;
      }}
      const from = marker.getLatLng();
      const start = performance.now();
      const duration = 900;
      if (animFrame) cancelAnimationFrame(animFrame);
      function step(now) {{
        const t = Math.min(1, (now - start) / duration);
        const eased = t < .5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
        const lat = from.lat + (toLatLng[0] - from.lat) * eased;
        const lng = from.lng + (toLatLng[1] - from.lng) * eased;
        marker.setLatLng([lat, lng]);
        if (t < 1) animFrame = requestAnimationFrame(step);
      }}
      animFrame = requestAnimationFrame(step);
    }}

    function asLocation(payload) {{
      if (!payload || payload.latitude == null || payload.longitude == null) return null;
      return {{
        location_id: payload.location_id,
        latitude: Number(payload.latitude),
        longitude: Number(payload.longitude),
        speed: payload.speed,
        battery: payload.battery,
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
      animateMarker(latLng);
      route.addLatLng(latLng);
      map.panTo(latLng, {{ animate: true, duration: .8 }});
      statusEl.textContent = loc.emergency_status || session?.status || 'active';
      speedEl.textContent = `${{Number(loc.speed || 0).toFixed(1)}} m/s`;
      coordsEl.textContent = `${{loc.latitude.toFixed(6)}}, ${{loc.longitude.toFixed(6)}}`;
      batteryEl.textContent = loc.battery == null ? '--' : `${{loc.battery}}%`;
      lastEl.textContent = loc.timestamp ? new Date(loc.timestamp).toLocaleTimeString() : '--';
      hintEl.textContent = `Live GPS received at ${{lastEl.textContent}}`;
    }}

    function applyState(data) {{
      route.setLatLngs([]);
      const points = Array.isArray(data.path) ? data.path : [];
      for (const point of points) {{
        const loc = asLocation(point);
        if (loc) {{
          const latLng = [loc.latitude, loc.longitude];
          route.addLatLng(latLng);
        }}
      }}
      const latest = asLocation(data.latest);
      if (latest) {{
        latest.emergency_status = data.emergency_status || (data.active ? 'active' : 'inactive');
        lastLocationKey = null;
        applyLocation(latest, {{ status: latest.emergency_status }});
      }} else {{
        statusEl.textContent = data.active ? 'Waiting' : 'Inactive';
        hintEl.textContent = 'No GPS point has reached the backend for this SOS session yet.';
      }}
    }}

    async function loadHistory() {{
      try {{
        const res = await fetch(`/tracking/history/${{sessionId}}`, {{ cache: 'no-store' }});
        if (!res.ok) return;
        const data = await res.json();
        route.setLatLngs([]);
        for (const loc of data.locations || []) applyLocation(loc, data.session);
      }} catch (err) {{
        hintEl.textContent = 'Unable to load route history yet. Retrying...';
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
          hintEl.textContent = 'No GPS point has reached the backend for this SOS session yet.';
        }} else {{
          statusEl.textContent = 'Error';
          hintEl.textContent = `Backend returned ${{res.status}} while loading location.`;
        }}
      }} catch (err) {{
        statusEl.textContent = 'Offline';
        hintEl.textContent = 'Cannot reach the tracking backend from this browser.';
      }}
    }}

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
