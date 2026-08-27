# SheGuard App - Improvement Plan

Audit date: 2026-05-12

## Goal

Move the current Flutter MVP from "feature-rich local demo" to "production-testable mobile safety client" by stabilizing backend contracts, cleaning platform configs, strengthening security, and adding tests around emergency behavior.

## Phase 0 - Repository Hygiene

Priority: immediate

Tasks:

1. Remove generated outputs from version control/workspace tracking:
   - `.dart_tool/`
   - `build/`
   - `android/.gradle/`
   - `android/build/`
   - `android/.kotlin/`
   - `ios/Flutter/ephemeral/`
   - generated plugin registrants if the team chooses to regenerate them
2. Remove local machine config:
   - `android/local.properties`
3. Keep `.flutter-plugins-dependencies` out of committed source unless the team intentionally tracks Flutter generated metadata.
4. Add a clean-repo check in CI:
   - `flutter pub get`
   - `flutter analyze`
   - `flutter test`
   - optional `flutter build apk --debug`

Acceptance criteria:

- Fresh clone can run `flutter pub get` and build without checked-in generated folders.
- No local SDK paths appear in source.

## Phase 1 - Android Platform Cleanup

Priority: immediate

Tasks:

1. Choose Gradle style:
   - Option A: keep Groovy (`settings.gradle`, `build.gradle`, `app/build.gradle`)
   - Option B: keep Kotlin DSL (`*.gradle.kts`)
2. Delete the ignored/conflicting set.
3. Choose final Android identity:
   - current active: `com.sheguard.app`
   - conflicting ignored: `com.sheguard.sheguard_app`
4. Keep one `MainActivity.kt` under the matching package.
5. Add production release signing:
   - `key.properties`
   - release signing config
   - no debug signing for release
6. Make cleartext debug-only:
   - remove global `android:usesCleartextTraffic="true"` for release
   - use debug network security config if LAN HTTP is still needed

Acceptance criteria:

- `flutter build apk --debug` has no "settings.gradle.kts is ignored" warning.
- Package ID is consistent across manifest/build/source.
- Release build is signable with a real keystore.

## Phase 2 - Backend Contract Stabilization

Priority: immediate

Tasks:

1. Create an OpenAPI or Markdown contract for all endpoints.
2. Decide fate of undocumented endpoints:
   - `/system/local-network`
   - `/track/{session_id}`
   - `/tracking/start`
   - `/tracking/update`
   - `/evidence/upload`
   - `/camera/register`
   - `/camera/list`
3. If backend will support them:
   - document request/response bodies
   - add backend health endpoint
   - require auth where appropriate
   - add mobile integration tests
4. If backend will not support them yet:
   - feature-flag public tracking/evidence upload/camera APIs
   - stop retrying unavailable upload endpoints
   - use `/location/update` consistently for MVP tracking

Acceptance criteria:

- Every endpoint called by Dart appears in the backend contract.
- Every documented "not implemented" feature is either removed from runtime code or protected by a feature flag.

## Phase 3 - SOS Workflow Hardening

Priority: high

Tasks:

1. Replace immediate `SosActivationResult` with `EmergencySessionState`.
2. Track steps:
   - call attempted
   - tracking started
   - GPS acquired
   - SMS attempted/sent/failed
   - incident created
   - evidence capture started
   - evidence encrypted
3. Persist emergency session immediately before platform calls.
4. Restore active emergency session on app restart.
5. Show accurate UI progress instead of "0 contacts" while background sync is pending.
6. Make duplicate throttling durable by storing last activation timestamp.

Acceptance criteria:

- User sees honest progress during SOS.
- App restart during SOS still shows emergency active.
- Tests cover SMS failure, backend failure, GPS failure, and no-contact cases.

## Phase 4 - Security And Privacy

Priority: high

Tasks:

1. Enforce HTTPS in production.
2. Move sensitive SharedPreferences payloads to encrypted storage:
   - contact metadata
   - emergency sessions
   - evidence manifest
   - evidence upload queue
   - offline tracking queue if it contains precise location
3. Add stale raw evidence cleanup on app start.
4. Add evidence retention/delete controls.
5. Define and enforce privacy guard:
   - mask exact location in non-emergency UI
   - reduce logging of coordinates/contact details
   - disable optional evidence capture if privacy mode requires it
6. Reduce sensitive debug logging.
7. Add permission rationale screens for SMS, call, background location, camera, microphone, notifications, battery optimization.

Acceptance criteria:

- Sensitive data at rest is encrypted or intentionally documented.
- Raw evidence files do not survive crashes unhandled.
- Production builds do not allow cleartext API calls.

## Phase 5 - iOS Parity Or Android-Only Declaration

Priority: high if iOS is required

Tasks:

1. Add missing `Info.plist` keys:
   - camera usage
   - microphone usage
   - notification usage as required by plugin/current iOS target
   - background location modes if intended
2. Audit each plugin for iOS behavior:
   - direct SMS is not equivalent to Android SEND_SMS
   - direct phone calls may open dialer instead of auto-calling
   - background service behavior differs significantly
3. Add iOS-specific fallbacks and UI copy.
4. Run iOS build on macOS CI or local Mac.

Acceptance criteria:

- Either README clearly says "Android only for emergency automation" or iOS builds and permission prompts work correctly.

## Phase 6 - Performance Improvements

Priority: medium

Tasks:

1. Disable LAN scan in production and move it behind developer mode.
2. Cache/reduce reverse geocoding:
   - only geocode after meaningful distance/time changes
   - avoid geocoding every high-frequency tracking update
3. Split `HomeScreen`:
   - header/status
   - SOS controls
   - quick actions
   - active emergency panel
   - developer panel
4. Replace broad provider watches with `Selector` or smaller widgets.
5. Batch/offload queue writes if tracking volume grows.

Acceptance criteria:

- Home screen rebuilds are localized.
- Startup/API discovery is predictable.
- Emergency tracking remains high accuracy, normal monitoring is lower power.

## Phase 7 - Test Coverage

Priority: medium

Add tests for:

- `ApiService` response decoding, auth header, timeout/error mapping.
- `AuthProvider.restore()` success/failure.
- `ContactProvider` metadata overlay and local hide/edit behavior.
- `LocationService` queueing and sync behavior using mocked API.
- `SosService` no contacts, SMS denied, backend down, GPS unavailable, duplicate throttle.
- `EvidenceCaptureService` upload unavailable and queue retention.
- `MotionProtectionService` shake/fall threshold behavior through testable pure functions.
- Actual widget smoke tests for `LoginScreen`, `RegisterScreen`, `HomeScreen`, `ContactsScreen`.

Acceptance criteria:

- Critical emergency paths have deterministic tests without real plugins.
- `flutter test` covers provider/service logic, not just DTOs.

## Phase 8 - Architecture Refactor

Priority: medium

Target structure:

```text
lib/
|-- app/
|   |-- environment.dart
|   |-- routes.dart
|   `-- bootstrap.dart
|-- features/
|   |-- auth/
|   |-- contacts/
|   |-- evidence/
|   |-- incidents/
|   |-- settings/
|   |-- sos/
|   `-- tracking/
|-- shared/
|   |-- api/
|   |-- storage/
|   |-- platform/
|   |-- theme/
|   `-- widgets/
`-- main.dart
```

Tasks:

1. Move endpoint calls to typed repositories.
2. Add a single route source.
3. Add platform wrapper interfaces for SMS/call/location/notification/camera/audio.
4. Convert emergency flow into a session controller.
5. Remove dead modules or feature-flag them:
   - camera service
   - unused widgets
   - obsolete route exports

Acceptance criteria:

- Feature folders own their models/providers/services/screens.
- Emergency flow can be tested without plugin channels.

## Phase 9 - Dashboard/Admin Plan

Priority: later

Because no dashboard exists in this workspace, do not bolt admin screens into the mobile app without backend support.

Recommended dashboard architecture:

- Separate web app: Flutter Web, React, or Next.js.
- Backend admin APIs:
  - admin login/roles
  - users list/detail
  - contacts read-only/audit
  - incidents list/detail
  - live location/session view
  - evidence review
  - camera source management
  - analytics aggregations
- Security:
  - role-based access control
  - audit logs
  - evidence access logging
  - no public incident data without signed URLs/session authorization

Acceptance criteria:

- Admin dashboard is not started until backend admin API and authorization model exist.

## Suggested Work Order

1. Clean Android Gradle/package duplication.
2. Align API contract and remove impossible runtime calls.
3. Harden SOS progress/state.
4. Lock down production security.
5. Expand tests.
6. Refactor by feature.
7. Add dashboard only after backend admin APIs exist.

## Success Metrics

- No analyzer warnings.
- Debug build has no Gradle conflict warning.
- All runtime endpoints are documented.
- SOS UI shows accurate progress.
- Emergency state survives restart.
- Sensitive local data is encrypted.
- At least 25-40 meaningful unit/widget tests cover auth, contacts, SOS, tracking, evidence, and settings.
