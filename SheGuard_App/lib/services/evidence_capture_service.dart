import 'dart:convert';
import 'dart:io';

import 'package:camera/camera.dart';
import 'package:cryptography/cryptography.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:record/record.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api_service.dart';

class EvidenceCaptureService {
  EvidenceCaptureService({
    ApiService? api,
    AudioRecorder? recorder,
    FlutterSecureStorage? secureStorage,
  })  : _api = api,
        _recorder = recorder ?? AudioRecorder(),
        _secureStorage = secureStorage ?? const FlutterSecureStorage();

  static const _keyName = 'sheguard_evidence_key_v1';
  static const _manifestKey = 'encrypted_evidence_manifest';
  static const _uploadQueueKey = 'encrypted_evidence_upload_queue';

  final ApiService? _api;
  final AudioRecorder _recorder;
  final FlutterSecureStorage _secureStorage;
  final _cipher = AesGcm.with256bits();
  String? _activeSessionId;
  String? _activeAudioPath;

  Future<void> startEmergencyCapture(String sessionId) async {
    _activeSessionId = sessionId;
    await retryPendingUploads();
    await Future.wait([
      _startAudio(sessionId),
      captureFrontImage(sessionId),
    ]);
  }

  Future<void> stopEmergencyCapture() async {
    final sessionId = _activeSessionId;
    if (sessionId == null) return;
    try {
      final path = await _recorder.stop();
      final audioPath = path ?? _activeAudioPath;
      if (audioPath != null && File(audioPath).existsSync()) {
        await _encryptAndRecord(
          sessionId: sessionId,
          clearPath: audioPath,
          type: 'audio',
          extension: 'm4a',
        );
      }
      debugPrint('SheGuard emergency audio capture stopped: $sessionId');
    } catch (error) {
      debugPrint('SheGuard audio capture stop failed: $error');
    } finally {
      _activeSessionId = null;
      _activeAudioPath = null;
    }
  }

  Future<void> _startAudio(String sessionId) async {
    try {
      if (!await _recorder.hasPermission()) {
        debugPrint('SheGuard audio evidence skipped: microphone denied.');
        return;
      }
      final dir = await _evidenceDirectory();
      final path = '${dir.path}${Platform.pathSeparator}$sessionId-raw.m4a';
      await _recorder.start(
        const RecordConfig(
          encoder: AudioEncoder.aacLc,
          bitRate: 64000,
          sampleRate: 16000,
        ),
        path: path,
      );
      _activeAudioPath = path;
      debugPrint('SheGuard emergency audio capture started: $sessionId');
    } catch (error) {
      debugPrint('SheGuard audio evidence start failed: $error');
    }
  }

  Future<void> captureFrontImage(String sessionId) async {
    CameraController? controller;
    try {
      final permission = await Permission.camera.request();
      if (!permission.isGranted) {
        debugPrint('SheGuard camera evidence skipped: camera denied.');
        return;
      }
      final cameras = await availableCameras();
      CameraDescription? camera;
      for (final item in cameras) {
        if (item.lensDirection == CameraLensDirection.front) {
          camera = item;
          break;
        }
      }
      if (camera == null) {
        debugPrint('SheGuard camera evidence skipped: no front camera.');
        return;
      }

      controller = CameraController(
        camera,
        ResolutionPreset.medium,
        enableAudio: false,
      );
      await controller.initialize();
      final image = await controller.takePicture();
      await _encryptAndRecord(
        sessionId: sessionId,
        clearPath: image.path,
        type: 'front_image',
        extension: 'jpg',
      );
      debugPrint('SheGuard front camera evidence captured: $sessionId');
    } catch (error) {
      debugPrint('SheGuard camera evidence failed: $error');
    } finally {
      await controller?.dispose();
    }
  }

  Future<Directory> _evidenceDirectory() async {
    final root = await getApplicationSupportDirectory();
    final dir = Directory('${root.path}${Platform.pathSeparator}evidence');
    if (!dir.existsSync()) {
      await dir.create(recursive: true);
    }
    return dir;
  }

  Future<void> _encryptAndRecord({
    required String sessionId,
    required String clearPath,
    required String type,
    required String extension,
  }) async {
    final input = File(clearPath);
    if (!input.existsSync()) return;

    final bytes = await input.readAsBytes();
    final secretKey = await _evidenceKey();
    final box = await _cipher.encrypt(bytes, secretKey: secretKey);
    final outputDir = await _evidenceDirectory();
    final timestamp = DateTime.now().toUtc().millisecondsSinceEpoch;
    final output = File(
      '${outputDir.path}${Platform.pathSeparator}$sessionId-$type-$timestamp.$extension.enc',
    );
    await output.writeAsBytes(box.concatenation());
    await input.delete();

    final prefs = await SharedPreferences.getInstance();
    final manifest = prefs.getStringList(_manifestKey) ?? const [];
    final record = jsonEncode({
      'session_id': sessionId,
      'type': type,
      'path': output.path,
      'filename': output.uri.pathSegments.last,
      'created_at': DateTime.now().toUtc().toIso8601String(),
      'encrypted': true,
      'algorithm': 'AES-256-GCM',
    });
    await prefs.setStringList(_manifestKey, [record, ...manifest]);
    await _queueOrUpload(record);
    debugPrint('SheGuard encrypted evidence stored: ${output.path}');
  }

  Future<void> retryPendingUploads() async {
    final prefs = await SharedPreferences.getInstance();
    final queue = prefs.getStringList(_uploadQueueKey) ?? const [];
    if (queue.isEmpty) return;
    final remaining = <String>[];
    for (final raw in queue) {
      if (!await _uploadRecord(raw)) {
        remaining.add(raw);
      }
    }
    await prefs.setStringList(_uploadQueueKey, remaining);
  }

  Future<void> _queueOrUpload(String record) async {
    if (await _uploadRecord(record)) return;
    final prefs = await SharedPreferences.getInstance();
    final queue = prefs.getStringList(_uploadQueueKey) ?? const [];
    await prefs.setStringList(
        _uploadQueueKey, [record, ...queue].take(50).toList());
  }

  Future<bool> _uploadRecord(String raw) async {
    final api = _api;
    if (api == null) return false;
    try {
      final record = jsonDecode(raw) as Map<String, dynamic>;
      final file = File(record['path'] as String);
      if (!file.existsSync()) return true;
      await api.postJson('/evidence/upload', {
        'session_id': record['session_id'],
        'evidence_type': record['type'],
        'filename': record['filename'],
        'content_base64': base64Encode(await file.readAsBytes()),
        'encrypted': true,
        'created_at': record['created_at'],
      });
      debugPrint('SheGuard encrypted evidence uploaded: ${record['filename']}');
      return true;
    } catch (error) {
      debugPrint('SheGuard evidence upload deferred: $error');
      return false;
    }
  }

  Future<SecretKey> _evidenceKey() async {
    final stored = await _secureStorage.read(key: _keyName);
    if (stored != null && stored.isNotEmpty) {
      return SecretKey(base64Decode(stored));
    }
    final key = await _cipher.newSecretKey();
    final bytes = await key.extractBytes();
    await _secureStorage.write(key: _keyName, value: base64Encode(bytes));
    return key;
  }
}
