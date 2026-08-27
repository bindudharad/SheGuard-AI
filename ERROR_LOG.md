# SheGuard Error & Defect Log

**Generated:** 2026-08-07 · Consolidated findings from runtime, logs, and static review.

---

## BLOCKERS (must fix before production)

| # | Defect | Evidence | Impact |
|---|---|---|---|
| 1 | `.env` JWT secret is placeholder `replace-with-a-long-random-secret`; `security.py` rejects it | register/login → 500; fixed only by env override | Auth broken on stock config |
| 2 | `python-multipart` not installed | `/incidents/create` multipart → 500 | Camera/AI media uploads fail |
| 3 | `websockets`/`wsproto` not installed | `/ws/live`, `/ws/emergency/{id}`, `/ws/tracking/{id}` → 404 | Realtime layer dead |
| 4 | No working JDK on system (JAVA_HOME broken, no jlink.exe) | APK build fails at `:connectivity_plus:compileDebugJavaWithJavac` | Cannot build Android app |
| 5 | `/emergency/status` endpoint missing on backend | Flutter `auto_sos_manager.dart:263` polls it every 15 s | SOS status polling always fails |

## HIGH

| # | Defect | Evidence | Impact |
|---|---|---|---|
| 6 | AI accuracy on real video: attack→"fight" (all 15 frames); normal→31/33 "fight" | real-video inference tests | False alarms / missed attacks |
| 7 | Dashboard `title` maps from `raw.type`; backend returns `incident_type` | live API vs `lib/incidents.js` | Every incident shows "SOS Emergency" |
| 8 | Dashboard default API URL = old IP `192.168.1.3:8000`; Vite env is build-time only | `src/config.js:1` | Wrong backend unless rebuilt with env var |
| 9 | Flutter hardcoded API URL `192.168.1.3:8000` | `lib/config/api_config.dart:2` | App can't reach current backend |
| 10 | No login rate limiting | 10 bad logins → no 429 | Brute-force exposure |

## MEDIUM

| # | Defect | Evidence |
|---|---|---|
| 11 | `/evidence/file` route shadowed by `/evidence/{incident_id}` (int) → unreachable | route order in incidents.py |
| 12 | `/health` path doesn't exist (health at `/`) — docs/consumers may 404 | route table |
| 13 | CORS defaults to `*` | `main.py` `_cors_origins` |
| 14 | `/docs`, `/redoc`, `/openapi.json` public | no auth |
| 15 | `/system/local-network` unauth'd info disclosure | 200 without token |
| 16 | `.env` contains valid GROQ/GEMINI/OPENROUTER/HF/NVIDIA/TELEGRAM keys | secrets in working tree (gitignored) |
| 17 | incident→user linking poor (98/174 NULL user_id); evidence missing for 56% (97/174) | DB audit |
| 18 | 7 unused Flutter files; `groq_client.py` duplicated in AI+backend; `telegram.py` legacy duplicate; `train_v2.py` orphaned; 3 orphaned `telegram_*_test.py` | dead-files scan |
| 19 | XSS name stored raw (mitigated by React default escaping) | register with `<script>` name |
| 20 | `SHEGUARD_FULL_FILE_TREE.txt` 238 MB + ~187 MB report JSONs not gitignored | repo bloat risk |

## LOW / WATCH

| # | Defect |
|---|---|
| 21 | Watchdog prints `STEP 4 COOLDOWN CHECK` every ~1 s (log noise) |
| 22 | Bundle chunk > 500 kB warning |
| 23 | 81 outdated Flutter packages |
| 24 | `metrics.json` / `metrics_v2.json` byte-identical duplicates |
| 25 | `/incidents` & `/incident/history` unpaginated |
| 26 | Old `sheguard.log` shows Telegram send timeouts (alert path reliability) |
| 27 | Two FastAPI backends coexist (`SheGuard\backend.py` legacy + `SheGuard_Backend\app\`) |

## Historical errors (from `logs/sheguard.log`)
- Telegram delivery timeouts during alert sends.
- `forrtl: error (200)` window-close crash when backend shell closes (cosmetic; use hidden start).

---

**Error log score: 8 blockers/20 issues logged** → remediation priority as listed above.

