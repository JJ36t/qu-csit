import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/utils/arabic_formatting.dart';
import '../../announcements/data/announcements_repository.dart';
import '../../auth/presentation/auth_provider.dart';
import '../data/timetable_repository.dart';

class HomeTab extends ConsumerStatefulWidget {
  const HomeTab({super.key});

  @override
  ConsumerState<HomeTab> createState() => _HomeTabState();
}

class _HomeTabState extends ConsumerState<HomeTab> {
  List<dynamic> _todaySlots = [];
  List<dynamic> _announcements = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final today = DateTime.now();
      final iso = _iso(today);
      final repo = ref.read(timetableRepositoryProvider);
      final week = await repo.getWeek(weekStart: today.subtract(Duration(days: today.weekday % 7)));
      final todayDay = week.firstWhere((d) => d.date == iso, orElse: () => week.first);
      _todaySlots = todayDay.entries;
      final annRepo = ref.read(announcementsRepositoryProvider);
      _announcements = await annRepo.list();
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authProvider);
    final user = auth.me?.user;

    return Scaffold(
      appBar: AppBar(
        title: Text('مرحباً، ${user?.fullNameAr ?? ""}'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () => ref.read(authProvider.notifier).logout(),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  _NextLectureCard(slots: _todaySlots),
                  const SizedBox(height: 16),
                  _SectionHeader(title: 'محاضرات اليوم'),
                  if (_todaySlots.isEmpty)
                    _EmptyInline(text: 'لا محاضرات اليوم')
                  else
                    ..._todaySlots.take(3).map((e) => _SlotRow(entry: e)),
                  const SizedBox(height: 16),
                  _SectionHeader(title: 'آخر الإعلانات'),
                  if (_announcements.isEmpty)
                    _EmptyInline(text: 'لا إعلانات')
                  else
                    ..._announcements.take(3).map((a) => _AnnouncementRow(announcement: a)),
                ],
              ),
      ),
    );
  }

  String _iso(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
}

class _NextLectureCard extends StatelessWidget {
  const _NextLectureCard({required this.slots});
  final List<dynamic> slots;

  @override
  Widget build(BuildContext context) {
    // Find the next upcoming slot by combining today's date with each slot's start_time.
    final now = DateTime.now();
    dynamic next;
    DateTime? nextStart;
    for (final entry in slots) {
      if (entry.isCancelled == true) continue;
      final startStr = (entry.effectiveStart as String?) ?? entry.slot.startTime as String;
      final parts = startStr.split(':');
      final start = DateTime(
        now.year, now.month, now.day,
        int.parse(parts[0]), int.parse(parts[1]),
      );
      if (start.isAfter(now) && (nextStart == null || start.isBefore(nextStart))) {
        nextStart = start;
        next = entry;
      }
    }
    if (next == null) {
      return Card(
        color: Theme.of(context).colorScheme.primaryContainer,
        child: const Padding(
          padding: EdgeInsets.all(24),
          child: Column(
            children: [
              Icon(Icons.event_available, size: 48),
              SizedBox(height: 8),
              Text('لا محاضرات قادمة اليوم', textAlign: TextAlign.center),
            ],
          ),
        ),
      );
    }
    return Card(
      color: Theme.of(context).colorScheme.primaryContainer,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.timer_outlined, size: 24),
                const SizedBox(width: 8),
                Text(
                  'المحاضرة القادمة',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              '${ArabicDateFormatter.formatTime((next.effectiveStart as String?) ?? next.slot.startTime as String)} — ${ArabicDateFormatter.formatTime((next.effectiveEnd as String?) ?? next.slot.endTime as String)}',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            if (nextStart != null) ...[
              const SizedBox(height: 8),
              StreamBuilder(
                stream: Stream.periodic(const Duration(seconds: 1), (_) => DateTime.now()),
                builder: (context, snap) {
                  final remaining = nextStart!.difference(DateTime.now());
                  return Text(
                    ArabicDateFormatter.countdown(remaining),
                    style: Theme.of(context).textTheme.bodyLarge,
                  );
                },
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({required this.title});
  final String title;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(
        title,
        style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
      ),
    );
  }
}

class _EmptyInline extends StatelessWidget {
  const _EmptyInline({required this.text});
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Text(text, style: Theme.of(context).textTheme.bodyMedium),
    );
  }
}

class _SlotRow extends StatelessWidget {
  const _SlotRow({required this.entry});
  final dynamic entry;

  @override
  Widget build(BuildContext context) {
    final start = (entry.effectiveStart as String?) ?? entry.slot.startTime as String;
    final end = (entry.effectiveEnd as String?) ?? entry.slot.endTime as String;
    final isCancelled = entry.isCancelled as bool;
    return Card(
      child: ListTile(
        leading: const Icon(Icons.book_outlined),
        title: Text('${ArabicDateFormatter.formatTime(start)} — ${ArabicDateFormatter.formatTime(end)}'),
        subtitle: Text(
          isCancelled ? 'ملغاة' : ((entry.slot.kind as String) == 'lab' ? 'مختبر' : 'نظري'),
          style: TextStyle(color: isCancelled ? Colors.red : null),
        ),
      ),
    );
  }
}

class _AnnouncementRow extends StatelessWidget {
  const _AnnouncementRow({required this.announcement});
  final dynamic announcement;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: const Icon(Icons.campaign_outlined),
        title: Text(announcement.title as String, maxLines: 1, overflow: TextOverflow.ellipsis),
        subtitle: Text(
          (announcement.body as String).split('\n').first,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
      ),
    );
  }
}
