import 'package:freezed_annotation/freezed_annotation.dart';

part 'auth_models.freezed.dart';
part 'auth_models.g.dart';

/// /auth/login response.
@freezed
class TokenPair with _$TokenPair {
  const factory TokenPair({
    @JsonKey(name: 'access_token') required String accessToken,
    @JsonKey(name: 'refresh_token') required String refreshToken,
    @JsonKey(name: 'expires_in') required int expiresInSeconds,
    @JsonKey(name: 'token_type') @Default('Bearer') String tokenType,
    @JsonKey(name: 'must_change_password') @Default(false) bool mustChangePassword,
  }) = _TokenPair;

  factory TokenPair.fromJson(Map<String, dynamic> json) => _$TokenPairFromJson(json);
}

@freezed
class UserOut with _$UserOut {
  const factory UserOut({
    required String id,
    required String role,
    @JsonKey(name: 'university_id') required String universityId,
    @JsonKey(name: 'full_name_ar') required String fullNameAr,
    String? email,
    String? phone,
    required String status,
    @JsonKey(name: 'must_change_password') @Default(false) bool mustChangePassword,
    @JsonKey(name: 'last_login_at') String? lastLoginAt,
  }) = _UserOut;

  factory UserOut.fromJson(Map<String, dynamic> json) => _$UserOutFromJson(json);
}

@freezed
class StudentOut with _$StudentOut {
  const factory StudentOut({
    @JsonKey(name: 'user_id') required String userId,
    @JsonKey(name: 'department_id') required String departmentId,
    required int stage,
    @JsonKey(name: 'study_type') required String studyType,
    @JsonKey(name: 'group_id') String? groupId,
    @JsonKey(name: 'enrollment_year') required int enrollmentYear,
    required String status,
  }) = _StudentOut;

  factory StudentOut.fromJson(Map<String, dynamic> json) => _$StudentOutFromJson(json);
}

@freezed
class StaffOut with _$StaffOut {
  const factory StaffOut({
    @JsonKey(name: 'user_id') required String userId,
    @JsonKey(name: 'department_id') String? departmentId,
    @JsonKey(name: 'academic_title') String? academicTitle,
    String? office,
  }) = _StaffOut;

  factory StaffOut.fromJson(Map<String, dynamic> json) => _$StaffOutFromJson(json);
}

@freezed
class AuthMeOut with _$AuthMeOut {
  const factory AuthMeOut({
    required UserOut user,
    StudentOut? student,
    StaffOut? staff,
  }) = _AuthMeOut;

  factory AuthMeOut.fromJson(Map<String, dynamic> json) => _$AuthMeOutFromJson(json);
}

/// Login request body.
@freezed
class LoginRequest with _$LoginRequest {
  const factory LoginRequest({
    @JsonKey(name: 'university_id') required String universityId,
    required String password,
    @JsonKey(name: 'device_fingerprint') String? deviceFingerprint,
    @JsonKey(name: 'device_model') String? deviceModel,
    @JsonKey(name: 'fcm_token') String? fcmToken,
  }) = _LoginRequest;

  factory LoginRequest.fromJson(Map<String, dynamic> json) =>
      _$LoginRequestFromJson(json);
}

@freezed
class ChangePasswordRequest with _$ChangePasswordRequest {
  const factory ChangePasswordRequest({
    @JsonKey(name: 'old_password') required String oldPassword,
    @JsonKey(name: 'new_password') required String newPassword,
  }) = _ChangePasswordRequest;

  factory ChangePasswordRequest.fromJson(Map<String, dynamic> json) =>
      _$ChangePasswordRequestFromJson(json);
}
