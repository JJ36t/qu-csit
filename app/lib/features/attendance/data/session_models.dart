import 'package:freezed_annotation/freezed_annotation.dart';

part 'session_models.freezed.dart';
part 'session_models.g.dart';

@freezed
class SessionOpenResponse with _$SessionOpenResponse {
  const factory SessionOpenResponse({
    @JsonKey(name: 'session_id') required String sessionId,
    required String secret,
    @JsonKey(name: 'window_s') @Default(20) int windowS,
    @JsonKey(name: 'late_threshold_minutes') @Default(15) int lateThresholdMinutes,
    required String status,
    @JsonKey(name: 'offering_id') required String offeringId,
    @JsonKey(name: 'starts_at') required String startsAt,
    @JsonKey(name: 'ends_at') required String endsAt,
  }) = _SessionOpenResponse;

  factory SessionOpenResponse.fromJson(Map<String, dynamic> json) =>
      _$SessionOpenResponseFromJson(json);
}

@freezed
class LiveRecord with _$LiveRecord {
  const factory LiveRecord({
    @JsonKey(name: 'student_id') required String studentId,
    @JsonKey(name: 'full_name_ar') required String fullNameAr,
    required String status,
    required String method,
    @JsonKey(name: 'scanned_at') String? scannedAt,
    @Default(false) bool flagged,
    @JsonKey(name: 'flag_reason') String? flagReason,
  }) = _LiveRecord;

  factory LiveRecord.fromJson(Map<String, dynamic> json) =>
      _$LiveRecordFromJson(json);
}

@freezed
class SessionLiveResponse with _$SessionLiveResponse {
  const factory SessionLiveResponse({
    @JsonKey(name: 'session_id') required String sessionId,
    @JsonKey(name: 'offering_id') required String offeringId,
    required String status,
    @JsonKey(name: 'present_count') required int presentCount,
    @JsonKey(name: 'late_count') required int lateCount,
    @JsonKey(name: 'absent_count') required int absentCount,
    @JsonKey(name: 'flagged_count') required int flaggedCount,
    @JsonKey(name: 'enrolled_count') required int enrolledCount,
    @Default([]) List<LiveRecord> records,
  }) = _SessionLiveResponse;

  factory SessionLiveResponse.fromJson(Map<String, dynamic> json) =>
      _$SessionLiveResponseFromJson(json);
}

@freezed
class SessionCloseResponse with _$SessionCloseResponse {
  const factory SessionCloseResponse({
    @JsonKey(name: 'session_id') required String sessionId,
    @JsonKey(name: 'closed_at') required String closedAt,
    @JsonKey(name: 'present_count') required int presentCount,
    @JsonKey(name: 'late_count') required int lateCount,
    @JsonKey(name: 'absent_count') required int absentCount,
    @JsonKey(name: 'flagged_count') required int flaggedCount,
    @JsonKey(name: 'enrolled_count') required int enrolledCount,
  }) = _SessionCloseResponse;

  factory SessionCloseResponse.fromJson(Map<String, dynamic> json) =>
      _$SessionCloseResponseFromJson(json);
}

@freezed
class AttendanceScanResponse with _$AttendanceScanResponse {
  const factory AttendanceScanResponse({
    required String status,
    required String method,
    @JsonKey(name: 'scanned_at') required String scannedAt,
    @Default(false) bool flagged,
    @JsonKey(name: 'flag_reason') String? flagReason,
    @JsonKey(name: 'message_ar') required String messageAr,
  }) = _AttendanceScanResponse;

  factory AttendanceScanResponse.fromJson(Map<String, dynamic> json) =>
      _$AttendanceScanResponseFromJson(json);
}
