import 'package:flutter/foundation.dart';
import 'package:geocoding/geocoding.dart';

import '../models/location_update.dart';
import '../models/location_freshness.dart';
import '../services/location_service.dart';
import '../services/notification_service.dart';

class LocationProvider extends ChangeNotifier {
  LocationProvider(this._locationService, this._notifications);

  final LocationService _locationService;
  final NotificationService _notifications;

  LocationUpdate? lastLocation;
  bool tracking = false;
  bool permissionGranted = false;
  String? error;
  String? placeLabel;
  int failedUpdates = 0;
  DateTime? _firstTrackingFailureAt;
  DateTime? _lastErrorNotificationAt;

  LocationFreshness? get freshness => lastLocation == null
      ? null
      : LocationFreshness(
          timestamp: lastLocation!.timestamp,
          speed: lastLocation!.speed,
          accuracy: lastLocation!.accuracy,
        );

  Future<void> requestPermission() async {
    permissionGranted = await _locationService.ensurePermission();
    if (!permissionGranted) {
      error = 'GPS permission denied or location services disabled.';
      await _notifications.show(
        id: 2,
        title: 'GPS disabled',
        body: 'Enable location permissions for SheGuard safety tracking.',
      );
    } else {
      error = null;
    }
    notifyListeners();
  }

  Future<LocationUpdate?> sendNow(int userId, {String? sessionId}) async {
    try {
      final update = await _locationService.sendCurrentLocation(userId,
          sessionId: sessionId);
      debugPrint(
        'SheGuard manual location/update success: '
        '${update.latitude},${update.longitude}',
      );
      lastLocation = update;
      await _updatePlaceLabel(update);
      permissionGranted = true;
      failedUpdates = 0;
      error = null;
      notifyListeners();
      return update;
    } catch (e) {
      error = e.toString();
      notifyListeners();
      return null;
    }
  }

  Future<void> start(int userId, {String? sessionId}) async {
    permissionGranted = await _locationService.ensurePermission();
    if (!permissionGranted) {
      tracking = false;
      error = 'GPS permission denied or location services disabled.';
      await _showTrackingErrorNotification();
      notifyListeners();
      return;
    }

    tracking = true;
    error = null;
    notifyListeners();
    await _notifications.showLiveTrackingActive();
    _locationService.startTracking(
      userId: userId,
      sessionId: sessionId,
      onUpdate: (update) {
        debugPrint(
          'SheGuard background location/update success: '
          '${update.latitude},${update.longitude}',
        );
        lastLocation = update;
        _updatePlaceLabel(update).then((_) => notifyListeners());
        failedUpdates = 0;
        _firstTrackingFailureAt = null;
        error = null;
        notifyListeners();
      },
      onError: (e) async {
        failedUpdates += 1;
        _firstTrackingFailureAt ??= DateTime.now();
        error = e.toString();
        await _showTrackingErrorNotification();
        notifyListeners();
      },
    );
  }

  void stop() {
    tracking = false;
    failedUpdates = 0;
    _firstTrackingFailureAt = null;
    _locationService.stopTracking();
    notifyListeners();
  }

  Future<void> _showTrackingErrorNotification() async {
    final now = DateTime.now();
    final firstFailureAt = _firstTrackingFailureAt;
    if (firstFailureAt == null ||
        now.difference(firstFailureAt) < const Duration(minutes: 2)) {
      debugPrint(
        'SheGuard GPS retry active; suppressing interruption alert. '
        'failedUpdates=$failedUpdates',
      );
      return;
    }
    final last = _lastErrorNotificationAt;
    if (last != null && now.difference(last).inSeconds < 45) return;
    _lastErrorNotificationAt = now;
    await _notifications.show(
      id: 3,
      title: 'Tracking interrupted',
      body: 'SheGuard could not update GPS. Check permissions and network.',
    );
  }

  Future<void> _updatePlaceLabel(LocationUpdate update) async {
    try {
      final places = await placemarkFromCoordinates(
        update.latitude,
        update.longitude,
      );
      if (places.isEmpty) return;
      final place = places.first;
      final locality = [
        place.locality,
        place.administrativeArea,
      ].where((part) => part != null && part.trim().isNotEmpty).join(', ');
      placeLabel = locality.isEmpty ? 'Location active' : locality;
    } catch (_) {
      placeLabel = 'Location active';
    }
  }
}
