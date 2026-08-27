import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:provider/provider.dart';

import '../core/safety_types.dart';
import '../providers/auth_provider.dart';
import '../providers/location_provider.dart';
import '../providers/safety_provider.dart';
import '../providers/settings_provider.dart';
import '../services/auto_sos_manager.dart';
import '../widgets/premium_ui.dart';
import '../core/app_theme.dart';
import 'fake_call_screen.dart';
import 'login_screen.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  static const route = '/settings';

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<SettingsProvider>();
    final safety = context.watch<SafetyProvider>();
    return PremiumScaffold(
      appBar: AppBar(title: const Text('Settings')),
      child: ListView(
        padding: const EdgeInsets.all(18),
        children: [
          GlassCard(
            glowColor: AppTheme.safe,
            child: Row(
              children: [
                const GlowIcon(icon: Icons.tune, color: AppTheme.safe),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Safety Controls',
                        style:
                            Theme.of(context).textTheme.headlineSmall?.copyWith(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w900,
                                ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Tune SheGuard for your daily protection style.',
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: .68),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          _PremiumSwitch(
            icon: Icons.visibility_off,
            title: 'Silent emergency mode',
            subtitle:
                'Long press SOS or triple tap the home header to alert quietly.',
            color: AppTheme.cyan,
            value: settings.silentModeEnabled,
            onChanged: settings.setSilentMode,
          ),
          _PremiumSwitch(
            icon: Icons.notifications_active,
            title: 'Local notifications',
            subtitle: 'Show clear confirmations for alerts and tracking.',
            color: AppTheme.safe,
            value: settings.notificationsEnabled,
            onChanged: settings.setNotifications,
          ),
          _PremiumSwitch(
            icon: Icons.campaign,
            title: 'Emergency siren',
            subtitle: 'Play a loud repeating alert during SOS.',
            color: AppTheme.emergency,
            value: settings.emergencySirenEnabled,
            onChanged: settings.setEmergencySiren,
          ),
          _PremiumSwitch(
            icon: Icons.my_location,
            title: 'Live GPS tracking',
            subtitle: 'Keep active protection running while logged in.',
            color: AppTheme.safe,
            value: settings.trackingEnabled,
            onChanged: settings.setTracking,
          ),
          _PremiumSwitch(
            icon: Icons.call,
            title: 'Automatic emergency calling',
            subtitle: 'Open the first emergency contact when help is sent.',
            color: AppTheme.warning,
            value: settings.autoEmergencyCallEnabled,
            onChanged: settings.setAutoEmergencyCalling,
          ),
          _PremiumSwitch(
            icon: Icons.vibration,
            title: 'Shake SOS',
            subtitle: 'Aggressive repeated shaking activates silent SOS.',
            color: AppTheme.cyan,
            value: settings.shakeSosEnabled,
            onChanged: settings.setShakeSos,
          ),
          GlassCard(
            margin: const EdgeInsets.only(bottom: 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    GlowIcon(icon: Icons.graphic_eq, color: AppTheme.cyan),
                    SizedBox(width: 14),
                    Text(
                      'Shake sensitivity',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ],
                ),
                Slider(
                  value: settings.shakeSensitivity,
                  onChanged: settings.shakeSosEnabled
                      ? settings.setShakeSensitivity
                      : null,
                ),
              ],
            ),
          ),
          _PremiumSwitch(
            icon: Icons.health_and_safety,
            title: 'AI fall detection',
            subtitle: 'Detect impact plus stillness and ask if you are safe.',
            color: AppTheme.safe,
            value: settings.fallDetectionEnabled,
            onChanged: settings.setFallDetection,
          ),
          _PremiumSwitch(
            icon: Icons.privacy_tip,
            title: 'Privacy guard',
            subtitle: 'Hide sensitive contact details where possible.',
            color: AppTheme.cyan,
            value: settings.privacyGuardEnabled,
            onChanged: settings.setPrivacyGuard,
          ),
          PremiumListTile(
            icon: Icons.gps_fixed,
            title: 'GPS permissions',
            subtitle: 'Request location access for emergency tracking.',
            color: AppTheme.safe,
            trailing: const Icon(Icons.chevron_right, color: Colors.white70),
            onTap: () => context.read<LocationProvider>().requestPermission(),
          ),
          PremiumListTile(
            icon: Icons.phone_callback,
            title: 'Fake incoming call',
            subtitle: 'Show a believable call screen when you need an exit.',
            color: AppTheme.warning,
            trailing: const Icon(Icons.chevron_right, color: Colors.white70),
            onTap: () async {
              final controller = TextEditingController(text: 'Amma');
              final name = await showDialog<String>(
                context: context,
                builder: (context) => AlertDialog(
                  title: const Text('Fake caller name'),
                  content: TextField(
                    controller: controller,
                    decoration: const InputDecoration(labelText: 'Caller name'),
                  ),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.pop(context),
                      child: const Text('Cancel'),
                    ),
                    FilledButton(
                      onPressed: () =>
                          Navigator.pop(context, controller.text.trim()),
                      child: const Text('Start call'),
                    ),
                  ],
                ),
              );
              controller.dispose();
              if (!context.mounted || name == null || name.isEmpty) return;
              Navigator.push(
                context,
                MaterialPageRoute(
                    builder: (_) => FakeCallScreen(callerName: name)),
              );
            },
          ),
          const PremiumListTile(
            icon: Icons.battery_saver,
            title: 'Battery optimization',
            subtitle: 'Allow SheGuard to keep tracking during emergencies.',
            color: AppTheme.cyan,
            trailing: Icon(Icons.open_in_new, color: Colors.white70),
            onTap: openAppSettings,
          ),
          GlassCard(
            margin: const EdgeInsets.only(bottom: 12),
            child: Theme(
              data:
                  Theme.of(context).copyWith(dividerColor: Colors.transparent),
              child: const ExpansionTile(
                leading: Icon(Icons.info_outline, color: AppTheme.cyan),
                iconColor: Colors.white,
                collapsedIconColor: Colors.white70,
                title: Text('About'),
                childrenPadding: EdgeInsets.fromLTRB(16, 0, 16, 12),
                children: [
                  Align(
                    alignment: Alignment.centerLeft,
                    child: Text('SheGuard 1.0.0'),
                  ),
                ],
              ),
            ),
          ),
          if (settings.developerModeEnabled)
            PremiumListTile(
              icon: Icons.cloud_done,
              title: 'Safety network',
              subtitle: safety.backendStatus.label,
              color: AppTheme.cyan,
              trailing: const Icon(Icons.refresh, color: Colors.white70),
              onTap: () =>
                  context.read<SafetyProvider>().refreshBackendStatus(),
            ),
          PremiumListTile(
            icon: Icons.logout,
            title: 'Logout',
            subtitle: 'Sign out of this SheGuard session.',
            color: AppTheme.emergency,
            onTap: () async {
              final locationProvider = context.read<LocationProvider>();
              final authProvider = context.read<AuthProvider>();
              locationProvider.stop();
              await context.read<AutoSosManager>().bindUser(null);
              await authProvider.logout();
              if (!context.mounted) return;
              Navigator.pushNamedAndRemoveUntil(
                  context, LoginScreen.route, (_) => false);
            },
          ),
        ],
      ),
    );
  }
}

class _PremiumSwitch extends StatelessWidget {
  const _PremiumSwitch({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.color,
    required this.value,
    required this.onChanged,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final Color color;
  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      margin: const EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          GlowIcon(icon: icon, color: color),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: .65),
                    height: 1.35,
                  ),
                ),
              ],
            ),
          ),
          Switch(value: value, onChanged: onChanged),
        ],
      ),
    );
  }
}
