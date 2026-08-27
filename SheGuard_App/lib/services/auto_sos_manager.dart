import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/emergency_contact.dart';
import '../models/emergency_event.dart';
import '../models/location_update.dart';
import '../models/user.dart';
import 'api_service.dart';
import 'contact_service.dart';
import 'emergency_realtime_service.dart';
import 'location_service.dart';
import 'notification_service.dart';
import 'sos_service.dart';

class AutoSosManager extends ChangeNotifier {
  AutoSosManager({
    required ApiService api,
    required EmergencyRealtimeService realtime,
    required ContactService contactService,
    required LocationService locationService,
    required SosService sosService,
    required NotificationService notifications,
  })  : _api = api,
        _realtime = realtime,
        _contactService = contactService,
        _locationService = locationService,
        _sosService = sosService,
        _notifications = notifications {
    _eventSub = _realtime.events.listen(_handleEmergencyEvent);
    _stateSub = _realtime.states.listen((value) {
      realtimeState = value;
      notifyListeners();
    });
  }

  static const _activeSessionKey = 'active_auto_sos_session';
  static const _handledEventsKey = 'handled_auto_sos_events';

  final ApiService _api;
  final EmergencyRealtimeService _realtime;
  final ContactService _contactService;
  final LocationService _locationService;
  final SosService _sosService;
  final NotificationService _notifications;

  StreamSubscription<EmergencyEvent>? _eventSub;
  StreamSubscription<RealtimeConnectionState>? _stateSub;
  Timer? _countdownTimer;
  Timer? _statusTimer;
  User? _user;
  bool _disposed = false;

  EmergencyEvent? activeEvent;
  LocationUpdate? lastLocation;
  RealtimeConnectionState realtimeState = RealtimeConnectionState.idle;
  bool active = false;
  bool activating = false;
  bool gpsActive = false;
  String? sessionId;
  String? trackingUrl;
  String? error;
  int countdownSeconds = 0;
  int contactsAttempted = 0;
  int contactsSent = 0;
  int contactsFailed = 0;
  bool parentCallAttempted = false;
  bool parentCallStarted = false;
  String? parentCallName;
  String? parentCallNumber;
  DateTime? activatedAt;

  Future<void> bindUser(User? user) async {
    _user = user;
    if (user == null) {
      await _realtime.stop();
      await _stopTimers();
      return;
    }
    await _restoreActiveSession(user);
    await _realtime.start(userId: user.userId);
  }

  Future<void> _handleEmergencyEvent(EmergencyEvent event) async {
    final user = _user;
    if (user == null || !event.isForUser(user.userId)) return;
    if (await _wasHandled(event.eventId)) {
      debugPrint('[AUTO_SOS] Duplicate event ignored: ${event.eventId}');
      return;
    }
    await _activateFromEvent(user, event);
  }

  Future<void> _activateFromEvent(User user, EmergencyEvent event) async {
    if (activating || active) return;
    activating = true;
    error = null;
    notifyListeners();

    final resolvedSessionId = event.sessionId ??
        'auto-${event.incidentId ?? event.eventId}-${DateTime.now().toUtc().millisecondsSinceEpoch}';
    try {
      active = true;
      activeEvent = event;
      sessionId = resolvedSessionId;
      activatedAt = DateTime.now();
      countdownSeconds = 10;
      notifyListeners();

      LocationUpdate? current;
      try {
        current = await _locationService
            .currentUpdate(user.userId)
            .timeout(const Duration(seconds: 12));
      } catch (locationError) {
        current = await _locationService.lastKnownUpdate(user.userId);
        debugPrint('[AUTO_SOS] Current GPS unavailable: $locationError');
      }

      if (!event.isNear(current)) {
        throw const ApiException(
          'AI incident is outside the verification radius for this phone.',
        );
      }

      Map<String, dynamic> startResponse = const {};
      try {
        startResponse = await _api.postJson(
          '/emergency/start',
          event.toEmergencyStartPayload(
            currentUserId: user.userId,
            sessionId: resolvedSessionId,
            location: current,
          ),
        );
      } catch (apiError) {
        debugPrint(
            '[AUTO_SOS] emergency/start failed; continuing locally: $apiError');
      }

      final contacts = await _loadContacts(user.userId);
      trackingUrl = startResponse['tracking_url']?.toString() ??
          event.trackingUrl ??
          await _api.publicTrackingUrl(resolvedSessionId);
      await _notifications.showAutoSosActivatedForEvent(
        incidentType: event.incidentType,
        eventId: event.eventId,
      );
      EmergencyContact? parent;
      for (final contact in contacts) {
        if (!contact.isHidden && contact.displayPhoneNumber.trim().isNotEmpty) {
          parent = contact;
          break;
        }
      }
      parentCallAttempted = parent != null;
      parentCallName = parent?.displayName;
      parentCallNumber = parent?.displayPhoneNumber;
      notifyListeners();

      final result = await _sosService.activate(
        userId: user.userId,
        userName: user.fullName,
        contacts: contacts,
        silent: false,
        sirenEnabled: false,
        sessionIdOverride: resolvedSessionId,
        incidentType: event.incidentType,
        evidenceLinks: event.evidenceLinks,
        incidentTime: event.createdAt,
        createIncident: false,
        callFallbackEnabled: false,
        incidentResponseSeed: startResponse,
        startEmergencyTracking: (sid) async {
          _locationService.startTracking(
            userId: user.userId,
            sessionId: sid,
            onUpdate: (update) {
              lastLocation = update;
              gpsActive = true;
              notifyListeners();
            },
            onError: (trackingError) {
              error = trackingError.toString();
              gpsActive = false;
              notifyListeners();
            },
          );
        },
      );

      if (!result.success) {
        throw ApiException(result.error ?? 'Auto SOS could not start.');
      }

      parentCallStarted = result.callStarted;
      lastLocation = current;
      contactsAttempted = result.smsResult?.attempted ?? contacts.length;
      contactsSent = result.smsResult?.sent ?? 0;
      contactsFailed = result.smsResult?.failed ?? 0;
      await _markHandled(event.eventId);
      await _persistActiveSession(event);
      _startCountdown();
      _startStatusPolling();
    } catch (activationError) {
      active = false;
      error = activationError.toString();
      debugPrint('[AUTO_SOS] Activation failed: $activationError');
    } finally {
      activating = false;
      notifyListeners();
    }
  }

  Future<void> cancelAutoSos() async {
    active = false;
    activating = false;
    countdownSeconds = 0;
    gpsActive = false;
    parentCallAttempted = false;
    parentCallStarted = false;
    parentCallName = null;
    parentCallNumber = null;
    error = null;
    await _stopTimers();
    _locationService.stopTracking();
    await _sosService.stopEmergencyServices();
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_activeSessionKey);
    notifyListeners();
  }

  Future<List<EmergencyContact>> _loadContacts(int userId) async {
    try {
      return await _contactService.fetchContacts(userId);
    } catch (error) {
      debugPrint('[AUTO_SOS] Contacts unavailable: $error');
      return const [];
    }
  }

  void _startCountdown() {
    _countdownTimer?.cancel();
    _countdownTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!active || countdownSeconds <= 0) {
        _countdownTimer?.cancel();
        return;
      }
      countdownSeconds -= 1;
      notifyListeners();
    });
  }

  void _startStatusPolling() {
    _statusTimer?.cancel();
    _statusTimer = Timer.periodic(const Duration(seconds: 15), (_) async {
      final sid = sessionId;
      if (!active || sid == null) return;
      try {
        await _locationService.syncQueuedTrackingUpdates();
        final status = await _api.getJson('/emergency/status?session_id=$sid');
        final state = status['status']?.toString().toLowerCase() ??
            status['state']?.toString().toLowerCase();
        if (state == 'resolved' || state == 'cancelled' || state == 'closed') {
          await cancelAutoSos();
        }
      } catch (statusError) {
        error = statusError.toString();
        notifyListeners();
      }
    });
  }

  Future<void> _restoreActiveSession(User user) async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_activeSessionKey);
    if (raw == null || raw.isEmpty) return;
    try {
      final json = jsonDecode(raw) as Map<String, dynamic>;
      final event = EmergencyEvent.fromJson(
        json['event'] as Map<String, dynamic>,
      );
      activeEvent = event;
      active = true;
      sessionId = json['session_id']?.toString();
      trackingUrl = json['tracking_url']?.toString();
      activatedAt = DateTime.tryParse(json['activated_at']?.toString() ?? '');
      _locationService.startTracking(
        userId: user.userId,
        sessionId: sessionId,
        onUpdate: (update) {
          lastLocation = update;
          gpsActive = true;
          notifyListeners();
        },
        onError: (trackingError) {
          error = trackingError.toString();
          gpsActive = false;
          notifyListeners();
        },
      );
      _startStatusPolling();
      notifyListeners();
    } catch (restoreError) {
      debugPrint('[AUTO_SOS] Restore failed: $restoreError');
      await prefs.remove(_activeSessionKey);
    }
  }

  Future<void> _persistActiveSession(EmergencyEvent event) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      _activeSessionKey,
      jsonEncode({
        'session_id': sessionId,
        'tracking_url': trackingUrl,
        'activated_at': activatedAt?.toUtc().toIso8601String(),
        'event': event.toJson(),
      }),
    );
  }

  Future<bool> _wasHandled(String eventId) async {
    final prefs = await SharedPreferences.getInstance();
    return (prefs.getStringList(_handledEventsKey) ?? const [])
        .contains(eventId);
  }

  Future<void> _markHandled(String eventId) async {
    final prefs = await SharedPreferences.getInstance();
    final handled = prefs.getStringList(_handledEventsKey) ?? const [];
    await prefs.setStringList(
      _handledEventsKey,
      [eventId, ...handled.where((item) => item != eventId)].take(50).toList(),
    );
  }

  Future<void> _stopTimers() async {
    _countdownTimer?.cancel();
    _statusTimer?.cancel();
    _countdownTimer = null;
    _statusTimer = null;
  }

  @override
  void dispose() {
    _disposed = true;
    _eventSub?.cancel();
    _stateSub?.cancel();
    _stopTimers();
    _realtime.dispose();
    super.dispose();
  }

  @override
  void notifyListeners() {
    if (!_disposed) super.notifyListeners();
  }
}
