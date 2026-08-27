import 'dart:async';
import 'dart:convert';
import 'dart:ui';

import 'package:battery_plus/battery_plus.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_background_service/flutter_background_service.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;
import 'package:permission_handler/permission_handler.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:wakelock_plus/wakelock_plus.dart';

import '../core/app_config.dart';
import '../config/api_config.dart';

class ForegroundTrackingService {
  static const _offlineTrackingQueueKey = 'offline_tracking_queue';
  static const _gpsTimeout = Duration(seconds: 60);
  static const _retryDelay = Duration(seconds: 3);

  final FlutterBackgroundService _service = FlutterBackgroundService();

  Future<void> initialize() async {
    await _service.configure(
      androidConfiguration: AndroidConfiguration(
        onStart: trackingServiceOnStart,
        autoStart: false,
        isForegroundMode: true,
        foregroundServiceNotificationId: 881,
        initialNotificationTitle: 'SheGuard live tracking',
        initialNotificationContent: 'Emergency GPS tracking is ready.',
      ),
      iosConfiguration: IosConfiguration(
        autoStart: false,
        onForeground: trackingServiceOnStart,
      ),
    );
  }

  Stream<Map<String, dynamic>?> onTrackingUpdate() {
    return _service.on('trackingUpdate');
  }

  Stream<Map<String, dynamic>?> onTrackingError() {
    return _service.on('trackingError');
  }

  Stream<Map<String, dynamic>?> onTrackingLog() {
    return _service.on('trackingLog');
  }

  Future<void> startEmergencyTracking({
    required int userId,
    required String sessionId,
    required String baseUrl,
  }) async {
    await _requestBatteryOptimizationBypass();
    await WakelockPlus.enable();
    final running = await _service.isRunning();
    if (!running) {
      await _service.startService();
    }
    _service.invoke('startTracking', {
      'user_id': userId,
      'session_id': sessionId,
      'base_url': baseUrl,
      'interval_ms': AppConfig.trackingInterval.inMilliseconds,
    });
  }

  Future<void> startEmergencyNotification() async {
    final running = await _service.isRunning();
    if (!running) {
      await _service.startService();
    }
  }

  Future<void> stopEmergencyNotification() => stopEmergencyTracking();

  Future<void> stopEmergencyTracking() async {
    _service.invoke('stopTracking');
    await WakelockPlus.disable();
  }

  Future<void> _requestBatteryOptimizationBypass() async {
    try {
      final status = await Permission.ignoreBatteryOptimizations.status;
      if (!status.isGranted) {
        await Permission.ignoreBatteryOptimizations.request();
      }
    } catch (error) {
      debugPrint('SheGuard battery optimization prompt unavailable: $error');
    }
  }
}

@pragma('vm:entry-point')
void trackingServiceOnStart(ServiceInstance service) async {
  DartPluginRegistrant.ensureInitialized();

  final battery = Battery();
  Timer? loopTimer;
  bool sosActive = false;
  bool requestInProgress = false;
  int userId = 0;
  String? sessionId;
  String baseUrl = ApiConfig.baseUrl;
  Duration interval = AppConfig.trackingInterval;
  int retryCount = 0;
  DateTime? firstFailureAt;
  String? lastForegroundMessage;
  DateTime? lastForegroundUpdateAt;

  Future<void> log(String message, [Map<String, dynamic>? extra]) async {
    final payload = {
      'message': message,
      'timestamp': DateTime.now().toUtc().toIso8601String(),
      if (extra != null) ...extra,
    };
    debugPrint('SheGuard tracking service: $payload');
    service.invoke('trackingLog', payload);
    if (service is AndroidServiceInstance) {
      final now = DateTime.now();
      final important = message.contains('started') ||
          message.contains('stopped') ||
          message.contains('No local backend');
      final shouldUpdate = important ||
          lastForegroundMessage != message &&
              (lastForegroundUpdateAt == null ||
                  now.difference(lastForegroundUpdateAt!) >
                      const Duration(seconds: 20));
      if (shouldUpdate) {
        lastForegroundMessage = message;
        lastForegroundUpdateAt = now;
        service.setForegroundNotificationInfo(
          title: 'SheGuard live tracking',
          content: message,
        );
      }
    }
  }

  Future<int?> batteryLevel() async {
    try {
      return battery.batteryLevel;
    } catch (_) {
      return null;
    }
  }

  Future<void> queueUpdate(Map<String, dynamic> payload) async {
    final prefs = await SharedPreferences.getInstance();
    final queue = prefs.getStringList(
            ForegroundTrackingService._offlineTrackingQueueKey) ??
        const [];
    await prefs.setStringList(
      ForegroundTrackingService._offlineTrackingQueueKey,
      [...queue, jsonEncode(payload)].take(300).toList(),
    );
  }

  Future<void> syncQueuedUpdates() async {
    final prefs = await SharedPreferences.getInstance();
    final queue = prefs.getStringList(
            ForegroundTrackingService._offlineTrackingQueueKey) ??
        const [];
    if (queue.isEmpty) return;
    final remaining = <String>[];
    var synced = 0;
    for (final raw in queue) {
      try {
        final payload = jsonDecode(raw) as Map<String, dynamic>;
        final response = await http
            .post(
              Uri.parse('$baseUrl/tracking/update'),
              headers: {'Content-Type': 'application/json'},
              body: jsonEncode(payload),
            )
            .timeout(const Duration(seconds: 60));
        if (response.statusCode >= 200 && response.statusCode < 300) {
          synced += 1;
        } else {
          remaining.add(raw);
        }
      } catch (_) {
        remaining.add(raw);
      }
    }
    await prefs.setStringList(
        ForegroundTrackingService._offlineTrackingQueueKey, remaining);
    if (synced > 0) {
      await log('Synced $synced queued GPS updates');
    }
  }

  Future<Position> fetchBestPosition() {
    return Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.bestForNavigation,
        timeLimit: ForegroundTrackingService._gpsTimeout,
      ),
    );
  }

  Future<void> uploadPosition(Position position) async {
    final sid = sessionId;
    if (sid == null || userId == 0) return;
    final payload = <String, dynamic>{
      'user_id': userId,
      'session_id': sid,
      'latitude': position.latitude,
      'longitude': position.longitude,
      'speed': position.speed.isFinite ? position.speed : 0,
      'heading': position.heading.isFinite ? position.heading : null,
      'accuracy': position.accuracy,
      'battery': await batteryLevel(),
      'timestamp': DateTime.now().toUtc().toIso8601String(),
    };
    try {
      final response = await http
          .post(
            Uri.parse('$baseUrl/tracking/update'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(payload),
          )
          .timeout(const Duration(seconds: 60));
      await log('Backend upload result ${response.statusCode}', {
        'session_id': sid,
        'status_code': response.statusCode,
      });
      if (response.statusCode < 200 || response.statusCode >= 300) {
        await queueUpdate(payload);
        throw Exception('Backend returned ${response.statusCode}');
      }
      await syncQueuedUpdates();
      service.invoke('trackingUpdate', payload);
    } catch (error) {
      await queueUpdate(payload);
      rethrow;
    }
  }

  Future<void> tick() async {
    if (!sosActive || requestInProgress) return;
    requestInProgress = true;
    try {
      await log('GPS request started', {
        'session_id': sessionId,
        'retry_count': retryCount,
      });
      final position = await fetchBestPosition();
      await log('GPS success', {
        'latitude': position.latitude,
        'longitude': position.longitude,
        'accuracy': position.accuracy,
      });
      await uploadPosition(position);
      retryCount = 0;
      firstFailureAt = null;
    } on TimeoutException catch (error) {
      retryCount += 1;
      firstFailureAt ??= DateTime.now();
      await log('GPS timeout; retrying in 3 seconds', {
        'retry_count': retryCount,
        'error': error.toString(),
      });
      service.invoke('trackingError', {
        'type': 'timeout',
        'retry_count': retryCount,
        'message': error.toString(),
        'continuous_failure_seconds':
            DateTime.now().difference(firstFailureAt!).inSeconds,
      });
      Timer(ForegroundTrackingService._retryDelay, tick);
    } catch (error) {
      retryCount += 1;
      firstFailureAt ??= DateTime.now();
      await log('GPS/upload error; retrying in 3 seconds', {
        'retry_count': retryCount,
        'error': error.toString(),
      });
      service.invoke('trackingError', {
        'type': 'error',
        'retry_count': retryCount,
        'message': error.toString(),
        'continuous_failure_seconds':
            DateTime.now().difference(firstFailureAt!).inSeconds,
      });
      Timer(ForegroundTrackingService._retryDelay, tick);
    } finally {
      requestInProgress = false;
    }
  }

  service.on('startTracking').listen((event) async {
    final data = event ?? <String, dynamic>{};
    userId = (data['user_id'] as num).toInt();
    sessionId = data['session_id']?.toString();
    baseUrl = data['base_url']?.toString() ?? ApiConfig.baseUrl;
    if (baseUrl.trim().isEmpty) {
      await log('[NETWORK] No local backend URL available for GPS upload', {
        'session_id': sessionId,
      });
      return;
    }
    interval = Duration(
      milliseconds: (data['interval_ms'] as num?)?.toInt() ??
          AppConfig.trackingInterval.inMilliseconds,
    );
    sosActive = true;
    retryCount = 0;
    firstFailureAt = null;
    await WakelockPlus.enable();
    await log('SOS live tracking loop started', {
      'session_id': sessionId,
      'interval_seconds': interval.inSeconds,
    });
    loopTimer?.cancel();
    loopTimer = Timer.periodic(interval, (_) => tick());
    unawaited(tick());
  });

  service.on('stopTracking').listen((event) async {
    sosActive = false;
    retryCount = 0;
    firstFailureAt = null;
    loopTimer?.cancel();
    loopTimer = null;
    await WakelockPlus.disable();
    await log('SOS live tracking stopped by user');
    if (service is AndroidServiceInstance) {
      await service.stopSelf();
    }
  });

  if (service is AndroidServiceInstance) {
    service.on('setAsForeground').listen((event) {
      service.setAsForegroundService();
    });
  }
}
