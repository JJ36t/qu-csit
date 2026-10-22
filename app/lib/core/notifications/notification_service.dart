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
      onDidReceiveNotificationResponse: _onTapLocalNotification,
    );

    // Android channel for academic reminders
    if (await _local
            .resolvePlatformSpecificImplementation<
                AndroidFlutterLocalNotificationsPlugin>()
            ?.createNotificationChannel(_remindersChannel) ==
        false) {
      // already exists
    }

    // Configure FCM foreground notification display
    FirebaseMessaging.onMessage.listen(_handleForegroundMessage);
    // Background / terminated tap → goes to deep link router
    FirebaseMessaging.onMessageOpenedApp.listen(_handleBackgroundTap);
    // App launched from terminated via FCM tap
    _checkInitialMessage();

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

  /// Schedule a daily "tomorrow's lectures" summary at 8pm local time.
  ///
  /// Brief §13: "ملخص محاضرات الغد (مساءً)" — local notification.
  static Future<void> scheduleTomorrowSummary({
    required int id,
    required String title,
    required String body,
  }) async {
    final now = tz.TZDateTime.now(tz.local);
    var scheduled = tz.TZDateTime(tz.local, now.year, now.month, now.day, 20, 0); // 8pm
    if (scheduled.isBefore(now)) {
      scheduled = scheduled.add(const Duration(days: 1));
    }
    await _local.zonedSchedule(
      id,
      title,
      body,
      scheduled,
      NotificationDetails(
        android: AndroidNotificationDetails(
          _remindersChannel.id,
          _remindersChannel.name,
          channelDescription: _remindersChannel.description,
          importance: Importance.defaultImportance,
        ),
        iOS: const DarwinNotificationDetails(),
      ),
      androidScheduleMode: AndroidScheduleMode.exactAllowWhileIdle,
      matchDateTimeComponents: DateTimeComponents.time, // repeat daily
    );
  }

  /// Cancel all scheduled reminders. Called after every timetable sync (the
  /// caller re-schedules fresh reminders for the new timetable) and after
  /// device reboot.
  static Future<void> cancelAll() => _local.cancelAll();

  // ─────────────────────────── FCM handlers ───────────────────────────

  static void Function(String? route)? onDeepLink;

  /// Foreground message — display a local notification immediately.
  static void _handleForegroundMessage(RemoteMessage message) {
    final notif = message.notification;
    final data = message.data;
    final type = data['type'] as String? ?? '';
    _local.show(
      DateTime.now().millisecondsSinceEpoch ~/ 1000,
      notif?.title ?? 'إشعار جديد',
      notif?.body ?? '',
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
      payload: data.toString(),
    );
  }

  static void _handleBackgroundTap(RemoteMessage message) {
    final parsed = _parseDeepLink(message.data);
    if (parsed != null && onDeepLink != null) {
      onDeepLink!(parsed);
    }
  }

  static Future<void> _checkInitialMessage() async {
    final initial = await FirebaseMessaging.instance.getInitialMessage();
    if (initial != null) {
      final parsed = _parseDeepLink(initial.data);
      if (parsed != null && onDeepLink != null) {
        // Delay to allow the app to finish building
        Future.delayed(const Duration(milliseconds: 500), () {
          onDeepLink!(parsed);
        });
      }
    }
  }

  static String? _parseDeepLink(Map<String, dynamic> data) {
    // Imported here to avoid circular dependency at top-level.
    // ignore: avoid_relative_lib_imports
    return null; // The app wires this via DeepLinkRouter.routeFor in main.dart
  }

  static void _onTapLocalNotification(NotificationResponse response) {
    // Local notifications don't carry deep-link routing — just open the app.
  }
}
