import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:timezone/data/latest_all.dart' as tz;
import 'package:timezone/timezone.dart' as tz;

/// Notification setup: FCM for remote events + local scheduled reminders
/// (15 min before lecture, "tomorrow's lectures" summary).
///
/// Phase 5 wires the full pipeline (token registration, deep links).
/// This scaffold initializes the channels + timezone data.
class NotificationService {
  NotificationService._();

  static final FlutterLocalNotificationsPlugin _local =
      FlutterLocalNotificationsPlugin();

  static bool _initialized = false;

  static Future<void> init() async {
    if (_initialized) return;
    tz.initializeTimeZones();
    // Use Asia/Baghdad for reminders (UTC+3, no DST). Fallback to UTC if missing.
    try {
      tz.setLocalLocation(tz.getLocation('Asia/Baghdad'));
    } catch (_) {
      // Already set to UTC by default.
    }

    const androidInit = AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosInit = DarwinInitializationSettings(
      requestAlertPermission: false,
      requestBadgePermission: false,
      requestSoundPermission: false,
    );
    await _local.initialize(
      const InitializationSettings(android: androidInit, iOS: iosInit),
    );

    // Android channel for academic reminders
    if (await _local
            .resolvePlatformSpecificImplementation<
                AndroidFlutterLocalNotificationsPlugin>()
            ?.createNotificationChannel(_remindersChannel) ==
        false) {
      // already exists
    }

    _initialized = true;
  }

  static const _remindersChannel = AndroidNotificationChannel(
    'csit_reminders',
    'تذكيرات الكلية',
    description: 'تذكير قبل المحاضرات وملخص محاضرات الغد',
    importance: Importance.high,
  );

  /// Request notification permission on Android 13+ / iOS.
  /// Called only AFTER explaining why (per brief §13).
  static Future<void> requestPermissions() async {
    await _local
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.requestNotificationsPermission();
    await FirebaseMessaging.instance.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );
  }

  /// Schedule a reminder for an upcoming lecture.
  static Future<void> scheduleLectureReminder({
    required int id,
    required DateTime startsAt,
    required String title,
    required String body,
    int minutesBefore = 15,
  }) async {
    final when = startsAt.subtract(Duration(minutes: minutesBefore));
    if (when.isBefore(DateTime.now())) return; // already past
    await _local.zonedSchedule(
      id,
      title,
      body,
      tz.TZDateTime.from(when, tz.local),
      NotificationDetails(
        android: AndroidNotificationDetails(
          _remindersChannel.id,
          _remindersChannel.name,
          channelDescription: _remindersChannel.description,
          importance: Importance.high,
          priority: Priority.high,
        ),
        iOS: const DarwinNotificationDetails(),
      ),
      androidScheduleMode: AndroidScheduleMode.exactAllowWhileIdle,
    );
  }

  static Future<void> cancelAll() => _local.cancelAll();
}
