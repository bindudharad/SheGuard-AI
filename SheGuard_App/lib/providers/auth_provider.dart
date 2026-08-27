import 'package:flutter/foundation.dart';

import '../models/user.dart';
import '../services/auth_service.dart';

class AuthProvider extends ChangeNotifier {
  AuthProvider(this._authService);

  final AuthService _authService;

  User? user;
  bool loading = true;
  String? error;

  bool get isAuthenticated => user != null;

  Future<void> restore() async {
    loading = true;
    notifyListeners();
    try {
      await _authService.restoreToken();
      user = await _authService.restoreSession();
      if (user != null) {
        user = await _authService.fetchProfile(user!.userId);
      }
      error = null;
    } catch (e) {
      error = e.toString();
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<bool> login(String phoneNumber, String password) async {
    return _run(() async {
      user = await _authService.login(
        phoneNumber: phoneNumber,
        password: password,
      );
    });
  }

  Future<bool> register({
    required String fullName,
    required String phoneNumber,
    required String password,
    String? profilePhoto,
  }) async {
    return _run(() async {
      user = await _authService.register(
        fullName: fullName,
        phoneNumber: phoneNumber,
        password: password,
        profilePhoto: profilePhoto,
      );
    });
  }

  Future<void> logout() async {
    await _authService.logout();
    user = null;
    notifyListeners();
  }

  Future<bool> _run(Future<void> Function() action) async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      await action();
      return true;
    } catch (e) {
      error = e.toString();
      return false;
    } finally {
      loading = false;
      notifyListeners();
    }
  }
}
