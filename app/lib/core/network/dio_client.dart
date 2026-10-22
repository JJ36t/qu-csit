import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../config.dart';
import 'token_storage.dart';

/// Dio instance configured for the QU-CSIT API.
///
/// Auto-attaches `Authorization: Bearer <access>` to every request.
/// On 401, transparently refreshes the access token via /auth/refresh,
/// retries the original request once, then resumes the call.
Dio buildDio({
  required TokenStorage tokenStorage,
  required FlutterSecureStorage secureStorage,
}) {
  final dio = Dio(BaseOptions(
    baseUrl: AppConfig.apiFullBase,
    connectTimeout: AppConfig.connectTimeout,
    receiveTimeout: AppConfig.receiveTimeout,
    sendTimeout: AppConfig.sendTimeout,
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    },
  ));

  dio.interceptors.add(_AuthInterceptor(
    dio: dio,
    tokenStorage: tokenStorage,
    secureStorage: secureStorage,
  ));

  if (kDebugMode) {
    dio.interceptors.add(LogInterceptor(
      requestBody: false,
      responseBody: false,
      requestHeader: false,
      responseHeader: false,
      error: true,
    ));
  }

  return dio;
}

class _AuthInterceptor extends Interceptor {
  _AuthInterceptor({
    required this.dio,
    required this.tokenStorage,
    required this.secureStorage,
  });

  final Dio dio;
  final TokenStorage tokenStorage;
  final FlutterSecureStorage secureStorage;
  bool _isRefreshing = false;

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    final access = await tokenStorage.getAccessToken();
    if (access != null && access.isNotEmpty) {
      options.headers['Authorization'] = 'Bearer $access';
    }
    handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    final req = err.requestOptions;
    final isAuthPath = req.path.contains('/auth/login') ||
        req.path.contains('/auth/refresh');
    if (err.response?.statusCode != 401 || isAuthPath) {
      handler.next(err);
      return;
    }

    // Try refresh exactly once per request
    if (req.extra['retried'] == true) {
      await tokenStorage.clear();
      handler.next(err);
      return;
    }
    req.extra['retried'] = true;

    final refresh = await tokenStorage.getRefreshToken();
    if (refresh == null || refresh.isEmpty) {
      await tokenStorage.clear();
      handler.next(err);
      return;
    }

    try {
      final r = await Dio(BaseOptions(baseUrl: AppConfig.apiFullBase)).post(
        '/auth/refresh',
        data: {'refresh_token': refresh},
      );
      final newAccess = r.data['access_token'] as String;
      final newRefresh = r.data['refresh_token'] as String;
      await tokenStorage.saveTokens(access: newAccess, refresh: newRefresh);
      req.headers['Authorization'] = 'Bearer $newAccess';
      final cloned = await dio.fetch(req);
      handler.resolve(cloned);
    } on DioException catch (_) {
      await tokenStorage.clear();
      handler.next(err);
    }
  }
}

/// Parsed API error — already-translated Arabic message + machine code.
class ApiError implements Exception {
  const ApiError({
    required this.code,
    required this.messageAr,
    this.details = const {},
    this.statusCode,
  });

  factory ApiError.fromDio(DioException err) {
    final data = err.response?.data;
    if (data is Map) {
      return ApiError(
        code: (data['code'] as String?) ?? 'NETWORK_ERROR',
        messageAr: (data['message_ar'] as String?) ?? 'حدث خطأ في الشبكة',
        details: (data['details'] as Map?)?.cast<String, dynamic>() ?? {},
        statusCode: err.response?.statusCode,
      );
    }
    switch (err.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.receiveTimeout:
      case DioExceptionType.sendTimeout:
        return const ApiError(
          code: 'TIMEOUT',
          messageAr: 'انتهت مهلة الاتصال، تحقق من الإنترنت',
        );
      case DioExceptionType.connectionError:
        return const ApiError(
          code: 'OFFLINE',
          messageAr: 'لا يوجد اتصال بالإنترنت',
        );
      default:
        return ApiError(
          code: 'NETWORK_ERROR',
          messageAr: err.message ?? 'حدث خطأ في الشبكة',
          statusCode: err.response?.statusCode,
        );
    }
  }

  final String code;
  final String messageAr;
  final Map<String, dynamic> details;
  final int? statusCode;

  @override
  String toString() => 'ApiError($code): $messageAr';
}
