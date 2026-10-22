import 'package:freezed_annotation/freezed_annotation.dart';

part 'comms_models.freezed.dart';
part 'comms_models.g.dart';

@freezed
class AnnouncementOut with _$AnnouncementOut {
  const factory AnnouncementOut({
    required String id,
    required String scope,
    @JsonKey(name: 'scope_id') String? scopeId,
    required String title,
    required String body,
    @Default(0) int priority,
    @Default(false) bool pinned,
    @JsonKey(name: 'publish_at') String? publishAt,
    @JsonKey(name: 'expires_at') String? expiresAt,
    @JsonKey(name: 'created_at') required String createdAt,
    @JsonKey(name: 'created_by') String? createdBy,
    @JsonKey(name: 'is_read') @Default(false) bool isRead,
  }) = _AnnouncementOut;

  factory AnnouncementOut.fromJson(Map<String, dynamic> json) =>
      _$AnnouncementOutFromJson(json);
}

@freezed
class NotificationOut with _$NotificationOut {
  const factory NotificationOut({
    required String id,
    required String type,
    required String title,
    String? body,
    Map<String, dynamic>? data,
    @JsonKey(name: 'read_at') String? readAt,
    @JsonKey(name: 'created_at') required String createdAt,
  }) = _NotificationOut;

  factory NotificationOut.fromJson(Map<String, dynamic> json) =>
      _$NotificationOutFromJson(json);
}

@freezed
class NotificationList with _$NotificationList {
  const factory NotificationList({
    @Default([]) List<NotificationOut> items,
    @Default(0) int total,
    @Default(0) int unread,
  }) = _NotificationList;

  factory NotificationList.fromJson(Map<String, dynamic> json) =>
      _$NotificationListFromJson(json);
}
