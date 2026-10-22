import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';
import '../../../shared/models/comms_models.dart';

class AnnouncementsApi {
  AnnouncementsApi(this._dio);
  final Dio _dio;

  Future<List<AnnouncementOut>> list({int page = 1, int limit = 20}) async {
    final r = await _dio.get('/announcements', queryParameters: {'page': page, 'limit': limit});
    final list = (r.data as List).cast<Map<String, dynamic>>();
    return list.map(AnnouncementOut.fromJson).toList();
  }

  Future<void> markRead(String id) async {
    await _dio.post('/announcements/$id/read');
  }
}

class NotificationsApi {
  NotificationsApi(this._dio);
  final Dio _dio;

  Future<NotificationList> list({bool unreadOnly = false, int page = 1}) async {
    final r = await _dio.get('/notifications', queryParameters: {
      'unread_only': unreadOnly,
      'page': page,
    });
    return NotificationList.fromJson(r.data as Map<String, dynamic>);
  }

  Future<void> markAllRead() => _dio.post('/notifications/read-all');
  Future<void> markOneRead(String id) => _dio.post('/notifications/$id/read');
}

final announcementsApiProvider = Provider<AnnouncementsApi>((ref) {
  final dio = ref.watch(dioProvider);
  return AnnouncementsApi(dio);
});

final notificationsApiProvider = Provider<NotificationsApi>((ref) {
  final dio = ref.watch(dioProvider);
  return NotificationsApi(dio);
});
