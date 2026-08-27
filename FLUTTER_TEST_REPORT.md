# SheGuard Flutter App Test Report

**Generated:** 2026-08-07 · Target: `SheGuard_App` (com.sheguard.app, versionCode 1, minSdk 23, targetSdk 35)

---

## 1. Static verification

| Check | Command | Result |
|---|---|---|
| Dependencies | `flutter pub get` | ✅ OK (81 packages newer versions available) |
| Static analysis | `flutter analyze` | ✅ "No issues found!" |
| Unit tests | `flutter test` | ✅ **6/6 passed** (model_payload_test + widget_test) |

## 2. Build verification

| Target | Result |
|---|---|
| APK build (debug/release) | ❌ **BLOCKED** — no working JDK |

### JDK failure details
- `JAVA_HOME=C:\Program Files\Java\jdk-21` is **invalid**: directory contains only `lib\`, no `java.exe`.
- No `java`/`javac` on PATH.
- Only runtimes found are PyCharm's bundled JBR 21.0.9 (`...\PyCharm Community Edition 2025.2.6\jbr`,
  `2025.2.6.1\jbr`); overriding `JAVA_HOME` to JBR fails at `:connectivity_plus:compileDebugJavaWithJavac`
  because **no `jlink.exe`** exists in the JBR.
- `flutter doctor` reports: Android toolchain "Cannot execute java", Android Studio not installed.

### Prebuilt artifacts (present in repo)
| APK | Size | Notes |
|---|---|---|
| `app-debug.apk` | 208.9 MB | dated 2026-05-13 |
| `app-release.apk` | 58.8 MB | dated earlier |
- `aapt dump` confirmed: package `com.sheguard.app`, versionCode 1, minSdk 23, targetSdk 35,
  permissions `INTERNET`, `ACCESS_FINE_LOCATION`.

## 3. Runtime verification

- No AVDs, no emulator system images, no connected devices → **runtime/device verification not possible** in this environment.

## 4. Code-level findings

| Area | Verdict | Detail |
|---|---|---|
| **Hardcoded IP** | ⚠️ | `lib/config/api_config.dart:2` → `http://192.168.1.3:8000` (old IP; current is `172.19.92.225`). Must be configurable/auto-detected. |
| **Missing endpoint** | ❌ | `auto_sos_manager.dart:263` polls `GET /emergency/status?session_id=…` every 15 s; **backend has no such route** → SOS status polling will always fail. |
| WebSocket | ❌ | `emergency_realtime_service.dart:80` + `incident_service.dart:96` connect to `/ws/live`; server returns 404 (libs missing). |
| Evidence encryption | ✅ | `evidence_capture_service.dart` AES-encrypts via `cryptography` before base64 upload; payload matches backend `EvidenceUpload`. |
| Background tracking | ✅ | `flutter_background_service` + `foreground_tracking_service.dart` present; queues location updates with sync-on-reconnect. |
| Dead code | ⚠️ | 7 unused files (see DEAD FILES report): `core/app_routes.dart`, `core/localhost.dart`, `core/api_config.dart`, `services/camera_service.dart`, `widgets/metric_tile.dart`, `widgets/status_tile.dart`, `widgets/timeline_card.dart`. |
| Phone API | ⚠️ | `third_party/telephony` path dependency is private; `flutter_secure_storage`, `geolocator`, `camera`, `record` all pinned. |

## 5. Verdict

Codebase is clean (analyze + tests pass) and well-architected, but **cannot be shipped/verified** here:
APK build blocked (JDK), runtime blocked (no device), and one backend endpoint is missing.

**Flutter score: 5.5 / 10** (static quality high; build/runtime unverifiable, integration gaps)

