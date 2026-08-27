import 'dart:async';
import 'dart:convert';

import 'package:battery_plus/battery_plus.dart';
import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/app_config.dart';
import '../models/location_update.dart';
import 'api_service.dart';
import 'foreground_tracking_service.dart';

class LocationService {
  LocationService(this._api, {ForegroundTrackingService? foregroundTracking})
      : _foregroundTracking = foregroundTracking ?? ForegroundTrackingService();

  static const _offlineTrackingQueueKey = 'offline_tracking_queue';
  static const _gpsTimeout = Duration(seconds: 60);

  final ApiService _api;
  final ForegroundTrackingService _foregroundTracking;
  final Battery _battery = Battery();
  StreamSubscription<Position>? _subscription;
  StreamSubscription<Map<String, dynamic>?>? _foregroundUpdateSubscription;
  StreamSubscription<Map<String, dynamic>?>? _foregroundErrorSubscription;
  StreamSubscription<Map<String, dynamic>?>? _foregroundLogSubscription;

  Future<bool> ensurePermission() async {
    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) return false;

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }

    return permission == LocationPermission.always ||
        permission == LocationPermission.whileInUse;
  }

  Future<LocationUpdate> currentUpdate(int userId) async {
    final allowed = await ensurePermission();
    if (!allowed) {
      throw const ApiException(
          'GPS permission is required for live safety tracking.');
    }

    final position = await Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.bestForNavigation,
        timeLimit: _gpsTimeout,
      ),
    );
    return LocationUpdate(
      userId: userId,
      latitude: position.latitude,
      longitude: position.longitude,
      speed: position.speed.isFinite ? position.speed : 0,
      heading: position.heading.isFinite ? position.heading : null,
      accuracy: position.accuracy,
      battery: await _batteryLevel(),
      timestamp: DateTime.now(),
    );
  }

  Future<LocationUpdate?> lastKnownUpdate(int userId) async {
    final allowed = await ensurePermission();
    if (!allowed) return null;

    final position = await Geolocator.getLastKnownPosition();
    if (position == null) return null;
    return LocationUpdate(
      userId: userId,
      latitude: position.latitude,
      longitude: position.longitude,
      speed: position.speed.isFinite ? position.speed : 0,
      heading: position.heading.isFinite ? position.heading : null,
      accuracy: position.accuracy,
      battery: await _batteryLevel(),
      timestamp: DateTime.now(),
    );
  }

  Future<LocationUpdate> sendCurrentLocation(int userId,
      {String? sessionId}) async {
    final update = await currentUpdate(userId);
    final enriched = LocationUpdate(
      userId: update.userId,
      sessionId: sessionId,
      latitude: update.latitude,
      longitude: update.longitude,
      speed: update.speed,
      heading: update.heading,
      accuracy: update.accuracy,
      battery: update.battery,
      timestamp: update.timestamp,
    );
    if (sessionId == null) {
      await _api.postJson('/location/update', enriched.toJson());
    } else {
      await _postTrackingUpdate(enriched);
    }
    return enriched;
  }

  Future<Map<String, dynamic>> startTrackingSession({
    required int userId,
    required String sessionId,
    LocationUpdate? initialLocation,
  }) async {
    final payload = <String, dynamic>{
      'user_id': userId,
      'session_id': sessionId,
      if (initialLocation != null) ...initialLocation.toJson(),
    };
    return _api.postJson('/tracking/start', payload);
  }

  Future<LocationUpdate?> fetchLiveLocation(int userId) async {
    final json = await _api.getJson('/location/live/$userId');
    return LocationUpdate.fromJson(json);
  }

  void startTracking({
    required int userId,
    String? sessionId,
    required void Function(LocationUpdate update) onUpdate,
    required void Function(Object error) onError,
  }) {
    _subscription?.cancel();
    _foregroundUpdateSubscription?.cancel();
    _foregroundErrorSubscription?.cancel();
    _foregroundLogSubscription?.cancel();

    if (sessionId != null) {
      debugPrint(
          '[TRACKING] Starting resilient foreground SOS tracking: $sessionId');
      unawaited(_api.resolveLocalBaseUrl().then((baseUrl) {
        debugPrint('[NETWORK] Foreground tracking backend: $baseUrl');
        return _foregroundTracking.startEmergencyTracking(
          userId: userId,
          sessionId: sessionId,
          baseUrl: baseUrl,
        );
      }).catchError((Object error) {
        debugPrint(
          '[NETWORK] Could not start foreground tracking backend sync: $error',
        );
        onError(error);
      }));
      _foregroundUpdateSubscription =
          _foregroundTracking.onTrackingUpdate().listen((event) {
        if (event == null) return;
        try {
          final update = LocationUpdate(
            userId: (event['user_id'] as num).toInt(),
            sessionId: event['session_id']?.toString(),
            latitude: (event['latitude'] as num).toDouble(),
            longitude: (event['longitude'] as num).toDouble(),
            speed: (event['speed'] as num?)?.toDouble() ?? 0,
            heading: (event['heading'] as num?)?.toDouble(),
            accuracy: (event['accuracy'] as num?)?.toDouble(),
            battery: (event['battery'] as num?)?.toInt(),
            timestamp: event['timestamp'] == null
                ? DateTime.now()
                : DateTime.tryParse(event['timestamp'].toString()) ??
                    DateTime.now(),
          );
          onUpdate(update);
        } catch (error) {
          debugPrint(
              '[TRACKING] Could not parse foreground tracking update: $error');
        }
      });
      _foregroundErrorSubscription =
          _foregroundTracking.onTrackingError().listen((event) {
        if (event == null) return;
        debugPrint(
          '[GPS] Foreground tracking retry ${event['retry_count']}: '
          '${event['message']}',
        );
        onError(event);
      });
      _foregroundLogSubscription =
          _foregroundTracking.onTrackingLog().listen((event) {
        if (event != null) {
          debugPrint('[TRACKING] ${event['message']}');
        }
      });
      return;
    }

    final settings = AndroidSettings(
      accuracy: LocationAccuracy.bestForNavigation,
      distanceFilter: 0,
      intervalDuration: AppConfig.trackingInterval,
      foregroundNotificationConfig: const ForegroundNotificationConfig(
        notificationTitle: 'SheGuard safety tracking',
        notificationText:
            'Live GPS updates are active for emergency protection.',
        enableWakeLock: true,
      ),
    );
    _subscription = Geolocator.getPositionStream(locationSettings: settings)
        .listen((position) async {
      try {
        final update = LocationUpdate(
          userId: userId,
          sessionId: sessionId,
          latitude: position.latitude,
          longitude: position.longitude,
          speed: position.speed.isFinite ? position.speed : 0,
          heading: position.heading.isFinite ? position.heading : null,
          accuracy: position.accuracy,
          battery: await _batteryLevel(),
          timestamp: DateTime.now(),
        );
        if (sessionId != null) {
          await _postTrackingUpdate(update);
          await syncQueuedTrackingUpdates();
        } else {
          await _api.postJson('/location/update', update.toJson());
        }
        onUpdate(update);
      } catch (error) {
        onError(error);
      }
    }, onError: onError);
  }

  void stopTracking() {
    _subscription?.cancel();
    _subscription = null;
    _foregroundUpdateSubscription?.cancel();
    _foregroundUpdateSubscription = null;
    _foregroundErrorSubscription?.cancel();
    _foregroundErrorSubscription = null;
    _foregroundLogSubscription?.cancel();
    _foregroundLogSubscription = null;
    _foregroundTracking.stopEmergencyTracking();
  }

  Future<void> _postTrackingUpdate(LocationUpdate update) async {
    if (update.sessionId == null) return;
    final payload = update.toJson();
    try {
      await _api.postJson('/tracking/update', payload);
    } catch (error) {
      await _queueTrackingUpdate(payload);
      debugPrint('SheGuard queued offline tracking update: $error');
      rethrow;
    }
  }

  Future<void> _queueTrackingUpdate(Map<String, dynamic> payload) async {
    final prefs = await SharedPreferences.getInstance();
    final queue = prefs.getStringList(_offlineTrackingQueueKey) ?? const [];
    await prefs.setStringList(
      _offlineTrackingQueueKey,
      [...queue, jsonEncode(payload)].take(200).toList(),
    );
  }

  Future<void> syncQueuedTrackingUpdates() async {
    final prefs = await SharedPreferences.getInstance();
    final queue = prefs.getStringList(_offlineTrackingQueueKey) ?? const [];
    if (queue.isEmpty) return;
    final remaining = <String>[];
    for (final raw in queue) {
      try {
        await _api.postJson(
          '/tracking/update',
          jsonDecode(raw) as Map<String, dynamic>,
        );
      } catch (_) {
        remaining.add(raw);
      }
    }
    await prefs.setStringList(_offlineTrackingQueueKey, remaining);
    if (remaining.length != queue.length) {
      debugPrint(
          'SheGuard synced ${queue.length - remaining.length} queued tracking updates.');
    }
  }

  Future<int?> _batteryLevel() async {
    try {
      return _battery.batteryLevel;
    } catch (_) {
      return null;
    }
  }
}
