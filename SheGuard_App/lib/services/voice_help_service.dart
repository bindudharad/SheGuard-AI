import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:speech_to_text/speech_to_text.dart';

class VoiceHelpService {
  VoiceHelpService();

  final SpeechToText _speech = SpeechToText();
  Timer? _debounceTimer;
  Timer? _cooldownTimer;
  bool _isListening = false;
  bool _helpDetected = false;
  bool _cooldownActive = false;
  bool _disposed = false;

  static const Duration _debounceDelay = Duration(milliseconds: 800);
  static const Duration _cooldownDuration = Duration(seconds: 10);

  Function()? onHelpDetected;

  Future<bool> initialize() async {
    if (_disposed) return false;
    try {
      final status = await Permission.microphone.status;
      if (!status.isGranted) {
        final result = await Permission.microphone.request();
        if (!result.isGranted) {
          debugPrint('[VOICE] Microphone permission denied');
          return false;
        }
      }

      final initialized = await _speech.initialize(
        onError: _handleError,
        onStatus: _handleStatus,
      );

      if (!initialized) {
        debugPrint('[VOICE] Speech recognition not available');
        return false;
      }

      debugPrint('[VOICE] Voice help service initialized');
      return true;
    } catch (error) {
      debugPrint('[VOICE] Initialization error: ' + error.toString());
      return false;
    }
  }

  void startListening() {
    if (_disposed || _isListening || _cooldownActive) return;

    try {
      _isListening = true;
      _speech.listen(
        onResult: _handleResult,
        listenOptions: SpeechListenOptions(
          listenFor: const Duration(seconds: 30),
          pauseFor: const Duration(seconds: 5),
          partialResults: true,
          localeId: 'en_US',
        ),
      );
      debugPrint('[VOICE] Started listening for HELP');
    } catch (error) {
      debugPrint('[VOICE] Start listening error: ' + error.toString());
      _isListening = false;
    }
  }

  void stopListening() {
    if (!_isListening) return;
    _speech.stop();
    _isListening = false;
    _debounceTimer?.cancel();
    debugPrint('[VOICE] Stopped listening');
  }

  void _handleResult(result) {
    if (_disposed || _helpDetected || _cooldownActive) return;

    final text = result.recognizedWords.toLowerCase().trim();
    if (text.isEmpty) return;

    debugPrint('[VOICE] Recognized: ' + text);

    if (text.contains('help') || text.contains('helpp') || text.contains('help me')) {
      _debounceTimer?.cancel();
      _debounceTimer = Timer(_debounceDelay, () {
        if (!_helpDetected && !_cooldownActive) {
          _triggerHelp();
        }
      });
    }
  }

  void _triggerHelp() {
    if (_helpDetected || _cooldownActive) return;

    _helpDetected = true;
    _cooldownActive = true;

    debugPrint('[VOICE] HELP detected!');
    onHelpDetected?.call();

    _cooldownTimer = Timer(_cooldownDuration, () {
      _helpDetected = false;
      _cooldownActive = false;
      debugPrint('[VOICE] Cooldown expired, ready for next HELP');
    });
  }

  void _handleError(error) {
    debugPrint('[VOICE] Speech error: ' + error.toString());
    _isListening = false;
    _debounceTimer?.cancel();
  }

  void _handleStatus(status) {
    debugPrint('[VOICE] Status: ' + status.toString());
    if (status == 'notListening' && !_disposed && !_cooldownActive) {
      Future.delayed(const Duration(seconds: 2), () {
        if (!_disposed && !_cooldownActive) {
          startListening();
        }
      });
    }
  }

  void dispose() {
    _disposed = true;
    stopListening();
    _debounceTimer?.cancel();
    _cooldownTimer?.cancel();
    _speech.cancel();
  }
}