class Evidence {
  const Evidence({
    this.evidenceId,
    required this.incidentId,
    this.imagePath,
    this.videoPath,
    this.cctvSource,
    this.createdAt,
    this.confidence,
    this.threatScore,
  });

  final int? evidenceId;
  final int incidentId;
  final String? imagePath;
  final String? videoPath;
  final String? cctvSource;
  final DateTime? createdAt;
  final double? confidence;
  final int? threatScore;

  factory Evidence.fromJson(Map<String, dynamic> json) {
    return Evidence(
      evidenceId: (json['evidence_id'] as num?)?.toInt(),
      incidentId: (json['incident_id'] as num?)?.toInt() ?? 0,
      imagePath: json['image_path'] as String?,
      videoPath: json['video_path'] as String?,
      cctvSource: json['cctv_source'] as String?,
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? ''),
      confidence: (json['confidence'] as num?)?.toDouble(),
      threatScore: (json['threat_score'] as num?)?.toInt(),
    );
  }
}
