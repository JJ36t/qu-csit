import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';
import 'session_models.dart';

class AttendanceApi {
  AttendanceApi(this._dio);
  final Dio _dio;

  /// POST /sessions/{id}/open
  Future<SessionOpenResponse> openSession(String sessionId) async {
    final r = await _dio.post('/sessions/$sessionId/open');
    return SessionOpenResponse.fromJson(r.data as Map<String, dynamic>);
  }

  /// POST /sessions/{id}/close
  Future<SessionCloseResponse> closeSession(String sessionId) async {
    final r = await _dio.post('/sessions/$sessionId/close');
    return SessionCloseResponse.fromJson(r.data as Map<String, dynamic>);
  }

  /// GET /sessions/{id}/live
  Future<SessionLiveResponse> getLive(String sessionId) async {
    final r = await _dio.get('/sessions/$sessionId/live');
    return SessionLiveResponse.fromJson(r.data as Map<String, dynamic>);
  }

  /// POST /attendance/scan
  Future<AttendanceScanResponse> scan({
    required String sessionId,
    required String token,
    String? deviceFingerprint,
    Map<String, dynamic>? location,
  }) async {
    final r = await _dio.post('/attendance/scan', data: {
      'session_id': sessionId,
      'token': token,
      if (deviceFingerprint != null) 'device_id': deviceFingerprint,
      if (location != null) 'location': location,
    });
    return AttendanceScanResponse.fromJson(r.data as Map<String, dynamic>);
  }
}

final attendanceApiProvider = Provider<AttendanceApi>((ref) {
  final dio = ref.watch(dioProvider);
  return AttendanceApi(dio);
});
