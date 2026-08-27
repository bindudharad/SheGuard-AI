class LocationUpdate {
  const LocationUpdate({
    required this.userId,
    required this.latitude,
    required this.longitude,
    required this.timestamp,
    this.sessionId,
    this.speed = 0,
    this.heading,
    this.accuracy,
    this.battery,
  });

  final int userId;
  final String? sessionId;
  final double latitude;
  final double longitude;
  final DateTime timestamp;
  final double speed;
  final double? heading;
  final double? accuracy;
  final int? battery;

  factory LocationUpdate.fromJson(Map<String, dynamic> json) {
    return LocationUpdate(
      userId: json['user_id'] as int? ?? 0,
      sessionId: json['session_id'] as String?,
      latitude: (json['latitude'] as num?)?.toDouble() ?? 0,
      longitude: (json['longitude'] as num?)?.toDouble() ?? 0,
      speed: (json['speed'] as num?)?.toDouble() ?? 0,
      heading: (json['heading'] as num?)?.toDouble(),
      accuracy: (json['accuracy'] as num?)?.toDouble(),
      battery: (json['battery'] as num?)?.toInt(),
      timestamp: DateTime.tryParse(json['timestamp'] as String? ?? '') ??
          DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'user_id': userId,
      if (sessionId != null) 'session_id': sessionId,
      'latitude': latitude,
      'longitude': longitude,
      'speed': speed,
      if (heading != null) 'heading': heading,
      if (battery != null) 'battery': battery,
      if (accuracy != null) 'accuracy': accuracy,
      'timestamp': timestamp.toUtc().toIso8601String(),
    };
  }
}
