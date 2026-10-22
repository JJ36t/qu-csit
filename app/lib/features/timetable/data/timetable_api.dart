import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';
import '../../../shared/models/timetable_models.dart';

class TimetableApi {
  TimetableApi(this._dio);
  final Dio _dio;

  Future<List<TimetableDay>> getTimetable({
    required String from,
    required String to,
  }) async {
    final r = await _dio.get('/timetable', queryParameters: {'from': from, 'to': to});
    final list = (r.data as List).cast<Map<String, dynamic>>();
    return list.map(TimetableDay.fromJson).toList();
  }

  Future<List<TimetableChangeOut>> getChanges({
    required String from,
    required String to,
  }) async {
    final r = await _dio.get('/timetable/changes',
        queryParameters: {'from': from, 'to': to});
    final list = (r.data as List).cast<Map<String, dynamic>>();
    return list.map(TimetableChangeOut.fromJson).toList();
  }
}

final timetableApiProvider = Provider<TimetableApi>((ref) {
  final dio = ref.watch(dioProvider);
  return TimetableApi(dio);
});
