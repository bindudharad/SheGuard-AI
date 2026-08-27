# SheGuard Dashboard Test Report

**Generated:** 2026-08-07 · Target: `SheGuard_Dashboard` (React + Vite)

---

## 1. Build

| Check | Result |
|---|---|
| `npm install` | ✅ |
| `npm run build` | ✅ (~10–11 s) |
| Bundle warning | ⚠️ chunk > 500 kB (513.26 kB) — minor, not a failure |

## 2. Live verification (vite preview, PID 34516, http://127.0.0.1:5173)

| Flow | Result |
|---|---|
| Login (phone + password → JWT) | ✅ 200 |
| Incidents list `/incidents` | ✅ 200 |
| Latest incidents `/incidents/latest` | ✅ 200 |
| Live tracking `/tracking/live/{id}` | ✅ 200 |
| Live location `/location/live/{id}` | ✅ 200 |
| Detail map (react-leaflet + OSM) | ✅ renders (needs internet) |

Refresh is **2 s polling** (`REFRESH_INTERVAL_MS=2000`); there is **no WebSocket usage** in the dashboard.

## 3. Defects found

### 3.1 Hardcoded API base URL (build-time)
- `src/config.js:1` default is `http://192.168.1.3:8000` (stale IP).
- Vite inlines `VITE_API_BASE_URL` at **build** time; it is **not** read at runtime.
- The QA build was rebuilt with `VITE_API_BASE_URL=http://localhost:8000`; verified the old IP is gone from
  the emitted bundle and the app then reaches the backend.
- **Fix:** read from runtime config/`import.meta.env` with a sane default, or serve a runtime config file.

### 3.2 Incident title/address mapping bug
- `lib/incidents.js` `normalizeIncident` maps `title` from `raw.type`, but the backend returns `incident_type`
  (confirmed via live API). Result: **every incident title falls back to "SOS Emergency"**.
- `address` similarly maps from fields the backend does not send → falls back to "GPS coordinates pending".
- Backend incident payload has no `type`/`title`/`image_url`/`video_url` fields (confirmed live).

### 3.3 Other
- `DetailMap` uses `L.divIcon` + OSM tiles — requires outbound internet.
- `IncidentDetailPage` is an overlay component, not a route (fine).
- No dead/unused files in `src/` (all 22 files referenced).

## 4. Verdict

Runs and talks to the backend correctly after a correct build-time env var, but two configuration/data-
mapping defects degrade the UX (wrong title/address, stale IP default).

**Dashboard score: 7.5 / 10**

