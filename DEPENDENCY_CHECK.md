# SheGuard Dependency Check Report

**Generated:** 2026-08-07 · Versions verified from installed packages/venvs.

---

## 1. AI engine venv (`SheGuard\.venv`)

| Package | Version | Status |
|---|---|---|
| torch | 2.11.0+cpu | ⚠️ CPU-only (no CUDA) |
| opencv-python | 4.13.0 | ✅ |
| mediapipe | 0.10.14 | ✅ |
| numpy | 2.2.6 | ✅ |
| scikit-learn | 1.7.2 | ✅ |
| ultralytics | 8.4.47 | ✅ |
| groq | 1.2.0 | ✅ |

## 2. Backend venv (`SheGuard_Backend\.venv`)

| Package | Version | Status |
|---|---|---|
| fastapi | 0.136.1 | ✅ |
| uvicorn | 0.46.0 | ✅ |
| sqlalchemy | 2.0.49 | ✅ |
| torch | 2.11.0+cpu | ⚠️ CPU-only |
| numpy | 2.2.6 | ✅ |
| opencv-python | 4.13.0.92 | ✅ |
| groq | 1.2.0 | ✅ |

### Missing (listed in `requirements-api.txt` but never installed)

| Package | Consequence |
|---|---|
| **python-multipart** | `/incidents/create` multipart → **500** |
| **websockets** / **wsproto** | All WebSocket endpoints → **404** |
| **pytest** | backend test suite not runnable here |
| **mediapipe** | not used by backend (AI engine only) — low impact |

> The 3 blockers (python-multipart, websockets/wsproto) are the difference between the REST app working and
> the realtime/multipart features working. Install before deployment.

## 3. Dashboard (`SheGuard_Dashboard\package.json`)

- npm install ✅; `npm run build` ✅.
- Vite build warning: chunk > 500 kB (513.26 kB) — cosmetic.

## 4. Flutter (`SheGuard_App`)

| Item | Status |
|---|---|
| `flutter pub get` | ✅ |
| Packages out of date | 81 (newer versions available) |
| Private dependency | `third_party/telephony` (path) — not on pub.dev |
| Gradle/JDK | ❌ build blocked (no working JDK) |
| Key packages | flutter_secure_storage, geolocator 13, camera, record, flutter_background_service, web_socket_channel, shared_preferences, http, cryptography |

## 5. System-level tooling

| Tool | Status |
|---|---|
| Python 3.10.11 | ✅ |
| Node v22.22.3 / npm 10.9.8 | ✅ |
| Flutter 3.32.0 / Dart 3.8.0 | ✅ |
| Git 2.54.0 | ✅ |
| JDK | ❌ broken install |
| Android SDK / adb | ✅ present (no AVD/devices) |
| ffmpeg / sqlite3 CLI | not on PATH (not required at runtime) |

## 6. Verdict

Two easy fixes unlock the biggest gaps:
1. `pip install python-multipart websockets` in the backend venv.
2. Install a working JDK 17+ for Android builds.

**Dependency score: 7 / 10**
