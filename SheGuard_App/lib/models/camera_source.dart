class CameraSource {
  const CameraSource({
    this.cameraId,
    required this.cameraName,
    this.ipAddress,
    this.rtspUrl,
    this.latitude,
    this.longitude,
    this.onlineStatus = 'online',
  });

  final int? cameraId;
  final String cameraName;
  final String? ipAddress;
  final String? rtspUrl;
  final double? latitude;
  final double? longitude;
  final String onlineStatus;

  factory CameraSource.fromJson(Map<String, dynamic> json) {
    return CameraSource(
      cameraId: (json['camera_id'] as num?)?.toInt(),
      cameraName: json['camera_name'] as String? ?? '',
      ipAddress: json['ip_address'] as String?,
      rtspUrl: json['rtsp_url'] as String?,
      latitude: (json['latitude'] as num?)?.toDouble(),
      longitude: (json['longitude'] as num?)?.toDouble(),
      onlineStatus: json['online_status'] as String? ?? 'unknown',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'camera_name': cameraName,
      'ip_address': ipAddress,
      'rtsp_url': rtspUrl,
      'latitude': latitude,
      'longitude': longitude,
      'online_status': onlineStatus,
    };
  }
}
