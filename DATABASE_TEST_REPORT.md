# SheGuard Database Test Report

**Generated:** 2026-08-07 · **Databases inspected:** backend `SheGuard_Backend\sheguard.db`, AI `SheGuard\sheguard.db`.

---

## 1. Backend database — `sheguard.db` (1.3 MB, SQLite)

### Schema
- **16 tables:** alerts, cameras, cctv_cameras, emergency_contacts, emergency_notifications,
  emergency_sessions, events, evidence, evidence_records, incident_victim_links, incidents, legacy_users,
  live_locations, sqlite_sequence, tracking_sessions, users
- **40 indexes**
- `PRAGMA integrity_check` → **OK**
- Foreign-key violation scan → **0**

### Row counts
| Table | Rows |
|---|---|
| incidents | 174 |
| users | 54 |
| live_locations | 1,406 |
| emergency_contacts | 10 |
| cctv_cameras | 2 |
| events | 2 |
| alerts | 2 |
| emergency_notifications | present |
| legacy_users | 1 |

### Data-quality findings (NULL / invalid values)

| Table / column | Problem rows | Notes |
|---|---|---|
| `incidents.user_id` | 98 NULL | incidents not linked to a user |
| `incidents.latitude` / `longitude` | 74 / 74 NULL | no GPS |
| `incidents.threat_level` | 5 NULL | |
| `incidents.ai_provider` | 143 NULL | cloud-AI field largely unused |
| `incidents.image_path` / `video_path` | 97 / 97 NULL | evidence missing for 56% of incidents |
| `live_locations.session_id` | 457 NULL | |
| `live_locations.battery` / `accuracy` | 104 / 105 NULL | |
| `cctv_cameras.latitude` / `longitude` | 1 / 1 NULL | |
| `users.profile_photo` | 54 NULL | all users |

**Not fatal** (columns nullable by design), but incident-to-user linking and evidence coverage are poor.

## 2. AI engine database — `SheGuard\sheguard.db` (32 KB, legacy)

- 5 tables; integrity OK.
- 2 alerts, 2 events, 1 user.
- Legacy artifact of the old `SheGuard\backend.py`; not used by the new backend.

## 3. Query performance

| Query | Time |
|---|---|
| Select 50 incidents | 51.5 ms (cold) |
| 10 × select 5 incidents | 6.4 ms total |
| Full `/incidents` endpoint | 144 ms avg (incl. serialization of 174 rows) |

No locking errors observed. SQLite is the single-writer bottleneck, but acceptable at this scale.

## 4. Verdict

Schema and integrity are healthy. The main concerns are **data coverage** (many incidents unlinked to users,
missing media/GPS) rather than corruption.

**Database score: 8 / 10**
