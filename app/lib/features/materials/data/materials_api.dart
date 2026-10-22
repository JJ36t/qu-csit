import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';
import 'materials_models.dart';

class MaterialsApi {
  MaterialsApi(this._dio);
  final Dio _dio;

  Future<List<MaterialWithDownload>> listForOffering({
    required String offeringId,
    int? weekNo,
  }) async {
    final r = await _dio.get('/offerings/$offeringId/materials', queryParameters: {
      if (weekNo != null) 'week_no': weekNo,
    });
    final list = (r.data as List).cast<Map<String, dynamic>>();
    return list.map(MaterialWithDownload.fromJson).toList();
  }

  Future<FileDownloadResponse> getDownloadUrl(String fileId) async {
    final r = await _dio.get('/files/$fileId/download');
    return FileDownloadResponse.fromJson(r.data as Map<String, dynamic>);
  }
}

final materialsApiProvider = Provider<MaterialsApi>((ref) {
  final dio = ref.watch(dioProvider);
  return MaterialsApi(dio);
});
