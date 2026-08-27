import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

class SettingsProvider extends ChangeNotifier {
  static const _notificationsKey = 'notifications_enabled';
  static const _silentKey = 'silent_mode_enabled';
  static const _privacyKey = 'privacy_guard_enabled';
  static const _trackingKey = 'tracking_enabled';
  static const _shakeKey = 'shake_sos_enabled';
  static const _fallKey = 'fall_detection_enabled';
  static const _shakeSensitivityKey = 'shake_sensitivity';
  static const _autoCallKey = 'auto_emergency_call_enabled';
  static const _sirenKey = 'emergency_siren_enabled';
  static const _developerModeKey = 'developer_mode_enabled';

  bool notificationsEnabled = true;
  bool silentModeEnabled = false;
  bool privacyGuardEnabled = true;
  bool trackingEnabled = true;
  bool shakeSosEnabled = true;
  bool fallDetectionEnabled = true;
  bool autoEmergencyCallEnabled = true;
  bool emergencySirenEnabled = false;
  bool developerModeEnabled = false;
  double shakeSensitivity = .65;

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    notificationsEnabled = prefs.getBool(_notificationsKey) ?? true;
    silentModeEnabled = prefs.getBool(_silentKey) ?? false;
    privacyGuardEnabled = prefs.getBool(_privacyKey) ?? true;
    trackingEnabled = prefs.getBool(_trackingKey) ?? true;
    shakeSosEnabled = prefs.getBool(_shakeKey) ?? true;
    fallDetectionEnabled = prefs.getBool(_fallKey) ?? true;
    autoEmergencyCallEnabled = prefs.getBool(_autoCallKey) ?? true;
    emergencySirenEnabled = prefs.getBool(_sirenKey) ?? false;
    developerModeEnabled = prefs.getBool(_developerModeKey) ?? false;
    shakeSensitivity = prefs.getDouble(_shakeSensitivityKey) ?? .65;
    notifyListeners();
  }

  Future<void> setNotifications(bool value) async {
    notificationsEnabled = value;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_notificationsKey, value);
    notifyListeners();
  }

  Future<void> setSilentMode(bool value) async {
    silentModeEnabled = value;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_silentKey, value);
    notifyListeners();
  }

  Future<void> setPrivacyGuard(bool value) async {
    privacyGuardEnabled = value;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_privacyKey, value);
    notifyListeners();
  }

  Future<void> setTracking(bool value) async {
    trackingEnabled = value;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_trackingKey, value);
    notifyListeners();
  }

  Future<void> setShakeSos(bool value) async {
    shakeSosEnabled = value;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_shakeKey, value);
    notifyListeners();
  }

  Future<void> setFallDetection(bool value) async {
    fallDetectionEnabled = value;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_fallKey, value);
    notifyListeners();
  }

  Future<void> setShakeSensitivity(double value) async {
    shakeSensitivity = value.clamp(0, 1);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble(_shakeSensitivityKey, shakeSensitivity);
    notifyListeners();
  }

  Future<void> setAutoEmergencyCalling(bool value) async {
    autoEmergencyCallEnabled = value;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_autoCallKey, value);
    notifyListeners();
  }

  Future<void> setEmergencySiren(bool value) async {
    emergencySirenEnabled = value;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_sirenKey, value);
    notifyListeners();
  }

  Future<void> setDeveloperMode(bool value) async {
    developerModeEnabled = value;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_developerModeKey, value);
    notifyListeners();
  }

  Future<void> toggleDeveloperMode() {
    return setDeveloperMode(!developerModeEnabled);
  }
}
