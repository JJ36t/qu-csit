import 'package:intl/intl.dart';

/// Arabic date/number formatting helpers. All dates are stored UTC and
/// displayed in Asia/Baghdad (UTC+3, no DST).
class ArabicDateFormatter {
  ArabicDateFormatter._();

  static const String baghdadTz = 'Asia/Baghdad';
  static const List<String> arabicMonths = [
    'كانون الثاني', 'شباط', 'آذار', 'نيسان', 'أيار', 'حزيران',
    'تموز', 'آب', 'أيلول', 'تشرين الأول', 'تشرين الثاني', 'كانون الأول',
  ];

  static const List<String> weekdays = [
    'الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت',
  ];

  /// Formats an ISO datetime string into Arabic, e.g.
  /// "الإثنين، 13 تشرين الأول 2025 — 10:00 ص".
  static String formatDateTime(String isoUtc) {
    final dt = DateTime.parse(isoUtc).toUtc();
    final baghdad = dt.toUtc().add(const Duration(hours: 3));
    return '${weekdays[baghdad.weekday % 7]}، '
        '${baghdad.day} ${arabicMonths[baghdad.month - 1]} ${baghdad.year} — '
        '${_formatTime12h(baghdad.hour, baghdad.minute)}';
  }

  static String formatDate(String isoUtc) {
    final dt = DateTime.parse(isoUtc).toUtc().add(const Duration(hours: 3));
    return '${dt.day} ${arabicMonths[dt.month - 1]} ${dt.year}';
  }

  static String formatTime(String hhmmss) {
    // Input "HH:mm:ss" → "h:mm ص/م"
    final parts = hhmmss.split(':');
    final h = int.parse(parts[0]);
    final m = int.parse(parts[1]);
    return _formatTime12h(h, m);
  }

  static String _formatTime12h(int hour, int minute) {
    final period = hour < 12 ? 'ص' : 'م';
    final h12 = hour % 12 == 0 ? 12 : hour % 12;
    final mm = minute.toString().padLeft(2, '0');
    return '$h12:$mm $period';
  }

  /// Format a duration as Arabic countdown, e.g. "باقٍ ٢ ساعة و٣٠ دقيقة".
  static String countdown(Duration d) {
    if (d.isNegative) return 'انتهى';
    final h = d.inHours;
    final m = d.inMinutes.remainder(60);
    if (h == 0) return 'باقٍ $m دقيقة';
    if (m == 0) return 'باقٍ $h ساعة';
    return 'باقٍ $h ساعة و$m دقيقة';
  }

  /// Numbers — Western (0-9) by default per brief §12.
  static String number(int n) => NumberFormat.decimalPattern().format(n);
  static String percent(double v) => '${(v * 100).toStringAsFixed(0)}٪';
}
