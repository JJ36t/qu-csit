import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/dio_client.dart';
import '../../core/network/token_storage.dart';
import '../../shared/models/auth_models.dart';

/// Remote data source for /auth/* endpoints.
class AuthApi {
  AuthApi(this._dio);
  final Dio _dio;

  Future<TokenPair> login(LoginRequest req) async {
    final r = await _dio.post('/auth/login', data: req.toJson());
    return TokenPair.fromJson(r.data as Map<String, dynamic>);
  }

  Future<TokenPair> refresh(String refreshToken) async {
    final r = await _dio.post('/auth/refresh', data: {'refresh_token': refreshToken});
    return TokenPair.fromJson(r.data as Map<String, dynamic>);
  }

  Future<void> logout(String? refreshToken) async {
    await _dio.post('/auth/logout', data: {'refresh_token': refreshToken});
  }

  Future<AuthMeOut> me() async {
    final r = await _dio.get('/auth/me');
    return AuthMeOut.fromJson(r.data as Map<String, dynamic>);
  }

  Future<void> changePassword(ChangePasswordRequest req) async {
    await _dio.post('/auth/change-password', data: req.toJson());
  }
}

final authApiProvider = Provider<AuthApi>((ref) {
  final dio = ref.watch(dioProvider);
  return AuthApi(dio);
});

final dioProvider = Provider<Dio>((ref) {
  // This is overridden in main.dart with the wired-up Dio instance.
  throw UnimplementedError('dioProvider must be overridden in ProviderScope');
});

final tokenStorageProvider = Provider<TokenStorage>((ref) {
  throw UnimplementedError('tokenStorageProvider must be overridden');
});
