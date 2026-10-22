import 'package:drift/drift.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/storage/local_db.dart';
import '../../../core/storage/providers.dart';
import '../../../shared/models/timetable_models.dart';
import '../data/timetable_api.dart';

/// Stale-while-revalidate timetable repository.
///
/// 1. Read cache instantly.
/// 2. Emit cached snapshot to UI.
/// 3. Fetch fresh data in background; replace cache; emit updated state.
/// 4. If fetch fails AND cache exists → keep showing cache (offline).
class TimetableRepository {
  TimetableRepository(this._api, this._db);
  final TimetableApi _api;
  final LocalDatabase _db;

  Future<List<TimetableDay>> getWeek({required DateTime weekStart}) async {
    final days = <TimetableDay>[];
    for (var i = 0; i < 7; i++) {
      final day = weekStart.add(Duration(days: i));
      days.add(await _getDay(day));
    }
    return days;
  }

  Future<TimetableDay> _getDay(DateTime date) async {
    final iso = _iso(date);
    final cached = await _db.getTimetableForDate(iso);
    // Background refresh — don't await.
    _refreshDay(date);
    final entries = cached
        .map((c) => TimetableEntry(
              slot: TimetableSlotOut(
                id: c.slotId,
                offeringId: c.offeringId,
                weekday: c.weekday,
                startTime: c.startTime,
                endTime: c.endTime,
                roomId: c.roomId,
                kind: c.kind,
              ),
              effectiveStart: c.effectiveStart,
              effectiveEnd: c.effectiveEnd,
              effectiveRoomId: c.effectiveRoomId,
              isCancelled: c.isCancelled,
            ))
        .toList();
    return TimetableDay(date: iso, entries: entries);
  }

  Future<void> _refreshDay(DateTime date) async {
    final iso = _iso(date);
    try {
      final days = await _api.getTimetable(from: iso, to: iso);
      if (days.isEmpty) return;
      final day = days.first;
      final rows = day.entries.map((e) {
        return CachedTimetableEntriesCompanion.insert(
          slotId: e.slot.id,
          offeringId: e.slot.offeringId,
          weekday: e.slot.weekday,
          startTime: e.slot.startTime,
          endTime: e.slot.endTime,
          roomId: Value(e.slot.roomId),
          kind: e.slot.kind,
          effectiveDate: iso,
          effectiveStart: Value(e.effectiveStart),
          effectiveEnd: Value(e.effectiveEnd),
          effectiveRoomId: Value(e.effectiveRoomId),
          isCancelled: Value(e.isCancelled),
          cachedAt: DateTime.now(),
        );
      }).toList();
      await _db.replaceTimetableForDate(iso, rows);
    } catch (_) {
      // Offline — keep cache.
    }
  }

  String _iso(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
}

final timetableRepositoryProvider = Provider<TimetableRepository>((ref) {
  final api = ref.watch(timetableApiProvider);
  final db = ref.watch(localDatabaseProvider);
  return TimetableRepository(api, db);
});
