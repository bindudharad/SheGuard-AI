import 'package:flutter_test/flutter_test.dart';
import 'package:sheguard_app/models/emergency_contact.dart';
import 'package:sheguard_app/models/incident.dart';
import 'package:sheguard_app/models/location_update.dart';

void main() {
  test('location update payload matches SheGuard_AI schema', () {
    final update = LocationUpdate(
      userId: 7,
      latitude: 12.34,
      longitude: 77.56,
      speed: 2.5,
      timestamp: DateTime.utc(2026, 5, 10, 10),
    );

    expect(update.toJson(), containsPair('user_id', 7));
    expect(update.toJson(), containsPair('latitude', 12.34));
    expect(update.toJson(), containsPair('longitude', 77.56));
    expect(update.toJson(), containsPair('speed', 2.5));
    expect(update.toJson(), contains('timestamp'));
  });

  test('SOS payload selects normal and silent incident types', () {
    const incident = Incident(incidentType: 'manual_sos', confidence: 1);

    expect(
      incident.toSosJson(userId: 1, latitude: 1, longitude: 2)['incident_type'],
      'manual_sos',
    );
    expect(
      incident.toSosJson(
        userId: 1,
        latitude: 1,
        longitude: 2,
        silent: true,
      )['incident_type'],
      'silent_sos',
    );
  });

  test('incident parsing accepts extended SheGuard_AI fields', () {
    final incident = Incident.fromJson({
      'incident_id': 12,
      'user_id': 7,
      'incident_type': 'attack',
      'confidence': 0.91,
      'threat_score': 9,
      'threat_level': 'critical',
      'kidnap_suspicion_score': 4,
      'ai_provider': 'gru',
      'explanation': 'High motion anomaly',
      'camera_id': 'cam-1',
    });

    expect(incident.threatLevel, 'critical');
    expect(incident.kidnapSuspicionScore, 4);
    expect(incident.cameraId, 'cam-1');
  });

  test('incident parsing derives uploads incident storage URLs', () {
    final incident = Incident.fromJson({
      'incident_id': 85,
      'incident_type': 'fall',
      'confidence': 90,
      'image_path':
          r'C:\Programs\codex\SheGuard\SheGuard_Backend\uploads\incidents\incident_20260513_033656\thumbnail.jpg',
      'video_path':
          r'C:\Programs\codex\SheGuard\SheGuard_Backend\uploads\incidents\incident_20260513_033656\incident_video.mp4',
      'metadata_path':
          r'C:\Programs\codex\SheGuard\SheGuard_Backend\uploads\incidents\incident_20260513_033656\metadata.json',
    });

    expect(incident.confidence, 0.9);
    expect(incident.incidentFolderId, 'incident_20260513_033656');
    expect(
      incident.thumbnailReference,
      r'C:\Programs\codex\SheGuard\SheGuard_Backend\uploads\incidents\incident_20260513_033656\thumbnail.jpg',
    );
    expect(
      incident.videoReference,
      r'C:\Programs\codex\SheGuard\SheGuard_Backend\uploads\incidents\incident_20260513_033656\incident_video.mp4',
    );
    expect(
      incident.metadataReference,
      r'C:\Programs\codex\SheGuard\SheGuard_Backend\uploads\incidents\incident_20260513_033656\metadata.json',
    );
  });

  test('contact local metadata does not alter backend payload shape', () {
    const contact = EmergencyContact(
      contactId: 3,
      userId: 1,
      contactName: 'Asha',
      relation: 'Sister',
      phoneNumber: '9999999999',
      isFavorite: true,
      localName: 'Asha local',
    );

    expect(contact.displayName, 'Asha local');
    expect(contact.toJson().keys.toSet(), {
      'user_id',
      'contact_name',
      'relation',
      'phone_number',
    });
  });
}
