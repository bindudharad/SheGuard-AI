import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_phone_direct_caller/flutter_phone_direct_caller.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/emergency_contact.dart';

class EmergencyCallService {
  List<EmergencyContact> _callQueue = [];
  final Set<String> _calledSessionIds = <String>{};
  int _index = 0;
  Timer? _fallbackTimer;

  Future<bool> callPrimaryImmediately(
    List<EmergencyContact> contacts, {
    String? sessionId,
    Duration fallbackDelay = const Duration(seconds: 20),
    bool allowFallback = true,
  }) async {
    if (sessionId != null && _calledSessionIds.contains(sessionId)) {
      debugPrint('SheGuard parent call skipped; session already called.');
      return false;
    }
    _callQueue = contacts
        .where((contact) => !contact.isHidden)
        .where((contact) => contact.displayPhoneNumber.trim().isNotEmpty)
        .toList();
    _index = 0;
    _fallbackTimer?.cancel();
    if (sessionId != null && _callQueue.isNotEmpty) {
      _calledSessionIds.add(sessionId);
    }

    debugPrint('SheGuard emergency call queue prepared: ${_callQueue.length}');
    final started = await callCurrent(direct: true);
    debugPrint('SheGuard call initiated: $started');

    if (!started && allowFallback && hasNext) {
      debugPrint(
          'SheGuard primary call failed to start; calling next contact.');
      return callNext(direct: true);
    }

    if (started && allowFallback && hasNext) {
      _fallbackTimer = Timer(fallbackDelay, () {
        debugPrint(
          'SheGuard automatic fallback call timer fired. '
          'Calling next emergency contact.',
        );
        unawaited(callNext(direct: true));
      });
    }
    return started;
  }

  Future<bool> openFirstContact(List<EmergencyContact> contacts) {
    return callPrimaryImmediately(contacts);
  }

  Future<bool> dialFirstParentOnce(
    List<EmergencyContact> contacts, {
    required String incidentKey,
  }) async {
    if (_calledSessionIds.contains(incidentKey)) {
      debugPrint('SheGuard parent dial skipped; incident already called.');
      return false;
    }
    EmergencyContact? parent;
    for (final contact in contacts) {
      if (!contact.isHidden && contact.displayPhoneNumber.trim().isNotEmpty) {
        parent = contact;
        break;
      }
    }
    if (parent == null) return false;
    _calledSessionIds.add(incidentKey);
    return _callContact(parent, direct: false);
  }

  Future<bool> callCurrent({bool direct = false}) async {
    if (_callQueue.isEmpty || _index >= _callQueue.length) {
      debugPrint('SheGuard call skipped: no emergency contact available.');
      return false;
    }
    return _callContact(_callQueue[_index], direct: direct);
  }

  Future<bool> callNext({bool direct = false}) async {
    if (_callQueue.isEmpty || !hasNext) return false;
    _index = (_index + 1).clamp(0, _callQueue.length - 1);
    return _callContact(_callQueue[_index], direct: direct);
  }

  void cancelFallback() {
    _fallbackTimer?.cancel();
    _fallbackTimer = null;
  }

  bool get hasNext => _callQueue.isNotEmpty && _index < _callQueue.length - 1;

  Future<bool> _callContact(
    EmergencyContact contact, {
    required bool direct,
  }) async {
    final phone = contact.displayPhoneNumber.trim().replaceAll(' ', '');
    if (phone.isEmpty) return false;
    try {
      if (direct) {
        final called =
            await FlutterPhoneDirectCaller.callNumber(phone) ?? false;
        debugPrint(
          'SheGuard direct call requested for ${contact.displayName}: $called',
        );
        if (called) return true;
      }

      final uri = Uri(scheme: 'tel', path: phone);
      final opened = await launchUrl(uri, mode: LaunchMode.externalApplication);
      debugPrint('SheGuard dialer opened for ${contact.displayName}: $opened');
      return opened;
    } catch (error) {
      debugPrint('SheGuard call failed for ${contact.displayName}: $error');
      return false;
    }
  }
}
