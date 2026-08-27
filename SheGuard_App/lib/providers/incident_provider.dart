import 'dart:async';

import 'package:flutter/foundation.dart';

import '../models/incident.dart';
import '../models/evidence.dart';
import '../models/location_update.dart';
import '../services/incident_service.dart';
import '../services/notification_service.dart';

class IncidentProvider extends ChangeNotifier {
  IncidentProvider(this._incidentService, this._notifications);

  final IncidentService _incidentService;
  final NotificationService _notifications;

  List<Incident> history = [];
  List<Incident> liveIncidents = [];
  bool loading = false;
  bool emergencyMode = false;
  bool silentEmergency = false;
  bool realtimeConnected = false;
  String? error;
  StreamSubscription<Incident>? _realtimeSubscription;
  Timer? _reconnectTimer;
  Timer? _pollingTimer;
  bool _realtimeRequested = false;
  bool _initialFeedLoaded = false;
  final Set<String> _knownIncidentKeys = <String>{};
  final Set<String> _emergencyPopupKeys = <String>{};
  Incident? pendingEmergencyIncident;

  @override
  void dispose() {
    _realtimeSubscription?.cancel();
    _reconnectTimer?.cancel();
    _pollingTimer?.cancel();
    super.dispose();
  }

  Future<bool> triggerSos({
    required int userId,
    LocationUpdate? location,
    bool silent = false,
  }) async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      await _incidentService.createSos(
        userId: userId,
        location: location,
        silent: silent,
      );
      emergencyMode = true;
      silentEmergency = silent;
      await _notifications.show(
        id: 4,
        title: silent ? 'Silent SOS activated' : 'SOS activated',
        body: 'SheGuard_AI received your emergency alert.',
      );
      return true;
    } catch (e) {
      error = e.toString();
      await _notifications.show(
        id: 5,
        title: 'SOS failed',
        body:
            'Could not reach SheGuard_AI. Keep trying or call local emergency services.',
      );
      return false;
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  void beginSos() {
    loading = true;
    error = null;
    notifyListeners();
  }

  void completeSos({required bool silent}) {
    loading = false;
    emergencyMode = true;
    silentEmergency = silent;
    error = null;
    notifyListeners();
  }

  void failSos(String message) {
    loading = false;
    error = message;
    notifyListeners();
  }

  Future<void> loadHistory(int userId) async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      history = await _incidentService.fetchHistory(userId);
    } catch (e) {
      error = e.toString();
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<List<Evidence>> loadEvidence(Incident incident) async {
    final id = incident.incidentId;
    if (id == null) return [];
    try {
      final evidence = await _incidentService.fetchEvidence(id);
      history = history
          .map((item) => item.incidentId == id
              ? item.copyWith(
                  evidenceAvailable: evidence.isNotEmpty,
                  evidence: evidence,
                )
              : item)
          .toList();
      notifyListeners();
      return evidence;
    } catch (e) {
      error = e.toString();
      notifyListeners();
      return [];
    }
  }

  Future<void> loadLive() async {
    try {
      liveIncidents = await _incidentService.fetchLiveIncidents();
      error = null;
    } catch (e) {
      error = e.toString();
    }
    notifyListeners();
  }

  Future<void> loadIncidentFeed({int limit = 50}) async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      liveIncidents = await _incidentService.fetchIncidents(limit: limit);
      for (final incident in liveIncidents) {
        _knownIncidentKeys.add(_incidentKey(incident));
      }
      _initialFeedLoaded = true;
    } catch (e) {
      error = e.toString();
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  void startIncidentRealtime() {
    _realtimeRequested = true;
    _pollingTimer ??= Timer.periodic(
      const Duration(seconds: 5),
      (_) => refreshIncidentFeedSilently(),
    );
    if (_realtimeSubscription != null) return;
    _connectIncidentRealtime();
  }

  Future<void> refreshIncidentFeedSilently() async {
    if (!_realtimeRequested) return;
    try {
      final latest = await _incidentService.fetchIncidents();
      final newIncidents = <Incident>[];
      for (final incident in latest) {
        final key = _incidentKey(incident);
        if (_initialFeedLoaded && !_knownIncidentKeys.contains(key)) {
          newIncidents.add(incident);
        }
        _knownIncidentKeys.add(key);
      }
      liveIncidents = latest;
      if (newIncidents.isNotEmpty) {
        _markPendingEmergency(newIncidents.first);
      }
      _initialFeedLoaded = true;
      error = null;
      notifyListeners();
    } catch (e) {
      error = e.toString();
      notifyListeners();
    }
  }

  void _connectIncidentRealtime() {
    _reconnectTimer?.cancel();
    _realtimeSubscription = _incidentService.watchIncidentEvents().listen(
      _upsertLiveIncident,
      onError: (Object e) {
        realtimeConnected = false;
        error = e.toString();
        notifyListeners();
        _scheduleRealtimeReconnect();
      },
      onDone: () {
        realtimeConnected = false;
        _realtimeSubscription = null;
        notifyListeners();
        _scheduleRealtimeReconnect();
      },
    );
    realtimeConnected = true;
    notifyListeners();
  }

  void stopIncidentRealtime() {
    _realtimeRequested = false;
    _reconnectTimer?.cancel();
    _pollingTimer?.cancel();
    _pollingTimer = null;
    _realtimeSubscription?.cancel();
    _realtimeSubscription = null;
    realtimeConnected = false;
    notifyListeners();
  }

  void _scheduleRealtimeReconnect() {
    if (!_realtimeRequested || _reconnectTimer != null) return;
    _reconnectTimer = Timer(const Duration(seconds: 5), () {
      _reconnectTimer = null;
      if (_realtimeRequested && _realtimeSubscription == null) {
        _connectIncidentRealtime();
      }
    });
  }

  void _upsertLiveIncident(Incident incident) {
    final id = incident.incidentId;
    if (id == null) {
      liveIncidents = [incident, ...liveIncidents];
    } else {
      liveIncidents = [
        incident,
        ...liveIncidents.where((item) => item.incidentId != id),
      ];
    }
    liveIncidents.sort((a, b) {
      final aTime = a.createdAt ?? DateTime.fromMillisecondsSinceEpoch(0);
      final bTime = b.createdAt ?? DateTime.fromMillisecondsSinceEpoch(0);
      return bTime.compareTo(aTime);
    });
    _knownIncidentKeys.add(_incidentKey(incident));
    _markPendingEmergency(incident);
    error = null;
    notifyListeners();
  }

  void emergencyPopupHandled(Incident incident) {
    final key = _incidentKey(incident);
    _emergencyPopupKeys.add(key);
    if (pendingEmergencyIncident != null &&
        _incidentKey(pendingEmergencyIncident!) == key) {
      pendingEmergencyIncident = null;
    }
    notifyListeners();
  }

  void _markPendingEmergency(Incident incident) {
    final key = _incidentKey(incident);
    if (_emergencyPopupKeys.contains(key)) return;
    pendingEmergencyIncident = incident;
  }

  String _incidentKey(Incident incident) {
    return incident.incidentId?.toString() ??
        '${incident.incidentType}-${incident.createdAt?.toIso8601String() ?? ''}-${incident.thumbnailReference ?? incident.videoReference ?? incident.metadataReference ?? ''}';
  }

  void clearEmergencyMode() {
    emergencyMode = false;
    silentEmergency = false;
    notifyListeners();
  }
}
