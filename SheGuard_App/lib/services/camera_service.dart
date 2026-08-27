import '../models/camera_source.dart';
import 'api_service.dart';

class CameraService {
  CameraService(this._api);

  final ApiService _api;

  Future<CameraSource> registerCamera(CameraSource camera) async {
    final json = await _api.postJson('/camera/register', camera.toJson());
    return CameraSource.fromJson(json);
  }

  Future<List<CameraSource>> listCameras() async {
    final json = await _api.getJson('/camera/list');
    final rows = (json['cameras'] as List? ?? const []);
    return rows
        .map((item) => CameraSource.fromJson(item as Map<String, dynamic>))
        .toList();
  }
}
