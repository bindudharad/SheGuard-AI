import '../config/api_config.dart';

class AppConfig {
  static const String baseUrl = ApiConfig.baseUrl;

  static const Duration apiTimeout = Duration(
    seconds: 120,
  );

  static const Duration trackingInterval = Duration(
    seconds: 5,
  );
}