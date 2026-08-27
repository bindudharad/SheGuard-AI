enum BackendStatus { unknown, connected, offline, timeout, error }

enum ProtectionStatus { 
  inactive, 
  monitoring, 
  helpPending, 
  emergency, 
  silentEmergency 
}

enum TrackingStatus {
  idle,
  starting,
  active,
  paused,
  offline,
  stopping,
  stopped,
  error,
}

extension BackendStatusLabel on BackendStatus {
  String get label {
    switch (this) {
      case BackendStatus.connected:
        return 'Connected';
      case BackendStatus.offline:
        return 'Offline';
      case BackendStatus.timeout:
        return 'Timed out';
      case BackendStatus.error:
        return 'Needs attention';
      case BackendStatus.unknown:
        return 'Checking';
    }
  }
}

extension ProtectionStatusLabel on ProtectionStatus {
  String get label {
    switch (this) {
      case ProtectionStatus.inactive:
        return 'Protection inactive';
      case ProtectionStatus.monitoring:
        return 'Active protection';
      case ProtectionStatus.helpPending:
        return 'HELP pending - cancel to stop';
      case ProtectionStatus.emergency:
        return 'Emergency mode';
      case ProtectionStatus.silentEmergency:
        return 'Silent emergency';
    }
  }
}

extension TrackingStatusLabel on TrackingStatus {
  String get label {
    switch (this) {
      case TrackingStatus.idle:
        return 'Idle';
      case TrackingStatus.starting:
        return 'Starting tracking...';
      case TrackingStatus.active:
        return 'Tracking active';
      case TrackingStatus.paused:
        return 'Tracking paused';
      case TrackingStatus.offline:
        return 'Offline - queuing updates';
      case TrackingStatus.stopping:
        return 'Stopping...';
      case TrackingStatus.stopped:
        return 'Tracking stopped';
      case TrackingStatus.error:
        return 'Tracking error';
    }
  }
}
