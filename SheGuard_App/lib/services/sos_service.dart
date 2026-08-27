import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/emergency_contact.dart';
import '../models/location_update.dart';
import 'api_service.dart';
import 'emergency_call_service.dart';
import 'emergency_siren_service.dart';
import 'emergency_sms_service.dart';
import 'evidence_capture_service.dart';
import 'incident_service.dart';
import 'location_service.dart';
import 'notification_service.dart';

class SosActivationResult {
  const SosActivationResult({
    required this.success,
    required this.sessionId,
    required this.location,
    required this.smsResult,
    required this.callStarted,
    this.error,
  });

  final bool success;
  final String sessionId;
  final LocationUpdate? location;
  final EmergencySmsResult? smsResult;
  final bool callStarted;
  final String? error;
}

class SosService {
  SosService({
    required LocationService locationService,
    required IncidentService incidentService,
    required EmergencySmsService smsService,
    required EmergencyCallService callService,
    required EmergencySirenService sirenService,
    required ApiService apiService,
    required EvidenceCaptureService evidenceCaptureService,
    required NotificationService notificationService,
  })  : _locationService = locationService,
        _incidentService = incidentService,
        _smsService = smsService,
        _callService = callService,
        _sirenService = sirenService,
        _apiService = apiService,
        _evidenceCapture = evidenceCaptureService,
        _notifications = notificationService;

  static const _sessionsKey = 'emergency_sessions';
  static const _duplicateWindow = Duration(seconds: 30);

  final LocationService _locationService;
  final IncidentService _incidentService;
  final EmergencySmsService _smsService;
  final EmergencyCallService _callService;
  final EmergencySirenService _sirenService;
  final ApiService _apiService;
  final EvidenceCaptureService _evidenceCapture;
  final NotificationService _notifications;

  bool _activating = false;
  DateTime? _lastActivationAt;

  Future<SosActivationResult> activate({
    required int userId,
    required String userName,
    required List<EmergencyContact> contacts,
    required bool silent,
    bool sirenEnabled = false,
    String? sessionIdOverride,
    String? incidentType,
    List<String> evidenceLinks = const [],
    DateTime? incidentTime,
    bool createIncident = true,
    bool callFallbackEnabled = true,
    Map<String, dynamic> incidentResponseSeed = const {},
    required Future<void> Function(String sessionId) startEmergencyTracking,
  }) async {
    final now = DateTime.now();
    final sessionId =
        sessionIdOverride ?? 'sos-${now.toUtc().millisecondsSinceEpoch}';

    if (_activating ||
        (_lastActivationAt != null &&
            now.difference(_lastActivationAt!) < _duplicateWindow)) {
      debugPrint('SheGuard SOS throttled to prevent duplicate alert spam.');
      return SosActivationResult(
        success: false,
        sessionId: sessionId,
        location: null,
        smsResult: null,
        callStarted: false,
        error: 'SOS is already being processed. Please wait a moment.',
      );
    }

    _activating = true;
    _lastActivationAt = now;

    try {
      debugPrint('[SOS] SOS pressed: $sessionId');

      final callStarted = await _callService.callPrimaryImmediately(
        contacts,
        sessionId: sessionId,
        allowFallback: callFallbackEnabled,
      );
      debugPrint('[SOS] Emergency call initiated for $sessionId: $callStarted');

      unawaited(_notifications.showEmergencyModeEnabled(silent: silent));
      if (silent) {
        unawaited(_notifications.showSilentEmergencyEnabled());
      }
      unawaited(_notifications.showLiveTrackingActive());
      unawaited(_notifications.showSosActivated(silent: silent));
      unawaited(_sirenService.start(enabled: sirenEnabled && !silent));
      unawaited(_evidenceCapture.startEmergencyCapture(sessionId));

      unawaited(startEmergencyTracking(sessionId).then((_) {
        debugPrint('[TRACKING] Foreground tracking started: $sessionId');
      }).catchError((Object error) {
        debugPrint(
          '[TRACKING] Tracking start failed but SOS remains active: $error',
        );
      }));

      unawaited(_runEmergencyBackgroundSync(
        userId: userId,
        userName: userName,
        sessionId: sessionId,
        silent: silent,
        contacts: contacts,
        incidentType: incidentType,
        evidenceLinks: evidenceLinks,
        incidentTime: incidentTime,
        createIncident: createIncident,
        incidentResponseSeed: incidentResponseSeed,
      ));

      return SosActivationResult(
        success: true,
        sessionId: sessionId,
        location: null,
        smsResult: null,
        callStarted: callStarted,
      );
    } catch (error) {
      debugPrint('[SOS] Call initiation failed for $sessionId: $error');
      unawaited(_runEmergencyBackgroundSync(
        userId: userId,
        userName: userName,
        sessionId: sessionId,
        silent: silent,
        contacts: contacts,
        incidentType: incidentType,
        evidenceLinks: evidenceLinks,
        incidentTime: incidentTime,
        createIncident: createIncident,
        incidentResponseSeed: incidentResponseSeed,
      ));
      return SosActivationResult(
        success: false,
        sessionId: sessionId,
        location: null,
        smsResult: null,
        callStarted: false,
        error: error.toString(),
      );
    } finally {
      _activating = false;
    }
  }

  Future<void> stopEmergencyCapture() {
    return _evidenceCapture.stopEmergencyCapture();
  }

  Future<void> stopEmergencyServices() async {
    _callService.cancelFallback();
    await _sirenService.stop();
    await _evidenceCapture.stopEmergencyCapture();
  }

  Future<void> _runEmergencyBackgroundSync({
    required int userId,
    required String userName,
    required String sessionId,
    required bool silent,
    required List<EmergencyContact> contacts,
    String? incidentType,
    List<String> evidenceLinks = const [],
    DateTime? incidentTime,
    bool createIncident = true,
    Map<String, dynamic> incidentResponseSeed = const {},
  }) async {
    LocationUpdate? location;
    var smsResult = const EmergencySmsResult(attempted: 0, sent: 0, failed: 0);
    Map<String, dynamic> incidentResponse = Map<String, dynamic>.from(
      incidentResponseSeed,
    );
    try {
      debugPrint('[SOS] Background SOS sync started: $sessionId');
      final trackingUrlFuture = _apiService
          .publicTrackingUrl(sessionId)
          .timeout(const Duration(seconds: 10), onTimeout: () => null)
          .catchError((Object error) {
        debugPrint('[NETWORK] Tracking URL check failed: $error');
        return null;
      });
      final Future<LocationUpdate?> smsLocationFuture = () async {
        try {
          return await _locationService
              .currentUpdate(userId)
              .timeout(const Duration(seconds: 12));
        } catch (error) {
          debugPrint('[GPS] SMS fallback GPS unavailable: $error');
          final lastKnown = await _locationService.lastKnownUpdate(userId);
          if (lastKnown != null) {
            debugPrint(
              '[GPS] Using last known GPS fallback: '
              '${lastKnown.latitude},${lastKnown.longitude}',
            );
          }
          return lastKnown;
        }
      }();

      final trackingUrl = await trackingUrlFuture;
      if (trackingUrl == null) {
        debugPrint(
          '[NETWORK] Backend unreachable before SMS. Sending Google Maps fallback only.',
        );
      }
      location = await smsLocationFuture;
      if (location != null) {
        debugPrint(
          '[GPS] SMS GPS fallback ready: '
          '${location.latitude},${location.longitude}',
        );
      }

      smsResult = await _smsService.sendEmergencySms(
        contacts: contacts,
        location: location,
        userName: userName,
        trackingUrl: trackingUrl,
        incidentType: incidentType,
        evidenceLinks: evidenceLinks,
        incidentTime: incidentTime,
      );
      debugPrint(
        '[SOS] SMS sent for $sessionId: '
        '${smsResult.sent}/${smsResult.attempted} sent, '
        '${smsResult.failed} failed',
      );

      try {
        await _locationService.startTrackingSession(
          userId: userId,
          sessionId: sessionId,
          initialLocation: location,
        );
        debugPrint('[TRACKING] Session created: $sessionId');
      } catch (error) {
        debugPrint('[TRACKING] Session create failed: $error');
      }

      try {
        location = await _locationService.sendCurrentLocation(userId,
            sessionId: sessionId);
        debugPrint(
          '[GPS] First GPS uploaded for $sessionId: '
          '${location.latitude},${location.longitude}',
        );
      } catch (error) {
        debugPrint(
          '[GPS] First GPS unavailable; foreground retry continues: $error',
        );
      }

      if (createIncident) {
        try {
          incidentResponse = await _incidentService.createSos(
            userId: userId,
            location: location,
            silent: silent,
          );
          debugPrint('[SOS] incidents/create success for $sessionId');
        } catch (error) {
          debugPrint(
            '[SOS] incidents/create failed; SOS call/tracking continue: $error',
          );
        }
      }

      await _storeSession(
        sessionId: sessionId,
        userId: userId,
        silent: silent,
        startedAt: DateTime.now(),
        location: location,
        smsResult: smsResult,
        incidentResponse: incidentResponse,
      );
    } catch (error) {
      debugPrint('[SOS] Background SOS sync failed: $error');
    }
  }

  Future<void> _storeSession({
    required String sessionId,
    required int userId,
    required bool silent,
    required DateTime startedAt,
    required LocationUpdate? location,
    required EmergencySmsResult smsResult,
    required Map<String, dynamic> incidentResponse,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final existing = prefs.getStringList(_sessionsKey) ?? const [];
    final record = <String, dynamic>{
      'session_id': sessionId,
      'user_id': userId,
      'silent': silent,
      'started_at': startedAt.toUtc().toIso8601String(),
      if (location != null) 'latitude': location.latitude,
      if (location != null) 'longitude': location.longitude,
      'sms_attempted': smsResult.attempted,
      'sms_sent': smsResult.sent,
      'sms_failed': smsResult.failed,
      'incident_id': incidentResponse['incident_id'],
      'incident_response': incidentResponse,
    };
    await prefs.setStringList(
      _sessionsKey,
      [jsonEncode(record), ...existing].take(20).toList(),
    );
    debugPrint('SheGuard emergency session stored: $sessionId');
  }
}
