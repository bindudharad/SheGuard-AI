import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

class EmergencySirenService {
  Timer? _timer;

  bool get active => _timer != null;

  Future<void> start({bool enabled = true}) async {
    if (!enabled || active) return;
    debugPrint('SheGuard emergency siren started.');
    await _pulse();
    _timer = Timer.periodic(const Duration(milliseconds: 1400), (_) {
      _pulse();
    });
  }

  Future<void> stop() async {
    _timer?.cancel();
    _timer = null;
    debugPrint('SheGuard emergency siren stopped.');
  }

  Future<void> _pulse() async {
    try {
      await SystemSound.play(SystemSoundType.alert);
      await HapticFeedback.vibrate();
    } catch (error) {
      debugPrint('SheGuard siren pulse failed: $error');
    }
  }
}
