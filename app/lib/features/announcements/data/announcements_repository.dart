import 'package:drift/drift.dart' show Value;
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/storage/local_db.dart';
import '../../../core/storage/providers.dart';
import '../../../shared/models/comms_models.dart';
import '../data/announcements_api.dart';

/// Stale-while-revalidate announcements repository.
class AnnouncementsRepository {
  AnnouncementsRepository(this._api, this._db);
  final AnnouncementsApi _api;
  final LocalDatabase _db;

  Future<List<AnnouncementOut>> list() async {
    final cached = await _db.getAllAnnouncements();
    // Background refresh
    _refresh();
    return cached.map((c) => AnnouncementOut(
      id: c.id,
      scope: c.scope,
      scopeId: c.scopeId,
      title: c.title,
      body: c.body,
      priority: c.priority,
      pinned: c.pinned,
      publishAt: c.publishAt?.toIso8601String(),
      createdAt: c.createdAt.toIso8601String(),
      isRead: c.isRead,
    )).toList();
  }

  Future<void> _refresh() async {
    try {
      final fresh = await _api.list(limit: 50);
      final rows = fresh.map((a) {
        final createdAt = DateTime.tryParse(a.createdAt) ?? DateTime.now();
        final publishAt = a.publishAt != null ? DateTime.tryParse(a.publishAt!) : null;
        return CachedAnnouncementsCompanion.insert(
          id: a.id,
          scope: a.scope,
          scopeId: Value(a.scopeId),
          title: a.title,
          body: a.body,
          priority: Value(a.priority),
          pinned: Value(a.pinned),
          publishAt: Value(publishAt),
          createdAt: createdAt,
          isRead: Value(a.isRead),
          cachedAt: DateTime.now(),
        );
      }).toList();
      await _db.replaceAnnouncements(rows);
    } catch (_) {
      // Offline — keep cache.
    }
  }

  Future<void> markRead(String id) async {
    await _db.markAnnouncementRead(id);
    try {
      await _api.markRead(id);
    } catch (_) {}
  }
}

final announcementsRepositoryProvider = Provider<AnnouncementsRepository>((ref) {
  final api = ref.watch(announcementsApiProvider);
  final db = ref.watch(localDatabaseProvider);
  return AnnouncementsRepository(api, db);
});
