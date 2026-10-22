import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/utils/arabic_formatting.dart';
import '../../announcements/data/announcements_repository.dart';
import '../data/timetable_repository.dart';

class TimetableTab extends ConsumerStatefulWidget {
  const TimetableTab({super.key});

  @override
  ConsumerState<TimetableTab> createState() => _TimetableTabState();
}

class _TimetableTabState extends ConsumerState<TimetableTab> {
  late DateTime _weekStart;
  bool _isWeekView = true;

  @override
  void initState() {
    super.initState();
    final today = DateTime.now();
    // Week starts on Sunday (configurable; brief default)
    _weekStart = today.subtract(Duration(days: today.weekday % 7));
  }

  @override
  Widget build(BuildContext context) {
    final repo = ref.watch(timetableRepositoryProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('الجدول الأسبوعي'),
        actions: [
          IconButton(
            icon: Icon(_isWeekView ? Icons.view_day_outlined : Icons.view_week_outlined),
            onPressed: () => setState(() => _isWeekView = !_isWeekView),
            tooltip: _isWeekView ? 'عرض اليوم' : 'عرض الأسبوع',
          ),
        ],
      ),
      body: FutureBuilder(
        future: repo.getWeek(weekStart: _weekStart),
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return _ErrorState(message: snapshot.error.toString());
          }
          if (!snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          final days = snapshot.data!;
          if (days.every((d) => d.entries.isEmpty)) {
            return _EmptyState(onRetry: () => setState(() {}));
          }
          if (_isWeekView) {
            return _WeekView(days: days);
          }
          // Single-day view
          final today = DateTime.now();
          final iso = _iso(today);
          final todayDay = days.firstWhere(
            (d) => d.date == iso,
            orElse: () => days.first,
          );
          return _DayView(day: todayDay);
        },
      ),
      floatingActionButton: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          FloatingActionButton.small(
            heroTag: 'prev_week',
            onPressed: () => setState(() => _weekStart = _weekStart.subtract(const Duration(days: 7))),
            child: const Icon(Icons.chevron_right), // RTL: right = previous
          ),
          const SizedBox(width: 8),
          FloatingActionButton.small(
            heroTag: 'next_week',
            onPressed: () => setState(() => _weekStart = _weekStart.add(const Duration(days: 7))),
            child: const Icon(Icons.chevron_left),
          ),
        ],
      ),
    );
  }

  String _iso(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
}

class _WeekView extends StatelessWidget {
  const _WeekView({required this.days});
  final List<dynamic> days; // List<TimetableDay>

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: days.length,
      itemBuilder: (context, i) {
        final day = days[i];
        final date = DateTime.parse(day.date as String);
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Text(
                ArabicDateFormatter.formatDate(day.date as String),
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
            ),
            if (day.entries.isEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: Text(
                  'لا محاضرات',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              )
            else
              ...day.entries.map<Widget>((entry) => _EntryCard(entry: entry)).toList(),
          ],
        );
      },
    );
  }
}

class _DayView extends StatelessWidget {
  const _DayView({required this.day});
  final dynamic day;

  @override
  Widget build(BuildContext context) {
    if (day.entries.isEmpty) {
      return const _EmptyState(onRetry: null);
    }
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: day.entries.length,
      itemBuilder: (context, i) => _EntryCard(entry: day.entries[i]),
    );
  }
}

class _EntryCard extends StatelessWidget {
  const _EntryCard({required this.entry});
  final dynamic entry; // TimetableEntry

  @override
  Widget build(BuildContext context) {
    final slot = entry.slot;
    final isCancelled = entry.isCancelled as bool;
    final start = (entry.effectiveStart as String?) ?? slot.startTime as String;
    final end = (entry.effectiveEnd as String?) ?? slot.endTime as String;
    final kindLabel = (slot.kind as String) == 'lab' ? 'مختبر' : 'نظري';
    final kindColor = (slot.kind as String) == 'lab'
        ? Colors.orange.shade700
        : Colors.blue.shade700;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: ListTile(
        leading: Container(
          width: 4,
          decoration: BoxDecoration(
            color: isCancelled ? Colors.grey : kindColor,
            borderRadius: BorderRadius.circular(4),
          ),
        ),
        title: Text(
          '${ArabicDateFormatter.formatTime(start)} — ${ArabicDateFormatter.formatTime(end)}',
          style: TextStyle(
            decoration: isCancelled ? TextDecoration.lineThrough : null,
            color: isCancelled ? Colors.grey : null,
          ),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (slot.roomId != null)
              Text('القاعة: ${slot.roomId}')
            else
              const Text('القاعة غير محددة'),
            const SizedBox(height: 4),
            if (isCancelled)
              const Text('ملغاة', style: TextStyle(color: Colors.red))
            else
              Text(kindLabel),
            if ((entry.changes as List).isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(
                  'تم تعديل الحصة',
                  style: TextStyle(color: kindColor, fontSize: 12),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.onRetry});
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.event_busy, size: 64, color: Colors.grey.shade400),
          const SizedBox(height: 16),
          Text('لا توجد محاضرات في هذه الفترة', style: Theme.of(context).textTheme.bodyLarge),
          if (onRetry != null) ...[
            const SizedBox(height: 16),
            FilledButton(onPressed: onRetry, child: const Text('إعادة المحاولة')),
          ],
        ],
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.message});
  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.cloud_off, size: 64, color: Colors.grey.shade400),
            const SizedBox(height: 16),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 8),
            Text(
              'عرض البيانات المخزّنة',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }
}
