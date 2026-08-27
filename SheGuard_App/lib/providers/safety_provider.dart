import 'dart:async';

import 'package:flutter/foundation.dart';

import '../core/safety_types.dart';
import '../models/location_update.dart';
import '../services/backend_health_service.dart';
import '../services/connectivity_service.dart';
import '../services/notification_service.dart';

class SafetyProvider extends ChangeNotifier {
  SafetyProvider(
    this._backendHealth,
    this._connectivity,
    this._notifications,
  );

  final BackendHealthService _backendHealth;
  final ConnectivityService _connectivity;
  final NotificationService _notifications;

  BackendStatus backendStatus = BackendStatus.unknown;
  ProtectionStatus protectionStatus = ProtectionStatus.inactive;
  TrackingStatus trackingStatus = TrackingStatus.idle;
  bool online = true;
  String? message;
  String? sessionId;
  String? emergencyId;
  LocationUpdate? lastLocation;
  DateTime? trackingStartedAt;
  StreamSubscription<bool>? _connectivitySub;
  bool _disposed = false;

  // HELP countdown
  Timer? _helpCountdownTimer;
  int helpCountdownSeconds = 0;
  bool helpActive = false;

  bool get emergencyActive =>
      protectionStatus == ProtectionStatus.emergency ||
      protectionStatus == ProtectionStatus.silentEmergency ||
      protectionStatus == ProtectionStatus.helpPending;

  Future<void> initialize() async {
    online = await _connectivity.isOnline();
    _connectivitySub ??= _connectivity.online.listen((value) async {
      online = value;
      if (!online) {
        backendStatus = BackendStatus.offline;
        message = 'Reconnecting to safety network...';
        if (trackingStatus == TrackingStatus.active) {
          trackingStatus = TrackingStatus.offline;
        }
        await _notifications.show(
          id: 20,
          title: 'Reconnecting to safety network',
          body: 'SOS can still send SMS with your GPS location.',
        );
      } else {
        await refreshBackendStatus();
        if (trackingStatus == TrackingStatus.offline) {
          trackingStatus = TrackingStatus.active;
        }
      }
      _notify();
    });
    if (!online) {
      backendStatus = BackendStatus.offline;
      message = 'Reconnecting to safety network...';
      _notify();
      return;
    }
    await refreshBackendStatus();
  }

  Future<void> refreshBackendStatus() async {
    backendStatus = await _backendHealth.check();
    message = backendStatus == BackendStatus.connected
        ? null
        : 'Reconnecting to safety network...';
    _notify();
  }

  void setMonitoring() {
    if (!emergencyActive) {
      protectionStatus = ProtectionStatus.monitoring;
      _notify();
    }
  }

  Future<void> activateEmergency({required bool silent}) async {
    protectionStatus =
        silent ? ProtectionStatus.silentEmergency : ProtectionStatus.emergency;
    await _notifications.show(
      id: 21,
      title: silent ? 'HELP ALERT SENT' : 'Emergency mode enabled',
      body: silent
          ? 'SheGuard is tracking quietly.'
          : 'SheGuard is sharing live GPS updates.',
    );
    _notify();
  }

  Future<void> activateHelp({VoidCallback? onComplete}) async {
    if (helpActive) return;
    helpActive = true;
    helpCountdownSeconds = 5;
    protectionStatus = ProtectionStatus.helpPending;
    await _notifications.show(
      id: 22,
      title: 'HELP DETECTED',
      body: 'Emergency will activate in 5 seconds. Tap to cancel.',
    );
    _notify();

    _helpCountdownTimer?.cancel();
    _helpCountdownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!helpActive) {
        timer.cancel();
        return;
      }
      helpCountdownSeconds -= 1;
      if (helpCountdownSeconds <= 0) {
        timer.cancel();
        // Auto-transition to emergency
        helpActive = false;
        helpCountdownSeconds = 0;
        activateEmergency(silent: false);
        onComplete?.call();
      } else {
        _notify();
      }
    });
  }

  void cancelHelp() {
    if (!helpActive) return;
    helpActive = false;
    helpCountdownSeconds = 0;
    _helpCountdownTimer?.cancel();
    _helpCountdownTimer = null;
    protectionStatus = ProtectionStatus.monitoring;
    _notifications.cancel(22);
    _notify();
  }

  void startTracking(String sessionId) {
    this.sessionId = sessionId;
    trackingStatus = TrackingStatus.active;
    trackingStartedAt = DateTime.now();
    _notify();
  }

  void updateLocation(LocationUpdate location) {
    lastLocation = location;
    if (trackingStatus != TrackingStatus.active && trackingStatus != TrackingStatus.offline) {
      trackingStatus = TrackingStatus.active;
    }
    _notify();
  }

  void setTrackingOffline() {
    if (trackingStatus == TrackingStatus.active) {
      trackingStatus = TrackingStatus.offline;
      _notify();
    }
  }

  void setTrackingOnline() {
    if (trackingStatus == TrackingStatus.offline) {
      trackingStatus = TrackingStatus.active;
      _notify();
    }
  }

  void stopTracking() {
    trackingStatus = TrackingStatus.stopped;
    sessionId = null;
    emergencyId = null;
    trackingStartedAt = null;
    _notify();
  }

  void setTrackingError(String error) {
    trackingStatus = TrackingStatus.error;
    message = error;
    _notify();
  }

  void resolveEmergency() {
    protectionStatus = ProtectionStatus.monitoring;
    stopTracking();
    _notify();
  }

  Duration? get trackingDuration {
    if (trackingStartedAt == null) return null;
    return DateTime.now().difference(trackingStartedAt!);
  }

  @override
  void dispose() {
    _disposed = true;
    _connectivitySub?.cancel();
    _helpCountdownTimer?.cancel();
    super.dispose();
  }

  void _notify() {
    if (!_disposed) notifyListeners();
  }
}