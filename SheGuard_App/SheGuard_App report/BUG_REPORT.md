# SheGuard App - Bug And Risk Report

Audit date: 2026-05-12

## Verification Results

- `flutter analyze`: completed with 1 issue.
- `flutter test`: all 5 tests passed.
- `flutter build apk --debug`: built `build\app\outputs\flutter-apk\app-debug.apk` successfully.
- Build warning: Flutter reports both `android/settings.gradle` and `android/settings.gradle.kts` exist, so `android/settings.gradle.kts` is ignored.

## Critical Issues

### 1. Backend API contract mismatch

Files:

- `lib/services/location_service.dart`
- `lib/services/foreground_tracking_service.dart`
- `lib/services/evidence_capture_service.dart`
- `lib/services/api_service.dart`
- `lib/services/camera_service.dart`
- `README.md`
- `PROJECT_STATUS.md`

Problem:

The app calls endpoints that are not in the documented `SheGuard_AI` contract:

- `GET /system/local-network`
- `GET /track/{session_id}`
- `POST /tracking/start`
- `POST /tracking/update`
- `POST /evidence/upload`
- `POST /camera/register`
- `GET /camera/list`

`README.md` and `PROJECT_STATUS.md` explicitly say evidence upload, public tracking pages, admin dashboards, and CCTV AI pipelines are outside this Flutter workspace. The client nevertheless attempts those calls.

Impact:

- SOS live tracking can queue indefinitely or fail silently if `/tracking/*` is absent.
- SMS tracking links may point to pages that do not exist.
- Evidence upload queues can accumulate forever.
- Camera/CCTV APIs are dead code unless backend exists.

Recommended fix:

Create a versioned API contract. Either implement these backend endpoints or remove/feature-flag client calls until the backend supports them.

### 2. Android Gradle configuration conflict

Files:

- `android/settings.gradle`
- `android/settings.gradle.kts`
- `android/build.gradle`
- `android/build.gradle.kts`
- `android/app/build.gradle`
- `android/app/build.gradle.kts`
- `android/app/src/main/kotlin/com/sheguard/app/MainActivity.kt`
- `android/app/src/main/kotlin/com/sheguard/sheguard_app/MainActivity.kt`

Problem:

Both Groovy and Kotlin DSL Gradle files exist. Flutter uses `settings.gradle` and ignores `settings.gradle.kts`. The active Groovy config sets `applicationId = "com.sheguard.app"` and `namespace = "com.sheguard.app"`, while Kotlin DSL uses `com.sheguard.sheguard_app`.

Impact:

- Future developers may edit ignored `.kts` files and see no effect.
- Package identity can drift between debug/release/build machines.
- Duplicate `MainActivity` files are confusing and increase upgrade risk.

Recommended fix:

Pick one Gradle style. Delete the ignored/conflicting set, keep one package ID, and keep one matching `MainActivity.kt`.

### 3. Production release uses debug signing

Files:

- `android/app/build.gradle`
- `android/app/build.gradle.kts`

Problem:

Release build config signs with debug signing config.

Impact:

- Not suitable for Play Store or secure production distribution.
- APK identity/security cannot be trusted for release.

Recommended fix:

Add `key.properties`, keystore loading, release signing config, and keep keystores out of source control.

### 4. Cleartext HTTP enabled

File:

- `android/app/src/main/AndroidManifest.xml`

Problem:

`android:usesCleartextTraffic="true"` allows HTTP traffic.

Impact:

- Credentials, tokens, incident data, and location can travel over unencrypted HTTP if backend is not HTTPS.
- Acceptable for LAN testing, not production.

Recommended fix:

Use HTTPS for production, add network security config with debug-only cleartext exceptions, and require `SHEGUARD_API_BASE_URL` for non-debug builds.

## High-Severity Issues

### 5. SOS UI reports before SMS/backend work completes

Files:

- `lib/services/sos_service.dart`
- `lib/screens/home_screen.dart`

Problem:

`SosService.activate()` starts `_runEmergencyBackgroundSync()` with `unawaited(...)` and immediately returns `SosActivationResult` with `smsResult: null`. `HomeScreen` then shows a snackbar such as "sent to 0 contacts" even though SMS is still running in the background.

Impact:

- Misleading emergency feedback.
- User may believe no contacts were alerted.

Recommended fix:

Expose SOS progress as a stream/state object or wait for the SMS step before showing recipient count.

### 6. Evidence upload is implemented despite documented absence

File:

- `lib/services/evidence_capture_service.dart`

Problem:

The service posts `/evidence/upload`, but docs say evidence upload is not implemented.

Impact:

- Upload queue can grow and retry forever.
- Backend 404/405 errors are hidden as deferred upload.

Recommended fix:

Add a backend upload endpoint or disable upload queue behind a feature flag.

### 7. Sensitive metadata in SharedPreferences

Files:

- `lib/services/local_contact_metadata_service.dart`
- `lib/services/sos_service.dart`
- `lib/services/location_service.dart`
- `lib/services/evidence_capture_service.dart`
- `lib/providers/settings_provider.dart`

Problem:

SharedPreferences stores contact names/phone overrides, emergency sessions, tracking queues, evidence manifest metadata, and backend base URL.

Impact:

- Data may be visible in device backups or rooted devices.
- Evidence filenames/paths/session IDs leak even if evidence content is encrypted.

Recommended fix:

Move sensitive metadata to encrypted storage or encrypt the SharedPreferences payloads with a key from `FlutterSecureStorage`.

### 8. Raw evidence exists before encryption

File:

- `lib/services/evidence_capture_service.dart`

Problem:

Audio is recorded to a raw `.m4a` path and encrypted only when recording stops. Camera image is also captured to a temporary clear image path before encryption.

Impact:

- Crash, OS kill, or storage sync during capture could leave temporary raw evidence.

Recommended fix:

Add startup cleanup/encryption of stale raw files, shorten raw file lifetime, and document evidence retention.

### 9. iOS permissions incomplete

File:

- `ios/Runner/Info.plist`

Problem:

The app uses camera, microphone, notifications, location, recording, and background-adjacent behavior, but `Info.plist` only includes location and notification strings. Missing likely keys include camera and microphone usage descriptions; background location modes are not configured.

Impact:

- iOS runtime permission crashes or denied plugin behavior.

Recommended fix:

Add required iOS permission descriptions and background modes if iOS is a supported target.

## Medium-Severity Issues

### 10. Generated and local files are present despite ignore rules

Files/folders:

- `.dart_tool/`
- `build/`
- `android/.gradle/`
- `android/build/`
- `android/.kotlin/`
- `ios/Flutter/Generated.xcconfig`
- `ios/Flutter/flutter_export_environment.sh`
- `android/local.properties`
- `.flutter-plugins-dependencies`

Problem:

Generated/cache/machine-specific files are visible in the workspace. `.gitignore` already lists many of them, but there is no `.git` repository here to confirm tracking status.

Impact:

- Bloated workspace, reproducibility risk, possible local path exposure.

Recommended fix:

Remove generated outputs from source control and regenerate with `flutter pub get` and `flutter build`.

### 11. Deprecated Flutter API

File:

- `lib/screens/splash_screen.dart:107`

Problem:

`withOpacity` is deprecated. Analyzer recommends `withValues()`.

Impact:

- Low immediate risk; future Flutter migration noise.

Recommended fix:

Replace `withOpacity(x)` with `withValues(alpha: x)`.

### 12. Large HomeScreen and broad rebuild scope

File:

- `lib/screens/home_screen.dart`

Problem:

`HomeScreen` is 708 lines and watches auth, location, incidents, safety, settings, and contacts.

Impact:

- Hard to test.
- More rebuilds than necessary.
- Emergency workflow logic is mixed with UI composition.

Recommended fix:

Split emergency controller/state, header, metrics, actions, and developer panel into separate widgets/classes.

### 13. LAN subnet scan can be slow and privacy-sensitive

File:

- `lib/services/api_service.dart`

Problem:

Backend discovery scans candidate LAN IPs with HTTP requests.

Impact:

- Startup/API delay.
- Battery/network overhead.
- May be flagged by networks/security tools.

Recommended fix:

Prefer explicit `--dart-define` backend URL. Restrict discovery to debug builds or a developer-mode action.

### 14. Privacy guard setting is not enforced

Files:

- `lib/providers/settings_provider.dart`
- `lib/screens/settings_screen.dart`
- `lib/services/evidence_capture_service.dart`
- `lib/services/location_service.dart`

Problem:

`privacyGuardEnabled` is persisted and displayed but does not appear to alter evidence capture, logging, SMS content, or location sharing.

Impact:

- User expectation mismatch.

Recommended fix:

Define privacy-guard behavior and enforce it in evidence/logging/location flows.

### 15. Dead or unused code

Likely unused:

- `lib/core/app_routes.dart`
- `lib/core/localhost.dart`
- `lib/models/camera_source.dart`
- `lib/services/camera_service.dart`
- `lib/widgets/metric_tile.dart`
- `lib/widgets/status_tile.dart`
- `lib/widgets/timeline_card.dart`
- `IncidentProvider.triggerSos()`
- `ApiConfig.publicTrackingBaseUrl`

Impact:

- Increases maintenance cost and suggests incomplete modules.

Recommended fix:

Remove dead code or wire it into features with tests.

## Low-Severity Issues

### 16. Tests are too shallow

Files:

- `test/model_payload_test.dart`
- `test/widget_test.dart`

Problem:

Existing tests cover DTO payloads and a smoke `MaterialApp`, not actual app/provider/service flows.

Recommended fix:

Add mocked API tests for auth restore, contacts, SOS progress, location queueing, and evidence upload failure.

### 17. Backend health uses incident endpoint

File:

- `lib/services/backend_health_service.dart`

Problem:

Health check calls `/incident/live?limit=1`.

Impact:

- Health status depends on incident endpoint behavior and auth semantics.

Recommended fix:

Add backend `GET /health` or `GET /system/health`.

## Missing Configurations

- Production backend HTTPS URL/configuration.
- Production Android signing.
- iOS camera/microphone permission strings.
- CI workflow.
- Backend API schema/OpenAPI reference.
- Privacy policy or permission onboarding documentation.
- Firebase/Supabase configs are absent, which is fine because the app does not use them.

## Dependency Risks

From `flutter pub outdated`:

- Direct packages behind latest: `camera`, `connectivity_plus`, `flutter_local_notifications`, `flutter_secure_storage`, `geolocator`, `network_info_plus`, `permission_handler`, `shared_preferences`, `wakelock_plus`, `flutter_lints`.
- Transitive discontinued package: `js 0.6.7`.
- Vendored `third_party/telephony` declares SDK `<3.0.0`, but the app SDK is `>=3.3.0 <4.0.0`. It currently builds, but this is a long-term compatibility risk.

## Final Bug Priority

1. Align backend endpoints.
2. Clean Android Gradle/package duplication.
3. Fix production security posture: HTTPS, cleartext debug-only, release signing.
4. Fix SOS result/progress reporting.
5. Harden evidence/privacy storage.
6. Complete iOS permission config or mark Android-only.
