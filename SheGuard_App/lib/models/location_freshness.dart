class LocationFreshness {
  const LocationFreshness({
    required this.timestamp,
    this.speed,
    this.accuracy,
  });

  final DateTime timestamp;
  final double? speed;
  final double? accuracy;

  Duration get age => DateTime.now().difference(timestamp);

  bool get isFresh => age.inSeconds <= 30;

  String get ageLabel {
    if (age.inSeconds < 5) return 'Just now';
    if (age.inSeconds < 60) return '${age.inSeconds}s ago';
    if (age.inMinutes < 60) return '${age.inMinutes}m ago';
    return '${age.inHours}h ago';
  }
}
