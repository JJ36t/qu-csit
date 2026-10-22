import 'package:freezed_annotation/freezed_annotation.dart';

part 'materials_models.freezed.dart';
part 'materials_models.g.dart';

@freezed
class MaterialOut with _$MaterialOut {
  const factory MaterialOut({
    required String id,
    @JsonKey(name: 'offering_id') required String offeringId,
    required String title,
    required String kind, // pdf | video_link | link
    @JsonKey(name: 'file_id') String? fileId,
    String? url,
    @JsonKey(name: 'week_no') int? weekNo,
    @JsonKey(name: 'is_published') @Default(false) bool isPublished,
    String? description,
    @JsonKey(name: 'created_at') required String createdAt,
  }) = _MaterialOut;

  factory MaterialOut.fromJson(Map<String, dynamic> json) =>
      _$MaterialOutFromJson(json);
}

@freezed
class MaterialWithDownload with _$MaterialWithDownload {
  const factory MaterialWithDownload({
    required String id,
    @JsonKey(name: 'offering_id') required String offeringId,
    required String title,
    required String kind,
    @JsonKey(name: 'file_id') String? fileId,
    String? url,
    @JsonKey(name: 'week_no') int? weekNo,
    @JsonKey(name: 'is_published') @Default(false) bool isPublished,
    String? description,
    @JsonKey(name: 'created_at') required String createdAt,
    @JsonKey(name: 'download_url') String? downloadUrl,
  }) = _MaterialWithDownload;

  factory MaterialWithDownload.fromJson(Map<String, dynamic> json) =>
      _$MaterialWithDownloadFromJson(json);
}

@freezed
class FileDownloadResponse with _$FileDownloadResponse {
  const factory FileDownloadResponse({
    required String url,
    @JsonKey(name: 'expires_in') required int expiresIn,
  }) = _FileDownloadResponse;

  factory FileDownloadResponse.fromJson(Map<String, dynamic> json) =>
      _$FileDownloadResponseFromJson(json);
}
