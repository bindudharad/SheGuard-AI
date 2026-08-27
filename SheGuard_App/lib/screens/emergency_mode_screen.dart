import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/app_theme.dart';
import '../services/auto_sos_manager.dart';
import '../services/emergency_realtime_service.dart';
import '../widgets/premium_ui.dart';

class EmergencyModeScreen extends StatefulWidget {
  const EmergencyModeScreen({super.key});

  static const route = '/emergency-mode';

  @override
  State<EmergencyModeScreen> createState() => _EmergencyModeScreenState();
}

class _EmergencyModeScreenState extends State<EmergencyModeScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _flash;

  @override
  void initState() {
    super.initState();
    _flash = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 720),
      lowerBound: .35,
      upperBound: 1,
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _flash.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final manager = context.watch<AutoSosManager>();
    final event = manager.activeEvent;
    return PopScope(
      canPop: !manager.active,
      child: PremiumScaffold(
        appBar: AppBar(
          automaticallyImplyLeading: !manager.active,
          backgroundColor: Colors.transparent,
          title: const Text('Auto SOS Mode'),
        ),
        child: ListView(
          padding: const EdgeInsets.fromLTRB(18, 16, 18, 28),
          children: [
            FadeTransition(
              opacity: _flash,
              child: GlassCard(
                glowColor: AppTheme.emergency,
                padding: const EdgeInsets.all(18),
                child: Row(
                  children: [
                    const GlowIcon(
                      icon: Icons.emergency_share,
                      color: AppTheme.emergency,
                      size: 58,
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Emergency Active',
                            style: TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w900,
                              fontSize: 22,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            event == null
                                ? 'SOS Triggered'
                                : 'SOS Triggered - ${event.incidentType}',
                            style: TextStyle(
                              color: Colors.white.withValues(alpha: .75),
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const PulsingDot(color: AppTheme.emergency),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 14),
            _StatusPanel(manager: manager),
            const SizedBox(height: 14),
            _CountdownCard(seconds: manager.countdownSeconds),
            const SizedBox(height: 14),
            _ContactStatus(manager: manager),
            const SizedBox(height: 14),
            if (manager.lastLocation != null)
              _LocationCard(manager: manager)
            else
              const _WaitingCard(),
            if (manager.error != null) ...[
              const SizedBox(height: 14),
              GlassCard(
                glowColor: AppTheme.warning,
                child: Row(
                  children: [
                    const GlowIcon(
                      icon: Icons.warning_amber,
                      color: AppTheme.warning,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        manager.error!,
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: .82),
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            const SizedBox(height: 18),
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: AppTheme.safe,
                side: BorderSide(color: AppTheme.safe.withValues(alpha: .55)),
                minimumSize: const Size.fromHeight(54),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(18),
                ),
              ),
              onPressed: () async {
                await context.read<AutoSosManager>().cancelAutoSos();
                if (!context.mounted) return;
                Navigator.pop(context);
              },
              icon: const Icon(Icons.check_circle),
              label: const Text("I'm safe - cancel auto SOS"),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatusPanel extends StatelessWidget {
  const _StatusPanel({required this.manager});

  final AutoSosManager manager;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      child: Column(
        children: [
          _SignalRow(
            icon: Icons.sensors,
            label: 'Realtime link',
            value: _realtimeLabel(manager.realtimeState),
            active: manager.realtimeState == RealtimeConnectionState.connected,
          ),
          const Divider(color: Colors.white12),
          _SignalRow(
            icon: Icons.gps_fixed,
            label: 'GPS tracking',
            value: manager.gpsActive ? 'Uploading live' : 'Acquiring signal',
            active: manager.gpsActive,
          ),
          const Divider(color: Colors.white12),
          _SignalRow(
            icon: Icons.call,
            label: 'Parent call',
            value: _parentCallLabel(manager),
            active: manager.parentCallStarted,
          ),
          const Divider(color: Colors.white12),
          _SignalRow(
            icon: Icons.shield,
            label: 'Emergency session',
            value: manager.sessionId ?? 'Binding session',
            active: manager.active,
          ),
        ],
      ),
    );
  }

  String _realtimeLabel(RealtimeConnectionState state) {
    switch (state) {
      case RealtimeConnectionState.connected:
        return 'Connected';
      case RealtimeConnectionState.connecting:
        return 'Connecting';
      case RealtimeConnectionState.reconnecting:
        return 'Reconnecting';
      case RealtimeConnectionState.disconnected:
        return 'Offline recovery';
      case RealtimeConnectionState.failed:
        return 'Retrying quietly';
      case RealtimeConnectionState.idle:
        return 'Idle';
    }
  }

  String _parentCallLabel(AutoSosManager manager) {
    if (!manager.parentCallAttempted) return 'Calling Parent...';
    final name = manager.parentCallName ?? 'Parent';
    if (manager.parentCallStarted) return 'Calling $name';
    return 'Dialer opened for $name';
  }
}

class _CountdownCard extends StatelessWidget {
  const _CountdownCard({required this.seconds});

  final int seconds;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      glowColor: AppTheme.warning,
      child: Row(
        children: [
          const GlowIcon(icon: Icons.timer, color: AppTheme.warning),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              seconds > 0
                  ? 'Escalation countdown: $seconds seconds'
                  : 'Emergency escalation locked',
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ContactStatus extends StatelessWidget {
  const _ContactStatus({required this.manager});

  final AutoSosManager manager;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      child: Row(
        children: [
          const GlowIcon(icon: Icons.contacts, color: AppTheme.cyan),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              'Contacts: ${manager.contactsSent} sent, '
              '${manager.contactsFailed} failed, '
              '${manager.contactsAttempted} attempted',
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _LocationCard extends StatelessWidget {
  const _LocationCard({required this.manager});

  final AutoSosManager manager;

  @override
  Widget build(BuildContext context) {
    final location = manager.lastLocation!;
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Live GPS',
            style: TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w900,
              fontSize: 18,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            '${location.latitude.toStringAsFixed(6)}, '
            '${location.longitude.toStringAsFixed(6)}',
            style: TextStyle(color: Colors.white.withValues(alpha: .8)),
          ),
          const SizedBox(height: 6),
          Text(
            'Speed ${location.speed.toStringAsFixed(1)} m/s'
            '${location.heading == null ? '' : ' | Heading ${location.heading!.toStringAsFixed(0)}'}'
            '${location.battery == null ? '' : ' | Battery ${location.battery}%'}',
            style: TextStyle(color: Colors.white.withValues(alpha: .66)),
          ),
        ],
      ),
    );
  }
}

class _WaitingCard extends StatelessWidget {
  const _WaitingCard();

  @override
  Widget build(BuildContext context) {
    return const GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'GPS signal locking',
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900),
          ),
          SizedBox(height: 12),
          ShimmerBar(height: 10),
          SizedBox(height: 8),
          ShimmerBar(width: 170, height: 10),
        ],
      ),
    );
  }
}

class _SignalRow extends StatelessWidget {
  const _SignalRow({
    required this.icon,
    required this.label,
    required this.value,
    required this.active,
  });

  final IconData icon;
  final String label;
  final String value;
  final bool active;

  @override
  Widget build(BuildContext context) {
    final color = active ? AppTheme.safe : AppTheme.warning;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          GlowIcon(icon: icon, color: color, size: 42),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: TextStyle(color: Colors.white.withValues(alpha: .64)),
                ),
                const SizedBox(height: 3),
                Text(
                  value,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
          ),
          PulsingDot(color: color),
        ],
      ),
    );
  }
}
