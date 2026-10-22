/// All route paths. Kept in one place so deep links from notifications can
/// reference them by name.
class Routes {
  Routes._();

  static const String login = '/login';
  static const String changePassword = '/change-password';
  static const String home = '/home';

  // Bottom nav targets (inside HomeShell):
  static const String homeTab = '/home/tab-home';
  static const String timetable = '/home/tab-timetable';
  static const String scan = '/home/tab-scan';
  static const String materials = '/home/tab-materials';
  static const String more = '/home/tab-more';

  // Sub-pages:
  static const String announcementDetail = '/announcement';
  static const String notifications = '/notifications';
  static const String profile = '/profile';
  static const String settings = '/settings';
}
