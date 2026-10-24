/// Centralized app configuration. Endpoints, timeouts, pagination defaults.
class AppConfig {
  const AppConfig._();

  /// API base URL. Override via --dart-define=API_BASE_URL=... for prod.
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000', // Android emulator → host loopback
  );

  static const String apiPrefix = '/api/v1';
  static String get apiOrigin => apiBaseUrl;
  static String get apiFullBase => '$apiBaseUrl$apiPrefix';

  static const Duration connectTimeout = Duration(seconds: 10);
  static const Duration receiveTimeout = Duration(seconds: 30);
  static const Duration sendTimeout = Duration(seconds: 30);

  static const int defaultPageLimit = 20;
  static const int maxCacheAgeMinutes = 60; // for stale-while-revalidate
  static const int lectureReminderMinutesBefore = 15;
}
