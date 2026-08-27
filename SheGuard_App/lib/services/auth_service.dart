import '../models/user.dart';
import 'api_service.dart';
import 'storage_service.dart';

class AuthService {
  AuthService(this._api, this._storage);

  final ApiService _api;
  final StorageService _storage;

  Future<User> register({
    required String fullName,
    required String phoneNumber,
    required String password,
    String? profilePhoto,
  }) async {
    final json = await _api.postJson('/register', {
      'full_name': fullName,
      'phone_number': phoneNumber,
      'password': password,
      'profile_photo': profilePhoto,
    });
    final user = User.fromJson(json);
    final token = _extractToken(json);
    _api.setAuthToken(token);
    await _storage.saveSession(user, token: token);
    return user;
  }

  Future<User> login({
    required String phoneNumber,
    required String password,
  }) async {
    final json = await _api.postJson('/login', {
      'phone_number': phoneNumber,
      'password': password,
    });
    final user = User.fromJson(json);
    final token = _extractToken(json);
    _api.setAuthToken(token);
    await _storage.saveSession(user, token: token);
    return user;
  }

  Future<User?> restoreSession() => _storage.readUser();

  Future<void> restoreToken() async {
    _api.setAuthToken(await _storage.readToken());
  }

  Future<User> fetchProfile(int userId) async {
    final json = await _api.getJson('/profile/$userId');
    final user = User.fromJson(json);
    await _storage.saveSession(user, preserveToken: true);
    return user;
  }

  Future<void> logout() async {
    _api.setAuthToken(null);
    await _storage.clearSession();
  }

  String? _extractToken(Map<String, dynamic> json) {
    return (json['access_token'] ?? json['token']) as String?;
  }
}
