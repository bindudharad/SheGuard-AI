import 'dart:async';
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:sensors_plus/sensors_plus.dart';

class MotionProtectionService {
  static const _cooldown = Duration(seconds: 45);
  static const _sampling = Duration(milliseconds: 160);
  static const _fallImpactThreshold = 29.0;
  static const _stillnessThreshold = 1.8;
  static const _stillnessWindow = Duration(seconds: 3);

  StreamSubscription<AccelerometerEvent>? _accelerometerSub;
  StreamSubscription<UserAccelerometerEvent>? _userAccelerometerSub;
  VoidCallback? _onShake;
  VoidCallback? _onFall;
  DateTime? _lastTriggerAt;
  DateTime? _impactAt;
  int _shakeHits = 0;
  double _lastUserMagnitude = 0;
  bool _enabled = false;

  void start({
    required bool shakeEnabled,
    required bool fallDetectionEnabled,
    required double shakeSensitivity,
    required VoidCallback onShake,
    required VoidCallback onFall,
  }) {
    stop();
    if (!shakeEnabled && !fallDetectionEnabled) return;
    _enabled = true;
    _onShake = onShake;
    _onFall = onFall;
    final shakeThreshold = 18.0 - (shakeSensitivity.clamp(0, 1) * 8.0);

    _userAccelerometerSub = userAccelerometerEventStream(
      samplingPeriod: _sampling,
    ).listen((event) {
      if (!_enabled || !shakeEnabled) return;
      final magnitude = _magnitude(event.x, event.y, event.z);
      _lastUserMagnitude = magnitude;
      if (magnitude >= shakeThreshold) {
        _shakeHits += 1;
      } else {
        _shakeHits = max(0, _shakeHits - 1);
      }
      if (_shakeHits >= 4 && _canTrigger()) {
        _shakeHits = 0;
        _lastTriggerAt = DateTime.now();
        debugPrint('SheGuard aggressive shake detected: $magnitude');
        _onShake?.call();
      }
    }, onError: (error) {
      debugPrint('SheGuard shake detection error: $error');
    });

    _accelerometerSub = accelerometerEventStream(
      samplingPeriod: _sampling,
    ).listen((event) {
      if (!_enabled || !fallDetectionEnabled) return;
      final magnitude = _magnitude(event.x, event.y, event.z);
      final now = DateTime.now();

      if (magnitude >= _fallImpactThreshold) {
        _impactAt = now;
        debugPrint('SheGuard fall impact candidate: $magnitude');
        return;
      }

      final impactAt = _impactAt;
      if (impactAt == null) return;
      if (now.difference(impactAt) > _stillnessWindow) {
        _impactAt = null;
        return;
      }
      if (_lastUserMagnitude <= _stillnessThreshold && _canTrigger()) {
        _impactAt = null;
        _lastTriggerAt = now;
        debugPrint('SheGuard fall detected after impact and stillness.');
        _onFall?.call();
      }
    }, onError: (error) {
      debugPrint('SheGuard fall detection error: $error');
    });
  }

  void stop() {
    _enabled = false;
    _accelerometerSub?.cancel();
    _userAccelerometerSub?.cancel();
    _accelerometerSub = null;
    _userAccelerometerSub = null;
    _impactAt = null;
    _shakeHits = 0;
  }

  bool _canTrigger() {
    final last = _lastTriggerAt;
    return last == null || DateTime.now().difference(last) > _cooldown;
  }

  double _magnitude(double x, double y, double z) {
    return sqrt(x * x + y * y + z * z);
  }
}
