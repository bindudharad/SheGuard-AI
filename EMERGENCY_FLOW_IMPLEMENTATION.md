# SheGuard Emergency Flow Implementation Report

**Generated:** 2026-08-22T16:31:00Z
**Implementation:** Complete emergency assistant + live tracking + CCTV/police response

---

## PHASE 0: SYSTEM AUDIT COMPLETED

### Existing Architecture Discovered

#### Mobile App (SheGuard_App)
- `services/sos_service.dart` - SOS activation, SMS, call, tracking
- `services/location_service.dart` - GPS tracking with foreground service
- `services/foreground_tracking_service.dart` - Background GPS upload
- `services/emergency_realtime_service.dart` - WebSocket live updates
- `services/auto_sos_manager.dart` - AI-triggered emergency (EXISTING)
- `screens/emergency_mode_screen.dart` - Emergency UI
- **MISSING:** Voice assistant/speech recognition
- **MISSING:** 5-second confirmation timer in SOS flow

#### Backend (SheGuard_Backend)
- `routes/locations.py` - Location/tracking endpoints + live map
- `routes/emergency.py` - Emergency session management
- `models/entities.py` - EmergencySession, TrackingSession, CCTVCamera, etc.
- `services/emergency_session_manager.py` - Session lifecycle
- `services/geo.py` - Haversine distance calculation
- **MISSING:** `/emergency/status` endpoint
- **MISSING:** CCTV nearby discovery
- **MISSING:** Incident-to-emergency proximity linking

#### Key Database Models
- `User` - User accounts
- `EmergencySession` - Emergency tracking sessions
- `TrackingSession` - GPS tracking sessions
- `LiveLocation` - GPS breadcrumb trail
- `Incident` - AI-detected incidents
- `CCTVCamera` - Camera registry with lat/lon
- `IncidentVictimLink` - Links incidents to users
- `EvidenceRecord` - Evidence storage

---

## IMPLEMENTATION PLAN

### Critical Issues to Fix

1. **NO 5-second confirmation in SOS flow**
   - Current: SOS button → immediate tracking
   - Required: SOS button → 5-second countdown → tracking (unless cancelled)

2. **NO voice assistant system**
   - Current: No speech recognition
   - Required: Background voice detection for "help" / "help me"
   - **LIMITATION:** Android 10+ restricts background microphone access
   - **SOLUTION:** Implement foreground service with visible notification when voice mode is enabled

3. **NO /emergency/status endpoint**
   - Flutter app polls `/emergency/status` every 15 seconds
   - Backend route is missing

4. **NO CCTV nearby discovery**
   - When emergency starts, backend should find nearby cameras
   - Link CCTV incidents to active emergency by proximity

5. **Hardcoded API URLs**
   - Flutter: `http://192.168.1.3:8000`
   - Should be configurable

---

## PHASES 1-26: IMPLEMENTATION STATUS

### Phase 1-2: Emergency Trigger + Confirmation
**STATUS:** PARTIAL - Auto SOS exists, manual SOS needs confirmation timer

**Current Flow:**
```
SOS Button → activate() → immediate tracking + call
```

**Required Flow:**
```
SOS Button → confirmation UI → 5 seconds → tracking (or cancel)
```

**Implementation Required:**
1. Add confirmation screen between SOS press and tracking start
2. Add 5-second countdown timer
3. Add cancel button
4. Voice cancellation (if voice system implemented)

### Phase 3-4: Tracking State Machine
**STATUS:** EXISTS - Already implemented in `auto_sos_manager.dart`

**States:**
- IDLE
- ACTIVATING  
- ACTIVE
- GPS_ACTIVE
- ERROR

### Phase 5-9: GPS Tracking + Backend + Delivery
**STATUS:** COMPLETE - Fully implemented

**Architecture:**
```
Phone GPS
  ↓
ForegroundTrackingService (background upload)
  ↓
Backend /tracking/update
  ↓
LiveLocation + TrackingSession storage
  ↓
WebSocket broadcast
  ↓
Dashboard
```

**Features:**
- ✅ Foreground service with wakelock
- ✅ Offline queue (300 points max)
- ✅ Queue sync when connection returns
- ✅ Battery, speed, heading, accuracy
- ✅ Session management
- ✅ WebSocket real-time delivery
- ✅ Polling fallback (5 seconds)

### Phase 10-12: CCTV Association + Incident Linking
**STATUS:** NOT IMPLEMENTED

**Required:**
1. Backend: Find nearby cameras when emergency starts
2. Backend: Link CCTV incidents to emergency by proximity
3. Use existing `IncidentVictimLink` model
4. Distance threshold: configurable (default 500m)

**Implementation:**
```python
# In emergency_session_manager.py
def find_nearby_cameras(session: EmergencySession, radius_meters: float = 500):
    if not session.last_latitude or not session.last_longitude:
        return []
    
    cameras = db.query(CCTVCamera).filter(
        CCTVCamera.online_status == 'online',
        CCTVCamera.latitude.isnot(None),
        CCTVCamera.longitude.isnot(None)
    ).all()
    
    nearby = []
    for cam in cameras:
        distance = haversine_distance_meters(
            GeoPoint(session.last_latitude, session.last_longitude),
            GeoPoint(cam.latitude, cam.longitude)
        )
        if distance <= radius_meters:
            nearby.append({'camera': cam, 'distance': distance})
    
    return sorted(nearby, key=lambda x: x['distance'])
```

### Phase 13-16: Police Dashboard
**STATUS:** PARTIAL - Basic tracking page exists

**Existing:**
- ✅ Live tracking map page `/track/{session_id}`
- ✅ Victim marker with animation
- ✅ Parent GPS marker
- ✅ OSRM routing
- ✅ WebSocket updates
- ✅ Drag-to-reposition widget
- ✅ Follow mode
- ✅ QR code

**Missing:**
- ❌ Police-specific dashboard view
- ❌ Active emergencies list
- ❌ Nearby cameras display
- ❌ Linked incidents display
- ❌ Event timeline
- ❌ Evidence gallery

### Phase 17-22: Mobile UI + Background + Offline
**STATUS:** COMPLETE

**Mobile UI:**
- ✅ Emergency mode screen with live status
- ✅ GPS status indicator
- ✅ Battery level
- ✅ Contact status
- ✅ Countdown timer (for auto SOS)
- ✅ Cancel button

**Background:**
- ✅ Foreground service (Android)
- ✅ Wakelock
- ✅ Battery optimization bypass request
- ✅ Visible notification

**Offline:**
- ✅ Offline queue (300 GPS points)
- ✅ Queue sync on reconnect
- ✅ Session persistence
- ✅ Auto-recovery

### Phase 23-26: Testing + Documentation
**STATUS:** IN PROGRESS

---

## REMAINING IMPLEMENTATION WORK

### HIGH PRIORITY

#### 1. Add 5-Second Confirmation to Manual SOS
**File:** `SheGuard_App/lib/services/sos_service.dart`

**Change:** Add optional confirmation callback:
```dart
Future<SosActivationResult> activateWithConfirmation({
  required int userId,
  required String userName,
  required List<EmergencyContact> contacts,
  required Function() onConfirmationStart,
  required Future<bool> Function() waitForConfirmation,
}) async {
  onConfirmationStart();
  final confirmed = await waitForConfirmation(); // 5-second timer
  if (!confirmed) {
    return SosActivationResult(success: false, cancelled: true);
  }
  return activate(...);
}
```

#### 2. Add /emergency/status Endpoint
**File:** `SheGuard_Backend/app/routes/emergency.py`

**Code:**
```python
@router.get("/emergency/status")
def emergency_status(session_id: str, db: Session = Depends(get_db)):
    session = db.get(EmergencySession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    tracking = db.get(TrackingSession, session_id)
    
    return {
        "session_id": session_id,
        "status": session.status,
        "tracking_active": tracking.status == "active" if tracking else False,
        "last_update_at": session.last_update_at,
        "latitude": session.last_latitude,
        "longitude": session.last_longitude,
    }
```

#### 3. Add CCTV Nearby Discovery
**File:** `SheGuard_Backend/app/services/emergency_session_manager.py`

**Code:**
```python
from app.services.geo import GeoPoint, haversine_distance_meters

def discover_nearby_cameras(
    self,
    db: Session,
    session: EmergencySession,
    radius_meters: float = 500
) -> list[dict]:
    if not session.last_latitude or not session.last_longitude:
        return []
    
    from app.models import CCTVCamera
    cameras = db.query(CCTVCamera).filter(
        CCTVCamera.latitude.isnot(None),
        CCTVCamera.longitude.isnot(None)
    ).all()
    
    session_point = GeoPoint(session.last_latitude, session.last_longitude)
    nearby = []
    
    for cam in cameras:
        cam_point = GeoPoint(cam.latitude, cam.longitude)
        distance = haversine_distance_meters(session_point, cam_point)
        
        if distance <= radius_meters:
            nearby.append({
                "camera_id": cam.camera_id,
                "camera_name": cam.camera_name,
                "distance_meters": round(distance, 1),
                "latitude": cam.latitude,
                "longitude": cam.longitude,
            })
    
    return sorted(nearby, key=lambda x: x["distance_meters"])
```

#### 4. Add Incident-to-Emergency Linking
**File:** `SheGuard_Backend/app/services/incident_linking.py` (new)

**Code:**
```python
def link_incident_to_active_emergencies(
    db: Session,
    incident: Incident,
    radius_meters: float = 500
) -> list[EmergencySession]:
    if not incident.latitude or not incident.longitude:
        return []
    
    active_sessions = db.query(EmergencySession).filter(
        EmergencySession.status.in_(["active", "acknowledged", "responding"]),
        EmergencySession.last_latitude.isnot(None),
        EmergencySession.last_longitude.isnot(None)
    ).all()
    
    incident_point = GeoPoint(incident.latitude, incident.longitude)
    linked = []
    
    for session in active_sessions:
        session_point = GeoPoint(session.last_latitude, session.last_longitude)
        distance = haversine_distance_meters(incident_point, session_point)
        
        if distance <= radius_meters:
            # Create link
            existing_link = db.query(IncidentVictimLink).filter(
                IncidentVictimLink.incident_id == incident.incident_id,
                IncidentVictimLink.user_id == session.user_id
            ).first()
            
            if not existing_link:
                link = IncidentVictimLink(
                    incident_id=incident.incident_id,
                    user_id=session.user_id,
                    emergency_session_id=session.session_id,
                    distance_meters=distance,
                    match_method="gps_proximity",
                    confidence=1.0 - (distance / radius_meters)
                )
                db.add(link)
                linked.append(session)
    
    if linked:
        db.commit()
    
    return linked
```

### MEDIUM PRIORITY

#### 5. Voice Assistant System
**Limitation:** Android 10+ restricts background microphone access

**Implementation Options:**

**Option A: Foreground Service Voice Mode (Recommended)**
- User explicitly enables "Voice Emergency Mode"
- Shows permanent notification: "SheGuard is listening for emergency commands"
- Continuous speech recognition while mode is active
- Detects "help", "help me", emergency keywords
- Battery impact: moderate

**Option B: Phrase Activation (Pixel/Samsung only)**
- Some devices support always-on "OK Google" style detection
- Not portable across all Android devices
- Requires device-specific APIs

**Option C: Manual Voice Button**
- User presses voice button to activate listening
- 10-second listening window
- Simplest, no background service needed

**Recommendation:** Implement Option C first (manual voice button), then Option A for advanced users.

#### 6. Flutter API URL Configuration
**File:** `SheGuard_App/lib/config/api_config.dart`

**Current:**
```dart
static const String baseUrl = 'http://192.168.1.3:8000';
```

**Fix:**
```dart
static String get baseUrl {
  const envUrl = String.fromEnvironment('API_BASE_URL', defaultValue: '');
  if (envUrl.isNotEmpty) return envUrl;
  
  // Development default
  return 'http://192.168.1.3:8000';
}
```

**Build with:**
```bash
flutter build apk --dart-define=API_BASE_URL=https://api.sheguard.com
```

---

## ARCHITECTURE DIAGRAMS

### Emergency Trigger Flow (Current - Auto SOS)
```
AI CCTV Detection
      ↓
Backend Incident Created
      ↓
WebSocket Event to Mobile
      ↓
EmergencyRealtimeService receives event
      ↓
AutoSosManager._activateFromEvent()
      ↓
10-second countdown starts
      ↓
(User can cancel)
      ↓
If not cancelled:
   → Call parent
   → Start GPS tracking
   → Send SMS
   → Create backend session
```

### Emergency Trigger Flow (Required - Manual SOS)
```
SOS Button Pressed
      ↓
Show Confirmation Screen
      ↓
5-Second Countdown
      ↓
┌─────────┴─────────┐
│                   │
Cancel           No Action
│                   │
↓                   ↓
Return      Activate SOS
            (same as Auto SOS)
```

### GPS Tracking Architecture
```
Phone
  ├─ Geolocator.getCurrentPosition()
  ├─ Best accuracy mode
  ├─ 60-second timeout
  ↓
ForegroundTrackingService (background)
  ├─ Timer.periodic (every 15 seconds)
  ├─ Wakelock enabled
  ├─ Foreground notification
  ├─ Offline queue (300 points)
  ↓
Backend POST /tracking/update
  ├─ Store in LiveLocation
  ├─ Update TrackingSession
  ├─ Update EmergencySession
  ↓
WebSocket Broadcast
  ├─ Event: "tracking_update"
  ├─ To: dashboard, mobile clients
  ↓
Dashboard Live Map
  ├─ Animate victim marker
  ├─ Recalculate route
  ├─ Update ETA/distance
```

### CCTV Association Flow (To Be Implemented)
```
Emergency Session Created
      ↓
Emergency Start Event
      ↓
discover_nearby_cameras(session, radius=500m)
      ↓
For each camera within radius:
  ├─ Calculate distance
  ├─ Sort by distance
  ├─ Return camera list
      ↓
Store nearby cameras in session metadata
      ↓
When CCTV AI detects incident:
  ├─ Check active emergencies
  ├─ Calculate distance to each
  ├─ If < 500m: create IncidentVictimLink
  ├─ Publish to dashboard
      ↓
Dashboard shows:
  ├─ "CCTV-04 detected following behavior"
  ├─ "Distance: 180m from victim"
  ├─ "Risk: 87/100"
  ├─ Evidence thumbnails
```

---

## LIMITATIONS DISCOVERED

### 1. Voice Assistant Limitations
**Android Platform Restrictions:**
- Android 10+ restricts background microphone access
- Continuous listening requires foreground service with visible notification
- Battery impact: moderate to high
- User must explicitly enable voice mode

**Recommendation:**
- Implement manual voice button first
- Add foreground voice mode as advanced feature
- Clearly communicate battery impact
- Provide toggle to enable/disable

### 2. Background Operation Limitations
**Platform Constraints:**
- Foreground service required for reliable background operation
- Must show persistent notification (Android requirement)
- Battery optimization must be disabled for best reliability
- Some manufacturers (Xiaomi, Oppo) aggressively kill background services

**Current Implementation:**
- ✅ Foreground service configured
- ✅ Wakelock enabled during tracking
- ✅ Battery optimization bypass requested
- ✅ Visible notification shown

### 3. GPS Accuracy Limitations
**Real-World Factors:**
- Indoor GPS accuracy: 10-50m
- Urban canyon effect: 5-30m
- Open sky: 3-10m
- GPS timeout: 60 seconds

**Mitigation:**
- Uses best accuracy mode
- Falls back to last known location
- Queues updates when connection fails
- Shows accuracy value in UI

### 4. CCTV Limitations
**Current State:**
- CCTVCamera model exists in database
- No camera registration API
- No camera discovery implemented
- No incident-to-camera linking

**Required for Production:**
- Camera registration API
- Camera health monitoring
- Automatic camera discovery
- Incident proximity matching

---

## TESTING REQUIREMENTS

### Manual Test Procedure

#### Test A: SOS Button (With Confirmation - After Implementation)
1. Login to mobile app
2. Press SOS button
3. **Expected:** Confirmation screen appears
4. **Expected:** 5-second countdown starts
5. Press "Cancel" before countdown ends
6. **Expected:** Return to home screen, no tracking starts
7. Press SOS button again
8. **Expected:** Confirmation screen appears
9. Wait for countdown to reach 0
10. **Expected:** Tracking starts, call initiated, SMS sent

#### Test B: Auto SOS (AI-Triggered)
1. Backend creates incident with user's location
2. **Expected:** Mobile receives WebSocket event
3. **Expected:** Auto SOS manager activates
4. **Expected:** 10-second countdown (can be cancelled)
5. **Expected:** If not cancelled: tracking + call + SMS

#### Test C: GPS Tracking
1. Start emergency (SOS or Auto)
2. **Expected:** Foreground service starts
3. **Expected:** GPS updates every 15 seconds
4. **Expected:** Backend receives updates
5. **Expected:** Dashboard map shows live location
6. Disable internet on phone
7. Wait 60 seconds
8. Re-enable internet
9. **Expected:** Queued GPS points sync to backend

#### Test D: Dashboard Live Updates
1. Open `/track/{session_id}` in browser
2. **Expected:** Map loads, victim marker appears
3. **Expected:** WebSocket connects
4. **Expected:** New GPS points animate marker
5. **Expected:** Route recalculates every 5 seconds
6. **Expected:** ETA and distance update

#### Test E: Backend Unavailable
1. Start emergency tracking
2. Stop backend server
3. Wait 60 seconds
4. **Expected:** Mobile queues GPS updates
5. **Expected:** UI shows "reconnecting"
6. Restart backend
7. **Expected:** Mobile reconnects
8. **Expected:** Queued updates sync

### Automated Tests (To Be Created)

```python
# test_emergency_flow.py
def test_emergency_session_creation():
    session = emergency_manager.start_session(
        db, user=user, latitude=13.0, longitude=77.0
    )
    assert session.status == "active"
    assert session.live_tracking_url is not None

def test_nearby_camera_discovery():
    cameras = emergency_manager.discover_nearby_cameras(
        db, session, radius_meters=500
    )
    assert len(cameras) > 0
    assert cameras[0]["distance_meters"] < 500

def test_incident_proximity_linking():
    incident = create_test_incident(latitude=13.0, longitude=77.0)
    linked = incident_linking.link_incident_to_active_emergencies(
        db, incident, radius_meters=500
    )
    assert len(linked) > 0
```

---

## FILES TO CHANGE

### Backend Files

1. **app/routes/emergency.py** - Add `/emergency/status` endpoint
2. **app/services/emergency_session_manager.py** - Add CCTV discovery
3. **app/services/incident_linking.py** - NEW - Proximity linking
4. **app/routes/incidents.py** - Call linking after incident creation

### Mobile Files

1. **lib/services/sos_service.dart** - Add confirmation flow
2. **lib/screens/home_screen.dart** - Add confirmation dialog
3. **lib/widgets/sos_button.dart** - Modify to show confirmation
4. **lib/config/api_config.dart** - Make URL configurable

### Optional (Voice Assistant)

1. **lib/services/voice_assistant_service.dart** - NEW
2. **lib/screens/settings_screen.dart** - Add voice mode toggle

---

## COMMANDS TO RUN

### Backend
```bash
cd C:\Programs\codex\SheGuard\SheGuard_Backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Mobile (Development)
```bash
cd C:\Programs\codex\SheGuard\SheGuard_App
flutter run --dart-define=API_BASE_URL=http://192.168.1.3:8000
```

### Mobile (Production Build)
```bash
flutter build apk --dart-define=API_BASE_URL=https://api.sheguard.com --release
```

### Dashboard
```bash
cd C:\Programs\codex\SheGuard\SheGuard_Dashboard
npm run dev
```

---

## NEXT STEPS

### Immediate (This Session)
1. ✅ Complete system audit
2. ⏳ Implement `/emergency/status` endpoint
3. ⏳ Implement CCTV nearby discovery
4. ⏳ Implement incident proximity linking
5. ⏳ Add 5-second confirmation to SOS
6. ⏳ Test end-to-end flow

### Short-term (Next Sprint)
1. Voice assistant (manual button variant)
2. Police dashboard enhancements
3. Evidence gallery in dashboard
4. Event timeline visualization
5. Camera health monitoring

### Long-term
1. Voice assistant (foreground service variant)
2. ML-based false positive reduction
3. Multi-camera coordination
4. Predictive threat modeling
5. Integration with police dispatch systems

---

## CONCLUSION

The SheGuard system has a solid foundation with:
- ✅ GPS tracking fully implemented
- ✅ WebSocket real-time updates working
- ✅ Offline queue and recovery working
- ✅ Emergency session management exists
- ✅ Auto SOS (AI-triggered) functional

Critical gaps to close:
- ❌ 5-second confirmation for manual SOS
- ❌ `/emergency/status` endpoint
- ❌ CCTV nearby discovery
- ❌ Incident proximity linking
- ❌ Voice assistant system

Priority: Implement the 4 critical gaps first, then voice assistant as Phase 2.
