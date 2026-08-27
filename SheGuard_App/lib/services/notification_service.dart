import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:shared_preferences/shared_preferences.dart';

class NotificationService {
  final FlutterLocalNotificationsPlugin _plugin =
      FlutterLocalNotificationsPlugin();
  static const int _realtimeReconnectId = 30;
  static const int _realtimeRestoredId = 31;
  static const Duration _realtimeReconnectCooldown = Duration(minutes: 5);

  bool _permissionRequested = false;
  final Set<int> _activeNotifications = <int>{};
  final Set<String> _vibrationKeys = <String>{};
  final Map<int, DateTime> _lastNotificationAt = <int, DateTime>{};

  Future<void> initialize() async {
    const android = AndroidInitializationSettings('@drawable/sheguard_icon');
    const settings = InitializationSettings(android: android);
    await _plugin.initialize(settings);
  }

  Future<void> requestPermission() async {
    if (_permissionRequested) return;
    _permissionRequested = true;
    try {
      await Permission.notification.request();
    } catch (_) {
      // Notification permission failures must never break emergency flows.
    }
  }

  Future<void> show({
    required String title,
    required String body,
    int id = 1,
    bool onlyAlertOnce = false,
    bool enableVibration = true,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    if (!(prefs.getBool('notifications_enabled') ?? true)) return;
    await requestPermission();
    const android = AndroidNotificationDetails(
      'sheguard_alerts',
      'SheGuard Alerts',
      channelDescription: 'Safety, GPS, SOS, and backend status alerts.',
      importance: Importance.high,
      priority: Priority.high,
    );
    final details = NotificationDetails(
      android: AndroidNotificationDetails(
        android.channelId,
        android.channelName,
        channelDescription: android.channelDescription,
        importance: android.importance,
        priority: android.priority,
        onlyAlertOnce: onlyAlertOnce,
        enableVibration: enableVibration,
      ),
    );
    try {
      await _plugin.show(id, title, body, details);
      _activeNotifications.add(id);
      _lastNotificationAt[id] = DateTime.now();
      debugPrint('SheGuard notification shown: $title');
    } catch (_) {
      // Keep SOS/GPS flows alive even if local notification delivery fails.
    }
  }

  Future<void> cancel(int id) async {
    try {
      await _plugin.cancel(id);
    } catch (_) {
      // Notification cancellation must never break emergency flows.
    } finally {
      _activeNotifications.remove(id);
    }
  }

  Future<void> showFullScreenEmergency({
    required String title,
    required String body,
    String? vibrationKey,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    if (!(prefs.getBool('notifications_enabled') ?? true)) return;
    await requestPermission();
    const android = AndroidNotificationDetails(
      'sheguard_emergency',
      'SheGuard Emergency',
      channelDescription: 'Critical auto SOS and emergency incident alerts.',
      importance: Importance.max,
      priority: Priority.max,
      category: AndroidNotificationCategory.alarm,
      fullScreenIntent: true,
      ongoing: true,
      autoCancel: false,
      visibility: NotificationVisibility.public,
    );
    const details = NotificationDetails(android: android);
    try {
      await _plugin.show(99, title, body, details);
      if (vibrationKey != null) {
        await vibrateOnce(vibrationKey);
      }
      debugPrint('SheGuard full-screen emergency notification shown: $title');
    } catch (_) {
      // Emergency activation must continue if the OS blocks full-screen alerts.
    }
  }

  Future<void> showRealtimeDisconnected() {
    return showRealtimeReconnectDebounced();
  }

  Future<void> showRealtimeReconnectDebounced() async {
    final now = DateTime.now();
    final last = _lastNotificationAt[_realtimeReconnectId];
    if (_activeNotifications.contains(_realtimeReconnectId)) {
      debugPrint('SheGuard realtime reconnect notification already active.');
      return;
    }
    if (last != null && now.difference(last) < _realtimeReconnectCooldown) {
      debugPrint('SheGuard realtime reconnect notification cooldown active.');
      return;
    }
    await show(
      id: _realtimeReconnectId,
      title: 'Realtime emergency link reconnecting',
      body: 'SheGuard is restoring live incident updates.',
      onlyAlertOnce: true,
      enableVibration: true,
    );
  }

  Future<void> showRealtimeRestored() async {
    await cancel(_realtimeReconnectId);
    await show(
      id: _realtimeRestoredId,
      title: 'Realtime emergency link restored',
      body: 'SheGuard is receiving live emergency events again.',
      onlyAlertOnce: true,
      enableVibration: false,
    );
  }

  Future<void> showAutoSosActivated(String incidentType) {
    return showAutoSosActivatedForEvent(incidentType: incidentType);
  }

  Future<void> showAutoSosActivatedForEvent({
    required String incidentType,
    String? eventId,
  }) {
    return showFullScreenEmergency(
      title: 'AUTO SOS ACTIVATED',
      body: 'AI CCTV reported $incidentType. Live tracking is active.',
      vibrationKey: eventId == null ? 'auto-sos' : 'auto-sos-$eventId',
    );
  }

  Future<void> vibrateOnce(String key) async {
    if (_vibrationKeys.contains(key)) return;
    _vibrationKeys.add(key);
    try {
      await HapticFeedback.heavyImpact();
      await HapticFeedback.vibrate();
    } catch (_) {
      // Haptic availability varies by platform and device state.
    }
  }

  Future<void> showSosActivated({required bool silent}) {
    return show(
      id: 4,
      title: 'HELP ALERT SENT',
      body: 'Your emergency contacts have been alerted.',
    );
  }

  Future<void> showLiveTrackingActive() {
    return show(
      id: 6,
      title: 'Live GPS tracking active',
      body: 'SheGuard is sharing live emergency location updates.',
    );
  }

  Future<void> showEmergencyModeEnabled({required bool silent}) {
    return show(
      id: 7,
      title: 'Emergency mode enabled',
      body: silent
          ? 'Silent emergency mode is active.'
          : 'SheGuard emergency protection is active.',
    );
  }

  Future<void> showSilentEmergencyEnabled() {
    return show(
      id: 8,
      title: 'HELP ALERT SENT',
      body: 'Your emergency contacts have been alerted quietly.',
    );
  }
}
