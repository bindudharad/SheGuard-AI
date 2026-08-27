class ApiConfig {
  // Base URL for the SheGuard backend API.
  // Configured via --dart-define=SHEGUARD_API_BASE_URL=http://192.168.1.3:8000
  // or via environment variable at build time.
  static const String baseUrl = String.fromEnvironment(
    'SHEGUARD_API_BASE_URL',
    defaultValue: '', // Must be provided at build time
  );

  // Public tracking base URL for shareable tracking links
  // Configured via --dart-define=SHEGUARD_PUBLIC_TRACKING_BASE_URL=http://192.168.1.3:8000
  static const String publicTrackingBaseUrl = String.fromEnvironment(
    'SHEGUARD_PUBLIC_TRACKING_BASE_URL',
    defaultValue: '',
  );
}