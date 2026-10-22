/// Deep-link router — parses the `type` + `target_id` from a notification
/// payload and returns the route path the app should navigate to.
///
/// Brief §5.4 + §7:
/// - timetable_change → /home/tab-timetable
/// - attendance_open → /home/tab-scan
/// - announcement → /announcement (with announcement_id in path)
/// - new_material → /home/tab-materials
/// - absence_warning → /attendance-summary (Phase 4 screen)
/// - grade_published → /grades (Phase 2 — not implemented yet)
/// - excuse_reviewed → /excuses (Phase 2)
/// - request_updated → /requests (Phase 2)
class DeepLinkRouter {
  DeepLinkRouter._();

  /// Returns the route to navigate to, or null if the type is unknown.
  static String? routeFor({
    required String type,
    String? targetId,
    Map<String, dynamic>? data,
  }) {
    switch (type) {
      case 'timetable_change':
        return '/home/tab-timetable';
      case 'attendance_open':
        return '/home/tab-scan';
      case 'announcement':
        if (data?['announcement_id'] != null) {
          return '/announcement/${data!['announcement_id']}';
        }
        return '/home/tab-materials'; // fallback
      case 'new_material':
        return '/home/tab-materials';
      case 'absence_warning':
        return '/attendance-summary';
      case 'grade_published':
        return '/grades';
      case 'excuse_reviewed':
        return '/excuses';
      case 'request_updated':
        return '/requests';
      default:
        return null;
    }
  }

  /// Parse the data payload that comes from an FCM message.
  /// FCM sends `data` as Map<String, String>, so values are strings.
  static ({String type, String? targetId, Map<String, dynamic> data}) parse(
    Map<String, dynamic>? payload,
  ) {
    if (payload == null) {
      return (type: '', targetId: null, data: {});
    }
    final type = (payload['type'] as String?) ?? '';
    final targetId = payload['target_id'] as String?;
    return (type: type, targetId: targetId, data: payload);
  }
}
