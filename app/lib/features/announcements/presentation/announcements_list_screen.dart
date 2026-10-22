import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/utils/arabic_formatting.dart';
import '../data/announcements_repository.dart';

class AnnouncementsListScreen extends ConsumerStatefulWidget {
  const AnnouncementsListScreen({super.key});

  @override
  ConsumerState<AnnouncementsListScreen> createState() => _AnnouncementsListScreenState();
}

class _AnnouncementsListScreenState extends ConsumerState<AnnouncementsListScreen> {
  Future<List<dynamic>>? _future;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  void _refresh() {
    final repo = ref.read(announcementsRepositoryProvider);
    setState(() {
      _future = repo.list();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('الإعلانات'),
        actions: [
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
            return Center(child: Text('تعذّر التحميل: ${snapshot.error}'));
          }
          if (!snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          final items = snapshot.data!;
          if (items.isEmpty) {
            return const Center(child: Text('لا توجد إعلانات'));
          }
          return RefreshIndicator(
            onRefresh: () async => _refresh(),
            child: ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: items.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemBuilder: (context, i) {
                final a = items[i];
                return _AnnouncementCard(
                  announcement: a,
                  onTap: () async {
                    await ref.read(announcementsRepositoryProvider).markRead(a.id);
                    _refresh();
                    if (mounted) {
                      Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => _AnnouncementDetailScreen(announcement: a),
                        ),
                      );
                    }
                  },
                );
              },
            ),
          );
        },
      ),
    );
  }
}

class _AnnouncementCard extends StatelessWidget {
  const _AnnouncementCard({required this.announcement, required this.onTap});
  final dynamic announcement;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scope = announcement.scope as String;
    final pinned = announcement.pinned as bool;
    final isRead = announcement.isRead as bool;
    final scopeColor = {
      'college': Colors.blue,
      'department': Colors.green,
      'stage': Colors.purple,
      'group': Colors.cyan,
      'offering': Colors.orange,
    }[scope] ?? Colors.grey;

    return Card(
      color: pinned ? Colors.amber.shade50 : null,
      child: ListTile(
        onTap: onTap,
        leading: Container(
          width: 4,
          decoration: BoxDecoration(
            color: scopeColor,
            borderRadius: BorderRadius.circular(4),
          ),
        ),
        title: Row(
          children: [
            if (pinned) const Padding(
              padding: EdgeInsets.only(left: 4),
              child: Icon(Icons.push_pin, size: 16, color: Colors.amber),
            ),
            Expanded(
              child: Text(
                announcement.title as String,
                style: TextStyle(
                  fontWeight: pinned || !isRead ? FontWeight.bold : FontWeight.normal,
                ),
              ),
            ),
          ],
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              (announcement.body as String).split('\n').first,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 4),
            Text(
              ArabicDateFormatter.formatDateTime(announcement.createdAt as String),
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }
}

class _AnnouncementDetailScreen extends StatelessWidget {
  const _AnnouncementDetailScreen({required this.announcement});
  final dynamic announcement;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('تفاصيل الإعلان')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              announcement.title as String,
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              ArabicDateFormatter.formatDateTime(announcement.createdAt as String),
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 24),
            Text(
              announcement.body as String,
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(height: 1.7),
            ),
          ],
        ),
      ),
    );
  }
}
