import 'dart:math' as math;

import 'location_update.dart';

class EmergencyEvent {
  const EmergencyEvent({
    required this.eventId,
    required this.userId,
    required this.incidentType,
    required this.createdAt,
    this.incidentId,
    this.sessionId,
    this.sessionToken,
    this.latitude,
    this.longitude,
    this.confidence,
    this.trackingUrl,
    this.evidenceLinks = const [],
    this.details = const {},
  });

  final String eventId;
  final int userId;
  final String incidentType;
  final DateTime createdAt;
  final int? incidentId;
  final String? sessionId;
  final String? sessionToken;
  final double? latitude;
  final double? longitude;
  final double? confidence;
  final String? trackingUrl;
  final List<String> evidenceLinks;
  final Map<String, dynamic> details;

  factory EmergencyEvent.fromJson(Map<String, dynamic> json) {
    final payload = (json['incident'] as Map?)?.cast<String, dynamic>() ??
        (json['event'] as Map?)?.cast<String, dynamic>() ??
        json;
    final evidence = payload['evidence_links'] ??
        payload['evidence'] ??
        payload['evidence_urls'] ??
        const [];
    return EmergencyEvent(
      eventId: (payload['event_id'] ??
              payload['id'] ??
              payload['incident_id'] ??
              DateTime.now().toUtc().millisecondsSinceEpoch)
          .toString(),
      userId: (payload['user_id'] as num?)?.toInt() ??
          (payload['victim_user_id'] as num?)?.toInt() ??
          0,
      incidentId: (payload['incident_id'] as num?)?.toInt(),
      sessionId: payload['session_id']?.toString(),
      sessionToken: payload['session_token']?.toString(),
      incidentType: payload['incident_type']?.toString() ??
          payload['type']?.toString() ??
          'ai_cctv_emergency',
      latitude: (payload['latitude'] as num?)?.toDouble(),
      longitude: (payload['longitude'] as num?)?.toDouble(),
      confidence: (payload['confidence'] as num?)?.toDouble(),
      trackingUrl: payload['tracking_url']?.toString(),
      evidenceLinks: evidence is List
          ? evidence.map((item) => item.toString()).toList()
          : const [],
      createdAt: DateTime.tryParse(
            payload['created_at']?.toString() ??
                payload['timestamp']?.toString() ??
                '',
          ) ??
          DateTime.now(),
      details: Map<String, dynamic>.from(payload),
    );
  }

  bool get hasLocation => latitude != null && longitude != null;

  bool isForUser(int currentUserId) {
    return userId == 0 || userId == currentUserId;
  }

  bool isNear(LocationUpdate? current, {double maxMeters = 1500}) {
    if (!hasLocation || current == null) return true;
    return _distanceMeters(
          latitude!,
          longitude!,
          current.latitude,
          current.longitude,
        ) <=
        maxMeters;
  }

  Map<String, dynamic> toEmergencyStartPayload({
    required int currentUserId,
    required String sessionId,
    LocationUpdate? location,
  }) {
    return {
      'user_id': currentUserId,
      'session_id': sessionId,
      'incident_id': incidentId,
      'event_id': eventId,
      'incident_type': incidentType,
      'source': 'ai_cctv',
      'session_token': sessionToken,
      'event_latitude': latitude,
      'event_longitude': longitude,
      'confidence': confidence,
      'created_at': createdAt.toUtc().toIso8601String(),
      if (location != null) 'current_location': location.toJson(),
    };
  }

  Map<String, dynamic> toJson() {
    return {
      'event_id': eventId,
      'user_id': userId,
      'incident_id': incidentId,
      'session_id': sessionId,
      'session_token': sessionToken,
      'incident_type': incidentType,
      'latitude': latitude,
      'longitude': longitude,
      'confidence': confidence,
      'tracking_url': trackingUrl,
      'evidence_links': evidenceLinks,
      'created_at': createdAt.toUtc().toIso8601String(),
      'details': details,
    };
  }

  Map<String, dynamic> toParentPayload({
    required String victimName,
    required String sessionId,
    LocationUpdate? location,
    String? trackingUrlOverride,
  }) {
    return {
      'victim_name': victimName,
      'session_id': sessionId,
      'incident_id': incidentId,
      'incident_type': incidentType,
      'tracking_url': trackingUrlOverride ?? trackingUrl,
      'evidence_links': evidenceLinks,
      'detected_at': createdAt.toUtc().toIso8601String(),
      if (location != null) 'location': location.toJson(),
    };
  }

  static double _distanceMeters(
    double lat1,
    double lon1,
    double lat2,
    double lon2,
  ) {
    const earthRadius = 6371000.0;
    final dLat = _radians(lat2 - lat1);
    final dLon = _radians(lon2 - lon1);
    final a = math.sin(dLat / 2) * math.sin(dLat / 2) +
        math.cos(_radians(lat1)) *
            math.cos(_radians(lat2)) *
            math.sin(dLon / 2) *
            math.sin(dLon / 2);
    return earthRadius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a));
  }

  static double _radians(double degrees) => degrees * math.pi / 180;
}
