import 'package:freezed_annotation/freezed_annotation.dart';

part 'timetable_models.freezed.dart';
part 'timetable_models.g.dart';

/// One weekly slot.
@freezed
class TimetableSlotOut with _$TimetableSlotOut {
  const factory TimetableSlotOut({
    required String id,
    @JsonKey(name: 'offering_id') required String offeringId,
    required int weekday,
    @JsonKey(name: 'start_time') required String startTime,
    @JsonKey(name: 'end_time') required String endTime,
    @JsonKey(name: 'room_id') String? roomId,
    required String kind, // theory | lab
  }) = _TimetableSlotOut;

  factory TimetableSlotOut.fromJson(Map<String, dynamic> json) =>
      _$TimetableSlotOutFromJson(json);
}

@freezed
class TimetableChangeOut with _$TimetableChangeOut {
  const factory TimetableChangeOut({
    required String id,
    @JsonKey(name: 'slot_id') required String slotId,
    required String date, // YYYY-MM-DD
    required String type, // cancel | move | extra
    @JsonKey(name: 'new_start') String? newStart,
    @JsonKey(name: 'new_end') String? newEnd,
    @JsonKey(name: 'new_room_id') String? newRoomId,
    String? reason,
    @JsonKey(name: 'created_by') String? createdBy,
  }) = _TimetableChangeOut;

  factory TimetableChangeOut.fromJson(Map<String, dynamic> json) =>
      _$TimetableChangeOutFromJson(json);
}

/// Combined view: a slot + any changes on a specific date.
@freezed
class TimetableEntry with _$TimetableEntry {
  const factory TimetableEntry({
    required TimetableSlotOut slot,
    @Default([]) List<TimetableChangeOut> changes,
    @JsonKey(name: 'effective_start') String? effectiveStart,
    @JsonKey(name: 'effective_end') String? effectiveEnd,
    @JsonKey(name: 'effective_room_id') String? effectiveRoomId,
    @JsonKey(name: 'is_cancelled') @Default(false) bool isCancelled,
  }) = _TimetableEntry;

  factory TimetableEntry.fromJson(Map<String, dynamic> json) =>
      _$TimetableEntryFromJson(json);
}

/// One day of the timetable.
@freezed
class TimetableDay with _$TimetableDay {
  const factory TimetableDay({
    required String date,
    @Default([]) List<TimetableEntry> entries,
  }) = _TimetableDay;

  factory TimetableDay.fromJson(Map<String, dynamic> json) =>
      _$TimetableDayFromJson(json);
}
