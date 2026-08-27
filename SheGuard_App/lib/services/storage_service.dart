import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../models/user.dart';

class StorageService {
  static const _storage = FlutterSecureStorage();
  static const _userKey = 'sheguard_user';
  static const _tokenKey = 'sheguard_auth_token';

  Future<void> saveSession(
    User user, {
    String? token,
    bool preserveToken = false,
  }) async {
    await _storage.write(key: _userKey, value: jsonEncode(user.toJson()));
    if (token != null) {
      await _storage.write(key: _tokenKey, value: token);
    } else if (!preserveToken) {
      await _storage.delete(key: _tokenKey);
    }
  }

  Future<User?> readUser() async {
    final raw = await _storage.read(key: _userKey);
    if (raw == null) return null;
    try {
      return User.fromJson(jsonDecode(raw) as Map<String, dynamic>);
    } catch (_) {
      await clearSession();
      return null;
    }
  }

  Future<String?> readToken() => _storage.read(key: _tokenKey);

  Future<void> clearSession() async {
    await _storage.delete(key: _userKey);
    await _storage.delete(key: _tokenKey);
  }
}
