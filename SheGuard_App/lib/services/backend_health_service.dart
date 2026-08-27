import 'dart:async';
import 'dart:io';

import '../core/safety_types.dart';
import 'api_service.dart';

class BackendHealthService {
  BackendHealthService(this._api);

  final ApiService _api;

  Future<BackendStatus> check() async {
    try {
      final healthy = await _api.checkBackendHealth();
      return healthy ? BackendStatus.connected : BackendStatus.error;
    } on ApiException catch (e) {
      final message = e.message.toLowerCase();
      if (message.contains('timed out')) return BackendStatus.timeout;
      if (message.contains('internet') || message.contains('reach')) {
        return BackendStatus.offline;
      }
      return BackendStatus.error;
    } on TimeoutException {
      return BackendStatus.timeout;
    } on SocketException {
      return BackendStatus.offline;
    } catch (_) {
      return BackendStatus.error;
    }
  }
}
