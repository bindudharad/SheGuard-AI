import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/io.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../models/emergency_event.dart';
import 'api_service.dart';
import 'notification_service.dart';

enum RealtimeConnectionState {
  idle,
  connecting,
  connected,
  reconnecting,
  disconnected,
  failed,
}

class EmergencyRealtimeService {
  EmergencyRealtimeService(this._api, this._notifications);

  final ApiService _api;
  final NotificationService _notifications;
  final _events = StreamController<EmergencyEvent>.broadcast();
  final _states = StreamController<RealtimeConnectionState>.broadcast();

  WebSocketChannel? _channel;
  StreamSubscription<dynamic>? _subscription;
  Timer? _heartbeat;
  Timer? _reconnectTimer;
  int? _userId;
  int _attempt = 0;
  bool _stopped = true;
  bool _reconnectScheduled = false;
  bool _outageNotificationShown = false;
  RealtimeConnectionState _state = RealtimeConnectionState.idle;

  static const List<Duration> _backoff = [
    Duration(seconds: 2),
    Duration(seconds: 5),
    Duration(seconds: 10),
    Duration(seconds: 20),
    Duration(seconds: 40),
    Duration(seconds: 60),
  ];

  Stream<EmergencyEvent> get events => _events.stream;
  Stream<RealtimeConnectionState> get states => _states.stream;

  Future<void> start({required int userId}) async {
    if (_userId == userId && !_stopped) return;
    _userId = userId;
    _stopped = false;
    _attempt = 0;
    _outageNotificationShown = false;
    await _connect();
  }

  Future<void> stop() async {
    _stopped = true;
    _reconnectTimer?.cancel();
    _heartbeat?.cancel();
    await _subscription?.cancel();
    await _channel?.sink.close();
    _channel = null;
    _emitState(RealtimeConnectionState.idle);
  }

  Future<void> _connect() async {
    final userId = _userId;
    if (_stopped || userId == null) return;
    _reconnectScheduled = false;
    _emitState(_attempt == 0
        ? RealtimeConnectionState.connecting
        : RealtimeConnectionState.reconnecting);
    try {
      final uri = await _api.websocketUri(
        '/ws/live',
        query: {
          'user_id': userId.toString(),
          'token': _api.authToken,
        },
      );
      final headers = <String, dynamic>{
        if (_api.authToken != null) 'Authorization': 'Bearer ${_api.authToken}',
      };
      final channel = IOWebSocketChannel.connect(uri, headers: headers);
      _channel = channel;
      _subscription = channel.stream.listen(
        _handleMessage,
        onError: _handleDisconnect,
        onDone: () => _handleDisconnect('socket closed'),
        cancelOnError: true,
      );
      _attempt = 0;
      final shouldShowRestored = _outageNotificationShown;
      _outageNotificationShown = false;
      _emitState(RealtimeConnectionState.connected);
      if (shouldShowRestored) {
        unawaited(_notifications.showRealtimeRestored());
      }
      _startHeartbeat();
      debugPrint('[REALTIME] Connected to $uri');
    } catch (error) {
      debugPrint('[REALTIME] Connect failed: $error');
      _scheduleReconnect(error);
    }
  }

  void _handleMessage(dynamic raw) {
    try {
      final decoded = raw is String ? jsonDecode(raw) : raw;
      if (decoded is! Map) return;
      final json = decoded.cast<String, dynamic>();
      final type = json['type']?.toString() ?? json['event']?.toString() ?? '';
      if (type == 'pong' || type == 'heartbeat') return;
      final payload = json['payload'];
      if (payload is Map) {
        final nested = payload.cast<String, dynamic>();
        if (type.contains('emergency') ||
            type.contains('incident') ||
            nested.containsKey('incident') ||
            nested.containsKey('incident_id')) {
          _events.add(EmergencyEvent.fromJson(nested));
          return;
        }
      }
      if (type.contains('emergency') ||
          type.contains('incident') ||
          json.containsKey('incident') ||
          json.containsKey('incident_id')) {
        final event = EmergencyEvent.fromJson(json);
        _events.add(event);
      }
    } catch (error) {
      debugPrint('[REALTIME] Ignored malformed event: $error');
    }
  }

  void _handleDisconnect(Object? error) {
    if (_stopped) return;
    debugPrint('[REALTIME] Disconnected: $error');
    _scheduleReconnect(error);
  }

  void _scheduleReconnect(Object? error) {
    if (_stopped || _reconnectScheduled) return;
    _heartbeat?.cancel();
    _subscription?.cancel();
    _channel = null;
    _reconnectScheduled = true;
    _attempt += 1;
    final delay = _backoff[(_attempt - 1).clamp(0, _backoff.length - 1)];
    _emitState(_attempt >= _backoff.length
        ? RealtimeConnectionState.failed
        : _attempt == 1
            ? RealtimeConnectionState.disconnected
            : RealtimeConnectionState.reconnecting);

    // Notification lifecycle:
    // - first outage transition alerts and vibrates once;
    // - all subsequent reconnect attempts are silent;
    // - successful reconnect cancels this notification and may show one quiet
    //   restored message.
    if (!_outageNotificationShown) {
      _outageNotificationShown = true;
      unawaited(_notifications.showRealtimeReconnectDebounced());
    }
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(delay, _connect);
    debugPrint(
      '[REALTIME] Reconnect attempt $_attempt scheduled in ${delay.inSeconds}s',
    );
  }

  void _startHeartbeat() {
    _heartbeat?.cancel();
    _heartbeat = Timer.periodic(const Duration(seconds: 25), (_) {
      try {
        _channel?.sink.add(jsonEncode({
          'type': 'ping',
          'timestamp': DateTime.now().toUtc().toIso8601String(),
        }));
      } catch (error) {
        _handleDisconnect(error);
      }
    });
  }

  Future<void> dispose() async {
    await stop();
    await _events.close();
    await _states.close();
  }

  void _emitState(RealtimeConnectionState next) {
    if (_state == next) return;
    _state = next;
    _states.add(next);
  }
}
