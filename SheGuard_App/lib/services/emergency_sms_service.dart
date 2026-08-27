import 'package:flutter/foundation.dart';
import 'package:telephony/telephony.dart';

import '../models/emergency_contact.dart';
import '../models/location_update.dart';

class EmergencySmsResult {
  const EmergencySmsResult({
    required this.attempted,
    required this.sent,
    required this.failed,
  });

  final int attempted;
  final int sent;
  final int failed;

  bool get anySent => sent > 0;
}

class EmergencySmsService {
  EmergencySmsService({Telephony? telephony})
      : _telephony = telephony ?? Telephony.instance;

  final Telephony _telephony;

  static String messageFor({
    LocationUpdate? location,
    required String userName,
    String? trackingUrl,
    String? incidentType,
    List<String> evidenceLinks = const [],
    DateTime? incidentTime,
  }) {
    final evidenceText = evidenceLinks.isEmpty
        ? ''
        : '\n\u{1F4CE} Evidence:\n${evidenceLinks.take(3).join('\n')}\n';
    final typeText = incidentType == null || incidentType.trim().isEmpty
        ? ''
        : '\nEmergency type: $incidentType\n';
    final timeText = incidentTime == null
        ? ''
        : 'Detected: ${incidentTime.toLocal().toIso8601String()}\n';
    return '\u{1F6A8} SOS ALERT!\n\n'
        '$userName needs help immediately.\n\n'
        '$typeText'
        '$timeText'
        '${trackingUrl == null ? '' : '\u{1F534} Live Tracking:\n$trackingUrl\n\n'}'
        '\u{1F4CD} Current GPS:\n'
        '${location == null ? 'GPS is being acquired.' : 'https://maps.google.com/?q=${location.latitude},${location.longitude}'}\n\n'
        '$evidenceText'
        'Location updates every 5 seconds.\n'
        'Please contact immediately.';
  }

  Future<bool> requestPermission() async {
    try {
      final granted = await _telephony.requestSmsPermissions ?? false;
      debugPrint('[SOS] SMS permission granted: $granted');
      return granted;
    } catch (error) {
      debugPrint('[SOS] SMS permission error: $error');
      return false;
    }
  }

  Future<EmergencySmsResult> sendEmergencySms({
    required List<EmergencyContact> contacts,
    LocationUpdate? location,
    required String userName,
    String? trackingUrl,
    String? incidentType,
    List<String> evidenceLinks = const [],
    DateTime? incidentTime,
  }) async {
    final recipients = contacts
        .where((contact) => !contact.isHidden)
        .map((contact) => contact.displayPhoneNumber.trim())
        .where((phone) => phone.isNotEmpty)
        .toSet()
        .toList();

    if (recipients.isEmpty) {
      debugPrint('[SOS] SMS skipped: no emergency contacts available.');
      return const EmergencySmsResult(attempted: 0, sent: 0, failed: 0);
    }

    final permitted = await requestPermission();
    if (!permitted) {
      debugPrint('[SOS] SMS skipped: SEND_SMS permission denied.');
      return EmergencySmsResult(
        attempted: recipients.length,
        sent: 0,
        failed: recipients.length,
      );
    }

    final message = messageFor(
      location: location,
      userName: userName,
      trackingUrl: trackingUrl,
      incidentType: incidentType,
      evidenceLinks: evidenceLinks,
      incidentTime: incidentTime,
    );
    var sent = 0;
    var failed = 0;

    for (final phone in recipients) {
      try {
        await _telephony.sendSms(
          to: phone,
          message: message,
          isMultipart: true,
        );
        sent += 1;
        debugPrint('[SOS] SMS sent to $phone');
      } catch (error) {
        failed += 1;
        debugPrint('[SOS] SMS failed for $phone: $error');
      }
    }

    return EmergencySmsResult(
      attempted: recipients.length,
      sent: sent,
      failed: failed,
    );
  }
}
