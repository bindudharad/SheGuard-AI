import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

import '../models/incident.dart';
import '../models/evidence.dart';
import '../models/location_update.dart';
import 'api_service.dart';

class IncidentService {
  IncidentService(this._api);

  static const incidentListPath = '/incidents';

  final ApiService _api;

  static String incidentFolderPath(String incidentFolderId) {
    return '/uploads/incidents/$incidentFolderId/';
  }

  static String thumbnailPath(String incidentFolderId) {
    return '${incidentFolderPath(incidentFolderId)}thumbnail.jpg';
  }

  static String videoPath(String incidentFolderId) {
    return '${incidentFolderPath(incidentFolderId)}incident_video.mp4';
  }

  static String metadataPath(String incidentFolderId) {
    return '${incidentFolderPath(incidentFolderId)}metadata.json';
  }

  Future<Map<String, dynamic>> createSos({
    required int userId,
    LocationUpdate? location,
    bool silent = false,
  }) async {
    final incident = Incident(
      incidentType: silent ? 'silent_sos' : 'manual_sos',
      confidence: 1,
    );
    return _api.postJson(
      '$incidentListPath/create',
      incident.toSosJson(
        userId: userId,
        latitude: location?.latitude,
        longitude: location?.longitude,
        silent: silent,
      ),
    );
  }

  Future<List<Incident>> fetchHistory(int userId) async {
    final json = await _api.getJson('/incident/history/$userId');
    final rows = (json['incidents'] as List? ?? const []);
    return rows
        .map((item) => Incident.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<List<Incident>> fetchLiveIncidents() async {
    final json = await _api.getJson('/incident/live');
    final rows = (json['incidents'] as List? ?? const []);
    return rows
        .map((item) => Incident.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<List<Incident>> fetchIncidents({int limit = 50}) async {
    final payload = await _api.getAnyJson('$incidentListPath?limit=$limit');
    final rows = _incidentRows(payload);
    return rows
        .map((item) => Incident.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<Incident?> fetchLatestIncident() async {
    final json = await _api.getJson('$incidentListPath/latest?limit=1');
    final rows = (json['incidents'] as List? ?? const []);
    if (rows.isEmpty) return null;
    return Incident.fromJson(rows.first as Map<String, dynamic>);
  }

  Future<Incident> fetchIncident(int incidentId) async {
    final json = await _api.getJson('$incidentListPath/$incidentId');
    final incident = json['incident'] as Map<String, dynamic>;
    return Incident.fromJson(incident);
  }

  Future<Map<String, dynamic>?> fetchIncidentMetadata(Incident incident) {
    return _api.publicJson(incident.metadataReference);
  }

  Stream<Incident> watchIncidentEvents() async* {
    final uri = await _api.websocketUri('/ws/live');
    final channel = WebSocketChannel.connect(uri);
    try {
      await for (final message in channel.stream) {
        final incident = _incidentFromRealtimeMessage(message);
        if (incident != null) {
          yield incident;
        }
      }
    } finally {
      await channel.sink.close();
    }
  }

  Incident? _incidentFromRealtimeMessage(dynamic message) {
    try {
      final decoded = jsonDecode(message.toString());
      if (decoded is! Map<String, dynamic>) return null;
      final event = decoded['event']?.toString();
      if (event != 'incident.created' && event != 'incident.merged') {
        return null;
      }

      // The backend broadcasts the full creation response. The stable incident
      // object is nested under payload.incident and contains media URLs.
      final payload = decoded['payload'];
      if (payload is! Map<String, dynamic>) return null;
      final incidentJson = payload['incident'];
      if (incidentJson is Map<String, dynamic>) {
        return Incident.fromJson(incidentJson);
      }
      return Incident.fromJson(payload);
    } catch (_) {
      return null;
    }
  }

  Future<List<Evidence>> fetchEvidence(int incidentId) async {
    final json = await _api.getJson('/evidence/$incidentId');
    final rows = (json['evidence'] as List? ?? const []);
    return rows
        .map((item) => Evidence.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  List<dynamic> _incidentRows(dynamic payload) {
    if (payload is List) return payload;
    if (payload is Map<String, dynamic>) {
      return payload['incidents'] as List? ??
          payload['data'] as List? ??
          payload['results'] as List? ??
          const [];
    }
    return const [];
  }
}
