import 'package:drift/drift.dart' show Value;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/storage/local_db.dart';
import '../../../core/storage/providers.dart';
import '../../../core/utils/arabic_formatting.dart';
import '../../announcements/data/announcements_api.dart';

class NotificationsTab extends ConsumerStatefulWidget {
  const NotificationsTab({super.key});

  @override
  ConsumerState<NotificationsTab> createState() => _NotificationsTabState();
}

class _NotificationsTabState extends ConsumerState<NotificationsTab> {
  Future<List<dynamic>>? _future;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  void _refresh() async {
    final api = ref.read(notificationsApiProvider);
    final db = ref.read(localDatabaseProvider);
    try {
      final fresh = await api.list();
      final rows = fresh.items.map((n) {
        final createdAt = DateTime.tryParse(n.createdAt) ?? DateTime.now();
        final readAt = n.readAt != null ? DateTime.tryParse(n.readAt!) : null;
        return CachedNotificationsCompanion.insert(
          id: n.id,
          type: n.type,
          title: n.title,
          body: Value(n.body),
          dataJson: Value(n.data != null ? n.data.toString() : null),
          readAt: Value(readAt),
          createdAt: createdAt,
        );
      }).toList();
      await db.replaceNotifications(rows);
    } catch (_) {}
    setState(() {
      _future = db.getAllNotifications();
    });
  }

  Future<void> _markAllRead() async {
    final api = ref.read(notificationsApiProvider);
    final db = ref.read(localDatabaseProvider);
    await db.markAllNotificationsRead();
    try {
      await api.markAllRead();
    } catch (_) {}
    _refresh();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('الإشعارات'),
        actions: [
          IconButton(
            icon: const Icon(Icons.done_all),
            onPressed: _markAllRead,
            tooltip: 'تعليم الكل كمقروء',
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _refresh,
          ),
        ],
      ),
      body: FutureBuilder<List<dynamic>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return Center(child: Text('تعذّر التحميل'));
          }
          if (!snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          final items = snapshot.data!;
          if (items.isEmpty) {
            return const Center(child: Text('لا إشعارات'));
          }
          return ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: items.length,
            separatorBuilder: (_, __) => const Divider(height: 0),
            itemBuilder: (context, i) {
              final n = items[i];
              final isRead = n.readAt != null;
              final typeIcon = _iconForType(n.type as String);
              return ListTile(
                leading: Icon(
                  typeIcon,
                  color: isRead ? Colors.grey : Theme.of(context).colorScheme.primary,
                ),
                title: Text(
                  n.title as String,
                  style: TextStyle(
                    fontWeight: isRead ? FontWeight.normal : FontWeight.bold,
                  ),
                ),
                subtitle: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (n.body != null) Text(n.body as String, maxLines: 2, overflow: TextOverflow.ellipsis),
                    const SizedBox(height: 4),
                    Text(
                      ArabicDateFormatter.formatDateTime(n.createdAt.toIso8601String()),
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              );
            },
          );
        },
      ),
    );
  }

  IconData _iconForType(String type) {
    switch (type) {
      case 'timetable_change':
        return Icons.edit_calendar;
      case 'attendance_open':
        return Icons.qr_code;
      case 'announcement':
        return Icons.campaign;
      case 'new_material':
        return Icons.attach_file;
      case 'absence_warning':
        return Icons.warning_amber;
      case 'grade_published':
        return Icons.grade;
      default:
        return Icons.notifications;
    }
  }
}
