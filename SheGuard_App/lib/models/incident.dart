import 'evidence.dart';

class Incident {
  const Incident({
    this.incidentId,
    this.userId,
    required this.incidentType,
    required this.confidence,
    this.threatScore,
    this.aiSummary,
    this.latitude,
    this.longitude,
    this.createdAt,
    this.threatLevel,
    this.kidnapSuspicionScore,
    this.aiProvider,
    this.explanation,
    this.cameraId,
    this.imagePath,
    this.videoPath,
    this.imageUrl,
    this.videoUrl,
    this.metadataPath,
    this.metadataUrl,
    this.incidentFolderId,
    this.status,
    this.evidenceAvailable = false,
    this.evidence = const [],
    // Phase G new fields
    this.riskScore,
    this.riskLevel,
    this.behaviors = const [],
    this.followingRelationship,
    this.agentTimeline = const [],
    this.x402Metadata,
    this.intelligenceResult,
    this.aiReasoning,
  });

  final int? incidentId;
  final int? userId;
  final String incidentType;
  final double confidence;
  final int? threatScore;
  final String? aiSummary;
  final double? latitude;
  final double? longitude;
  final DateTime? createdAt;
  final String? threatLevel;
  final int? kidnapSuspicionScore;
  final String? aiProvider;
  final String? explanation;
  final String? cameraId;
  final String? imagePath;
  final String? videoPath;
  final String? imageUrl;
  final String? videoUrl;
  final String? metadataPath;
  final String? metadataUrl;
  final String? incidentFolderId;
  final String? status;
  final bool evidenceAvailable;
  final List<Evidence> evidence;

  // Phase G new fields
  final double? riskScore;
  final String? riskLevel;
  final List<dynamic> behaviors;
  final Map<String, dynamic>? followingRelationship;
  final List<dynamic> agentTimeline;
  final Map<String, dynamic>? x402Metadata;
  final Map<String, dynamic>? intelligenceResult;
  final String? aiReasoning;

  factory Incident.fromJson(Map<String, dynamic> json) {
    return Incident(
      incidentId: (json['incident_id'] as num?)?.toInt() ??
          (json['id'] as num?)?.toInt(),
      userId: (json['user_id'] as num?)?.toInt(),
      incidentType:
          _string(json, ['incident_type', 'type', 'label']) ?? 'unknown',
      confidence: _normalizedConfidence(json['confidence']),
      threatScore: (json['threat_score'] as num?)?.toInt(),
      aiSummary: _string(json, ['ai_summary', 'summary', 'description']),
      latitude: (json['latitude'] as num?)?.toDouble(),
      longitude: (json['longitude'] as num?)?.toDouble(),
      createdAt: _date(json, ['created_at', 'timestamp', 'detected_at']),
      threatLevel: _string(json, ['threat_level']),
      kidnapSuspicionScore: (json['kidnap_suspicion_score'] as num?)?.toInt(),
      aiProvider: _string(json, ['ai_provider']),
      explanation: _string(json, ['explanation']),
      cameraId: json['camera_id']?.toString(),
      imagePath: _string(json, ['image_path', 'image', 'thumbnail_path']),
      videoPath: _string(json, ['video_path', 'video']),
      imageUrl: _string(json, ['image_url', 'thumbnail_url', 'thumbnail']),
      videoUrl: _string(json, ['video_url']),
      metadataPath: _string(json, ['metadata_path', 'metadata']),
      metadataUrl: _string(json, ['metadata_url']),
      incidentFolderId: _incidentFolderId(json),
      status: _string(json, ['status']),
      evidenceAvailable: (json['evidence_available'] as bool?) ??
          (json['image_url'] != null ||
              json['video_url'] != null ||
              json['image_path'] != null ||
              json['video_path'] != null ||
              _incidentFolderId(json) != null),
      // Phase G new fields
      riskScore: (json['risk_score'] as num?)?.toDouble(),
      riskLevel: _string(json, ['risk_level']),
      behaviors: (json['behaviors'] as List?) ?? const [],
      followingRelationship: json['following_relationship'] as Map<String, dynamic>?,
      agentTimeline: (json['agent_timeline'] as List?) ?? const [],
      x402Metadata: json['x402_metadata'] as Map<String, dynamic>?,
      intelligenceResult: json['intelligence_result'] as Map<String, dynamic>?,
      aiReasoning: _string(json, ['ai_summary', 'explanation', 'summary']),
    );
  }

  Incident copyWith({
    bool? evidenceAvailable,
    List<Evidence>? evidence,
  }) {
    return Incident(
      incidentId: incidentId,
      userId: userId,
      incidentType: incidentType,
      confidence: confidence,
      threatScore: threatScore,
      aiSummary: aiSummary,
      latitude: latitude,
      longitude: longitude,
      createdAt: createdAt,
      threatLevel: threatLevel,
      kidnapSuspicionScore: kidnapSuspicionScore,
      aiProvider: aiProvider,
      explanation: explanation,
      cameraId: cameraId,
      imagePath: imagePath,
      videoPath: videoPath,
      imageUrl: imageUrl,
      videoUrl: videoUrl,
      metadataPath: metadataPath,
      metadataUrl: metadataUrl,
      incidentFolderId: incidentFolderId,
      status: status,
      evidenceAvailable: evidenceAvailable ?? this.evidenceAvailable,
      evidence: evidence ?? this.evidence,
      riskScore: riskScore,
      riskLevel: riskLevel,
      behaviors: behaviors,
      followingRelationship: followingRelationship,
      agentTimeline: agentTimeline,
      x402Metadata: x402Metadata,
      intelligenceResult: intelligenceResult,
      aiReasoning: aiReasoning,
    );
  }

  String? get thumbnailReference {
    return imageUrl ??
        imagePath ??
        _incidentFolderFile(incidentFolderId, 'thumbnail.jpg');
  }

  String? get videoReference {
    return videoUrl ??
        videoPath ??
        _incidentFolderFile(incidentFolderId, 'incident_video.mp4');
  }

  String? get metadataReference {
    return metadataUrl ??
        metadataPath ??
        _incidentFolderFile(incidentFolderId, 'metadata.json');
  }

  Map<String, dynamic> toSosJson({
    required int userId,
    required double? latitude,
    required double? longitude,
    bool silent = false,
  }) {
    return {
      'user_id': userId,
      'incident_type': silent ? 'silent_sos' : 'manual_sos',
      'confidence': 1.0,
      'threat_score': 10,
      'ai_summary': silent
          ? 'Silent emergency alert triggered from SheGuard mobile app.'
          : 'SOS emergency alert triggered from SheGuard mobile app.',
      'latitude': latitude,
      'longitude': longitude,
      'send_alert': true,
    };
  }
}

String? _string(Map<String, dynamic> json, List<String> keys) {
  for (final key in keys) {
    final value = json[key];
    if (value != null && value.toString().trim().isNotEmpty) {
      return value.toString();
    }
  }
  return null;
}

DateTime? _date(Map<String, dynamic> json, List<String> keys) {
  final value = _string(json, keys);
  return value == null ? null : DateTime.tryParse(value);
}

double _normalizedConfidence(dynamic value) {
  final confidence = value is num ? value.toDouble() : 0.0;
  return confidence > 1 ? confidence / 100 : confidence;
}

String? _incidentFolderId(Map<String, dynamic> json) {
  final explicit = _string(json, [
    'incident_folder_id',
    'folder_id',
    'storage_id',
    'incident_dir',
    'folder',
  ]);
  if (explicit != null) return _folderName(explicit);

  for (final key in [
    'image_url',
    'video_url',
    'preview_image',
    'image_path',
    'video_path',
    'metadata_path',
    'thumbnail',
  ]) {
    final folder = _folderFromIncidentPath(json[key]?.toString());
    if (folder != null) return folder;
  }
  return null;
}

String? _folderFromIncidentPath(String? value) {
  if (value == null || value.trim().isEmpty) return null;
  final normalized = value.replaceAll('\\', '/');
  const marker = '/uploads/incidents/';
  var index = normalized.indexOf(marker);
  var start = -1;
  if (index >= 0) {
    start = index + marker.length;
  } else if (normalized.startsWith('uploads/incidents/')) {
    start = 'uploads/incidents/'.length;
  } else if (normalized.startsWith('/uploads/incidents/')) {
    start = '/uploads/incidents/'.length;
  }
  if (start < 0 || start >= normalized.length) return null;
  final folder = normalized.substring(start).split('/').first;
  return _folderName(folder);
}

String? _folderName(String value) {
  final normalized = value.replaceAll('\\', '/').split('/').last.trim();
  return normalized.isEmpty ? null : normalized;
}

String? _incidentFolderFile(String? folderId, String fileName) {
  if (folderId == null || folderId.trim().isEmpty) return null;
  return '/uploads/incidents/${folderId.trim()}/$fileName';
}
