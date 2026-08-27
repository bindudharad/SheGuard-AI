import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/app_theme.dart';
import '../models/incident.dart';
import '../providers/auth_provider.dart';
import '../providers/contact_provider.dart';
import '../providers/incident_provider.dart';
import '../providers/location_provider.dart';
import '../providers/safety_provider.dart';
import '../providers/settings_provider.dart';
import '../services/emergency_call_service.dart';
import '../services/auto_sos_manager.dart';
import '../services/motion_protection_service.dart';
import '../services/notification_service.dart';
import '../services/sos_service.dart';
import '../widgets/emergency_action_panel.dart';
import '../widgets/premium_ui.dart';
import '../widgets/safety_status_banner.dart';
import 'contacts_screen.dart';
import 'incident_history_screen.dart';
import 'live_status_screen.dart';
import 'login_screen.dart';
import 'emergency_mode_screen.dart';
import 'settings_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  static const route = '/home';

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _silentTapCount = 0;
  bool _fallPromptShowing = false;
  bool _emergencyRouteOpen = false;
  String? _motionSignature;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      final user = context.read<AuthProvider>().user;
      final settings = context.read<SettingsProvider>();
      final autoSosManager = context.read<AutoSosManager>();
      final safetyProvider = context.read<SafetyProvider>();
      final contactProvider = context.read<ContactProvider>();
      final incidentProvider = context.read<IncidentProvider>();
      final locationProvider = context.read<LocationProvider>();
      if (user != null) {
        await autoSosManager.bindUser(user);
        if (!mounted) return;
        safetyProvider.setMonitoring();
      }
      if (user != null && settings.trackingEnabled) {
        contactProvider.load(user.userId);
        incidentProvider.loadIncidentFeed();
        incidentProvider.startIncidentRealtime();
        locationProvider.requestPermission();
        locationProvider.start(user.userId);
      }
      _configureMotionProtection();
    });
  }

  @override
  void dispose() {
    context.read<MotionProtectionService>().stop();
    super.dispose();
  }

  void _configureMotionProtection() {
    final settings = context.read<SettingsProvider>();
    final signature =
        '${settings.shakeSosEnabled}:${settings.fallDetectionEnabled}:${settings.shakeSensitivity}';
    if (_motionSignature == signature) return;
    _motionSignature = signature;
    context.read<MotionProtectionService>().start(
          shakeEnabled: settings.shakeSosEnabled,
          fallDetectionEnabled: settings.fallDetectionEnabled,
          shakeSensitivity: settings.shakeSensitivity,
          onShake: () => _startSosCountdown(silent: true),
          onFall: _showFallSafetyCheck,
        );
  }

  Future<void> _startSosCountdown({required bool silent}) async {
    if (!mounted || context.read<IncidentProvider>().loading) return;
    var cancelled = false;
    final seconds = ValueNotifier<int>(3);
    Timer? timer;
    timer = Timer.periodic(const Duration(seconds: 1), (_) {
      seconds.value -= 1;
      if (seconds.value <= 0) {
        timer?.cancel();
        if (mounted && Navigator.of(context).canPop()) {
          Navigator.of(context).pop();
        }
      }
    });
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Sending help alert'),
          content: ValueListenableBuilder<int>(
            valueListenable: seconds,
            builder: (context, value, _) {
              return Text('SOS activating in $value...');
            },
          ),
          actions: [
            TextButton(
              onPressed: () {
                cancelled = true;
                Navigator.of(dialogContext).pop();
              },
              child: const Text('Cancel'),
            ),
          ],
        );
      },
    );
    timer.cancel();
    seconds.dispose();
    if (!cancelled && mounted) {
      await _triggerSos(silent: silent);
    }
  }


  Future<void> _activateHelp() async {
    final safetyProvider = context.read<SafetyProvider>();
    if (!safetyProvider.helpActive) {
      await safetyProvider.activateHelp(onComplete: () {
        if (mounted) {
          _triggerSos(silent: false);
        }
      });
    }
  }

  void _cancelHelp() {
    final safetyProvider = context.read<SafetyProvider>();
    if (safetyProvider.helpActive) {
      safetyProvider.cancelHelp();
    }
  }

  Future<void> _triggerSos({required bool silent}) async {
    final user = context.read<AuthProvider>().user;
    if (user == null) return;
    final locationProvider = context.read<LocationProvider>();
    final contactProvider = context.read<ContactProvider>();
    final incidentProvider = context.read<IncidentProvider>();
    final safetyProvider = context.read<SafetyProvider>();
    final sosService = context.read<SosService>();
    final settings = context.read<SettingsProvider>();
    final sirenEnabled = settings.emergencySirenEnabled;

    if (incidentProvider.loading) return;

    incidentProvider.beginSos();
    if (contactProvider.contacts.isEmpty) {
      await contactProvider.load(user.userId);
    }
    final result = await sosService.activate(
      userId: user.userId,
      userName: user.fullName,
      silent: silent,
      contacts: contactProvider.visibleContacts,
      sirenEnabled: sirenEnabled,
      startEmergencyTracking: (sessionId) =>
          locationProvider.start(user.userId, sessionId: sessionId),
    );
    if (!mounted) return;
    if (result.success) {
      incidentProvider.completeSos(silent: silent);
      safetyProvider.activateEmergency(silent: silent);
    } else {
      incidentProvider.failSos(result.error ?? 'SOS could not be delivered.');
    }

    final sms = result.smsResult;
    final callService = context.read<EmergencyCallService>();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          result.success
              ? (silent
                  ? 'HELP ALERT SENT to ${sms?.sent ?? 0} contacts.'
                  : 'Help alert sent to ${sms?.sent ?? 0} contacts.')
              : result.error ??
                  'SOS could not be delivered. Check backend and network.',
        ),
        action: result.success && callService.hasNext
            ? SnackBarAction(
                label: 'Call next',
                onPressed: () {
                  callService.callNext();
                },
              )
            : null,
      ),
    );
  }

  void _hiddenGesture() {
    final settings = context.read<SettingsProvider>();
    if (!settings.silentModeEnabled) return;
    _silentTapCount += 1;
    if (_silentTapCount >= 3) {
      _silentTapCount = 0;
      _startSosCountdown(silent: true);
    }
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) _silentTapCount = 0;
    });
  }

  Future<void> _showFallSafetyCheck() async {
    if (!mounted || _fallPromptShowing) return;
    _fallPromptShowing = true;
    var safe = false;
    await context.read<NotificationService>().show(
          id: 9,
          title: 'Possible fall detected',
          body: 'Confirm you are safe to stop automatic SOS.',
        );
    if (!mounted) return;
    final seconds = ValueNotifier<int>(20);
    Timer? timer;
    timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (safe) {
        timer?.cancel();
        return;
      }
      seconds.value -= 1;
      if (seconds.value <= 0) {
        timer?.cancel();
        if (mounted && Navigator.of(context).canPop()) {
          Navigator.of(context).pop();
        }
      }
    });
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Are you safe?'),
          content: ValueListenableBuilder<int>(
            valueListenable: seconds,
            builder: (context, value, _) {
              return Text(
                'SheGuard detected a possible fall. Silent SOS starts in $value seconds.',
              );
            },
          ),
          actions: [
            TextButton(
              onPressed: () {
                safe = true;
                Navigator.of(dialogContext).pop();
              },
              child: const Text('I am safe'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('Send SOS now'),
            ),
          ],
        );
      },
    );
    timer.cancel();
    seconds.dispose();
    _fallPromptShowing = false;
    if (!safe && mounted) {
      _startSosCountdown(silent: true);
    }
  }

  Future<void> _showEmergencyDetectedPopup(Incident incident) async {
    context.read<IncidentProvider>().emergencyPopupHandled(incident);
    final contactProvider = context.read<ContactProvider>();
    final callService = context.read<EmergencyCallService>();
    final notifications = context.read<NotificationService>();
    final user = context.read<AuthProvider>().user;
    if (contactProvider.contacts.isEmpty && user != null) {
      await contactProvider.load(user.userId);
    }
    await notifications.vibrateOnce(_incidentCallKey(incident));
    await callService.dialFirstParentOnce(
      contactProvider.visibleContacts,
      incidentKey: _incidentCallKey(incident),
    );
    if (!mounted) return;

    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('\u{1F6A8} Emergency Detected'),
          content: Text(
            '${_incidentTitle(incident.incidentType)} detected with '
            '${_incidentConfidencePercent(incident)}% confidence.\n\n'
            'Calling saved parent number...',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('Dismiss'),
            ),
            FilledButton(
              onPressed: () {
                Navigator.pop(dialogContext);
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => IncidentDetailScreen(incident: incident),
                  ),
                );
              },
              child: const Text('Open details'),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final location = context.watch<LocationProvider>();
    final incidents = context.watch<IncidentProvider>();
    final safety = context.watch<SafetyProvider>();
    final settings = context.watch<SettingsProvider>();
    final autoSos = context.watch<AutoSosManager>();
    final user = auth.user;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _configureMotionProtection();
      if (mounted && autoSos.active && !_emergencyRouteOpen) {
        _emergencyRouteOpen = true;
        Navigator.of(context)
            .pushNamed(EmergencyModeScreen.route)
            .whenComplete(() => _emergencyRouteOpen = false);
      }
      final incident =
          context.read<IncidentProvider>().pendingEmergencyIncident;
      if (mounted && incident != null) {
        _showEmergencyDetectedPopup(incident);
      }
    });

    return PremiumScaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: GestureDetector(
          onLongPress: () async {
            await context.read<SettingsProvider>().toggleDeveloperMode();
            if (!context.mounted) return;
            final enabled =
                context.read<SettingsProvider>().developerModeEnabled;
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                  content: Text(enabled
                      ? 'Developer mode enabled'
                      : 'Developer mode hidden')),
            );
          },
          child: const Text('SheGuard'),
        ),
        actions: [
          IconButton(
            tooltip: 'Settings',
            onPressed: () => Navigator.pushNamed(context, SettingsScreen.route),
            icon: const Icon(Icons.settings),
          ),
          IconButton(
            tooltip: 'Logout',
            onPressed: () async {
              final locationProvider = context.read<LocationProvider>();
              final authProvider = context.read<AuthProvider>();
              locationProvider.stop();
              await context.read<AutoSosManager>().bindUser(null);
              await authProvider.logout();
              if (!context.mounted) return;
              Navigator.pushNamedAndRemoveUntil(
                  context, LoginScreen.route, (_) => false);
            },
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      child: RefreshIndicator(
        onRefresh: () async {
          final safetyProvider = context.read<SafetyProvider>();
          final authProvider = context.read<AuthProvider>();
          final locationProvider = context.read<LocationProvider>();
          await safetyProvider.refreshBackendStatus();
          final activeUser = authProvider.user;
          if (activeUser != null) {
            await locationProvider.sendNow(activeUser.userId);
          }
        },
        child: ListView(
          padding: const EdgeInsets.fromLTRB(18, 12, 18, 28),
          children: [
            GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: _hiddenGesture,
              child: _HeroHeader(
                name: user?.fullName ?? 'there',
                protected: !safety.emergencyActive,
                locationLabel: location.placeLabel,
              ),
            ),
            const SizedBox(height: 16),
            SafetyStatusBanner(
              protectionStatus: safety.protectionStatus,
              backendStatus: safety.backendStatus,
              message: safety.message,
            ),
            EmergencyActionPanel(
              loading: incidents.loading,
              silentEnabled: settings.silentModeEnabled,
              onSos: () => _startSosCountdown(silent: false),
              onSilentSos: () => _startSosCountdown(silent: true),
              onHelp: () => _activateHelp(),
              helpActive: safety.helpActive,
              helpCountdownSeconds: safety.helpCountdownSeconds,
              onCancelHelp: () => _cancelHelp(),
            ),
            _StatusCard(
              icon: Icons.gps_fixed,
              title: location.tracking
                  ? 'GPS protection active'
                  : 'GPS protection ready',
              subtitle: location.tracking
                  ? 'Live location updating'
                  : 'SheGuard will start live tracking during an emergency.',
              color: location.tracking ? AppTheme.safe : AppTheme.warning,
            ),
            if (location.placeLabel != null) ...[
              _StatusCard(
                icon: Icons.place,
                title: location.placeLabel!,
                subtitle: 'Your current area',
                color: AppTheme.safe,
              ),
            ],
            if (safety.emergencyActive)
              _EmergencyActiveCard(
                tracking: location.tracking,
                contacts:
                    context.watch<ContactProvider>().visibleContacts.length,
              ),
            if (incidents.loading) ...[
              const SizedBox(height: 12),
              const GlassCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Sending protected alert',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    SizedBox(height: 12),
                    ShimmerBar(height: 10),
                    SizedBox(height: 8),
                    ShimmerBar(width: 180, height: 10),
                  ],
                ),
              ),
            ],
            if (safety.emergencyActive) ...[
              const SizedBox(height: 10),
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppTheme.safe,
                  side: BorderSide(color: AppTheme.safe.withValues(alpha: .55)),
                  minimumSize: const Size.fromHeight(52),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(18),
                  ),
                ),
                onPressed: () {
                  context.read<LocationProvider>().stop();
                  context.read<SosService>().stopEmergencyServices();
                  context.read<IncidentProvider>().clearEmergencyMode();
                  context.read<SafetyProvider>().resolveEmergency();
                },
                icon: const Icon(Icons.check_circle),
                label: const Text("I'm safe - return to monitoring"),
              ),
            ],
            const SizedBox(height: 16),
            const _ShortcutGrid(),
            if (settings.developerModeEnabled) ...[
              const SizedBox(height: 12),
              PremiumListTile(
                icon: Icons.monitor_heart,
                title: 'Developer live status',
                subtitle: 'Detailed safety service state',
                color: AppTheme.cyan,
                trailing:
                    const Icon(Icons.chevron_right, color: Colors.white70),
                onTap: () =>
                    Navigator.pushNamed(context, LiveStatusScreen.route),
              ),
            ],
            if (location.error != null || incidents.error != null) ...[
              const SizedBox(height: 14),
              GlassCard(
                glowColor: AppTheme.warning,
                child: Row(
                  children: [
                    const GlowIcon(
                        icon: Icons.wifi_off, color: AppTheme.warning),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Reconnecting to safety network...',
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
          ],
        ),
      ),
    );
  }
}

String _incidentTitle(String value) {
  return value
      .split(RegExp(r'[_\-\s]+'))
      .where((part) => part.isNotEmpty)
      .map((part) => '${part[0].toUpperCase()}${part.substring(1)}')
      .join(' ');
}

String _incidentCallKey(Incident incident) {
  return 'incident-${incident.incidentId ?? incident.createdAt?.millisecondsSinceEpoch ?? incident.hashCode}';
}

int _incidentConfidencePercent(Incident incident) {
  return (incident.confidence * 100).clamp(0, 100).round();
}

class _HeroHeader extends StatelessWidget {
  const _HeroHeader({
    required this.name,
    required this.protected,
    required this.locationLabel,
  });

  final String name;
  final bool protected;
  final String? locationLabel;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(20),
      glowColor: protected ? AppTheme.safe : AppTheme.emergency,
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Hi $name',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.w900,
                      ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    PulsingDot(
                      color: protected ? AppTheme.safe : AppTheme.emergency,
                    ),
                    const SizedBox(width: 10),
                    Text(
                      protected ? 'Protected' : 'Emergency Active',
                      style: TextStyle(
                        color: protected ? AppTheme.safe : AppTheme.emergency,
                        fontWeight: FontWeight.w900,
                        fontSize: 16,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  locationLabel ?? 'SheGuard is ready wherever you are.',
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: .68),
                    height: 1.35,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 16),
          _LiveShield(active: protected),
        ],
      ),
    );
  }
}

class _LiveShield extends StatefulWidget {
  const _LiveShield({required this.active});

  final bool active;

  @override
  State<_LiveShield> createState() => _LiveShieldState();
}

class _LiveShieldState extends State<_LiveShield>
    with SingleTickerProviderStateMixin {
  late final AnimationController _pulse;

  @override
  void initState() {
    super.initState();
    _pulse = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1600),
      lowerBound: .9,
      upperBound: 1.08,
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulse.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final color = widget.active ? AppTheme.safe : AppTheme.emergency;
    return ScaleTransition(
      scale: _pulse,
      child: GlowIcon(icon: Icons.shield, color: color, size: 64),
    );
  }
}

class _ShortcutGrid extends StatelessWidget {
  const _ShortcutGrid();

  @override
  Widget build(BuildContext context) {
    return GridView.count(
      crossAxisCount: 3,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisSpacing: 10,
      mainAxisSpacing: 10,
      childAspectRatio: .86,
      children: const [
        _ShortcutTile(
          icon: Icons.contacts,
          label: 'Contacts',
          route: ContactsScreen.route,
          color: AppTheme.cyan,
        ),
        _ShortcutTile(
          icon: Icons.tune,
          label: 'Safety',
          route: SettingsScreen.route,
          color: AppTheme.safe,
        ),
        _ShortcutTile(
          icon: Icons.history,
          label: 'Alerts',
          route: IncidentHistoryScreen.route,
          color: AppTheme.warning,
        ),
      ],
    );
  }
}

class _ShortcutTile extends StatelessWidget {
  const _ShortcutTile({
    required this.icon,
    required this.label,
    required this.route,
    required this.color,
  });

  final IconData icon;
  final String label;
  final String route;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(12),
      glowColor: color,
      onTap: () => Navigator.pushNamed(context, route),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          GlowIcon(icon: icon, color: color, size: 44),
          const SizedBox(height: 10),
          Text(
            label,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}

class _StatusCard extends StatelessWidget {
  const _StatusCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.color,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return PremiumListTile(
      icon: icon,
      title: title,
      subtitle: subtitle,
      color: color,
    );
  }
}

class _EmergencyActiveCard extends StatelessWidget {
  const _EmergencyActiveCard({
    required this.tracking,
    required this.contacts,
  });

  final bool tracking;
  final int contacts;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      glowColor: AppTheme.emergency,
      margin: const EdgeInsets.only(top: 6, bottom: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const GlowIcon(
                  icon: Icons.emergency_share, color: AppTheme.emergency),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  'Emergency Active',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.w900,
                      ),
                ),
              ),
              const PulsingDot(color: AppTheme.emergency),
            ],
          ),
          const SizedBox(height: 14),
          Text(
            tracking
                ? 'Live tracking is sharing your movement with trusted contacts.'
                : 'Help alert sent. GPS is locking onto your live route.',
            style: TextStyle(color: Colors.white.withValues(alpha: .72)),
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              _MiniSignal(label: 'Tracking', active: tracking),
              const SizedBox(width: 10),
              _MiniSignal(label: '$contacts contacts', active: contacts > 0),
            ],
          ),
        ],
      ),
    );
  }
}

class _MiniSignal extends StatelessWidget {
  const _MiniSignal({required this.label, required this.active});

  final String label;
  final bool active;

  @override
  Widget build(BuildContext context) {
    final color = active ? AppTheme.safe : AppTheme.warning;
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
        decoration: BoxDecoration(
          color: color.withValues(alpha: .1),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: color.withValues(alpha: .25)),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            PulsingDot(color: color),
            const SizedBox(width: 8),
            Flexible(
              child: Text(
                label,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: color,
                  fontWeight: FontWeight.w800,
                  fontSize: 12,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
