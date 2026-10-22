/// Reminds the user about upcoming lectures.
///
/// Brief §13:
/// - 15 min before each lecture → local notification with title + body
/// - Daily "tomorrow's lectures" summary at 8pm local time
/// - Re-schedule after every timetable sync + after device reboot
library;

import 'package:flutter/foundation.dart';

import '../notifications/notification_service.dart';

class ReminderScheduler {
  ReminderScheduler._();

  /// Re-schedule all lecture reminders from the freshly-fetched timetable.
  ///
  /// `slots` is a list of {starts_at, course_name, room} entries for the next
  /// 7 days. The caller (TimetableRepository) passes these after a successful
  /// /timetable fetch.
  static Future<void> reschedule({
    required List<ReminderSlot> slots,
  }) async {
    await NotificationService.cancelAll();

    // Per-lecture reminders (15 min before)
    for (var i = 0; i < slots.length; i++) {
      final s = slots[i];
      final startsAt = s.startsAt;
      if (startsAt.isBefore(DateTime.now())) continue;
      final title = 'تذكير: محاضرة قادمة';
      final body = '${s.courseName} في ${_formatTime(startsAt)}${s.room != null ? ' — القاعة: ${s.room}' : ''}';
      await NotificationService.scheduleLectureReminder(
        id: i + 1, // unique id per slot
        startsAt: startsAt,
        title: title,
        body: body,
        minutesBefore: 15,
      );
    }

    // Daily "tomorrow's lectures" summary at 8pm
    final tomorrowSlots = slots.where((s) {
      final tomorrow = DateTime.now().add(const Duration(days: 1));
      return s.startsAt.year == tomorrow.year &&
          s.startsAt.month == tomorrow.month &&
          s.startsAt.day == tomorrow.day;
    }).toList();
    if (tomorrowSlots.isNotEmpty) {
      final summary = tomorrowSlots.map((s) {
        return '${_formatTime(s.startsAt)} — ${s.courseName}';
      }).join('\n');
      await NotificationService.scheduleTomorrowSummary(
        id: 999,
        title: 'محاضرات الغد',
        body: '$summary',
      );
    }
  }

  static String _formatTime(DateTime dt) {
    final h = dt.hour % 12 == 0 ? 12 : dt.hour % 12;
    final m = dt.minute.toString().padLeft(2, '0');
    final period = dt.hour < 12 ? 'ص' : 'م';
    return '$h:$m $period';
  }
}

class ReminderSlot {
  const ReminderSlot({
    required this.startsAt,
    required this.courseName,
    this.room,
  });
  final DateTime startsAt;
  final String courseName;
  final String? room;
}
