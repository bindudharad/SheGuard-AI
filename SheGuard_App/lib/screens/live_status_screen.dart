import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/auth_provider.dart';
import '../providers/incident_provider.dart';
import '../providers/location_provider.dart';
import '../providers/safety_provider.dart';
import '../core/app_theme.dart';
import '../widgets/premium_ui.dart';
import '../widgets/safety_status_banner.dart';

class LiveStatusScreen extends StatefulWidget {
  const LiveStatusScreen({super.key});

  static const route = '/live-status';

  @override
  State<LiveStatusScreen> createState() => _LiveStatusScreenState();
}

class _LiveStatusScreenState extends State<LiveStatusScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _refresh());
  }

  Future<void> _refresh() async {
    final user = context.read<AuthProvider>().user;
    final safetyProvider = context.read<SafetyProvider>();
    final locationProvider = context.read<LocationProvider>();
    final incidentProvider = context.read<IncidentProvider>();
    await safetyProvider.refreshBackendStatus();
    if (user != null) await locationProvider.sendNow(user.userId);
    if (!mounted) return;
    await incidentProvider.loadLive();
  }

  @override
  Widget build(BuildContext context) {
    final location = context.watch<LocationProvider>();
    final safety = context.watch<SafetyProvider>();
    final gps = location.lastLocation;
    return PremiumScaffold(
      appBar: AppBar(title: const Text('Live Status')),
      child: RefreshIndicator(
        onRefresh: _refresh,
        child: ListView(
          padding: const EdgeInsets.all(18),
          children: [
            SafetyStatusBanner(
              protectionStatus: safety.protectionStatus,
              backendStatus: safety.backendStatus,
              message: safety.message,
            ),
            const SizedBox(height: 14),
            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisSpacing: 10,
              mainAxisSpacing: 10,
              childAspectRatio: 1.35,
              children: [
                _LiveMetric(
                  icon: Icons.emergency,
                  label: 'Emergency',
                  value: safety.emergencyActive ? 'Active' : 'Standby',
                  color: safety.emergencyActive
                      ? AppTheme.emergency
                      : AppTheme.safe,
                ),
                _LiveMetric(
                  icon: Icons.gps_fixed,
                  label: 'GPS',
                  value: location.tracking ? 'Live location updating' : 'Ready',
                  color: location.tracking ? AppTheme.safe : AppTheme.warning,
                ),
                _LiveMetric(
                  icon: Icons.battery_full,
                  label: 'Battery',
                  value: gps?.battery == null ? '--' : '${gps!.battery}%',
                  color: AppTheme.cyan,
                ),
                _LiveMetric(
                  icon: Icons.schedule,
                  label: 'Last updated',
                  value: location.freshness?.ageLabel ?? 'No GPS fix',
                  color: AppTheme.warning,
                ),
              ],
            ),
            const SizedBox(height: 14),
            const GlassCard(
              child: Row(
                children: [
                  GlowIcon(icon: Icons.radar, color: AppTheme.cyan),
                  SizedBox(width: 14),
                  Expanded(
                    child: Text(
                      'Live safety status stays calm and readable during emergencies.',
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _LiveMetric extends StatelessWidget {
  const _LiveMetric({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(14),
      glowColor: color,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          GlowIcon(icon: icon, color: color, size: 38),
          const Spacer(),
          Text(
            value,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w900,
              fontSize: 15,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: TextStyle(color: Colors.white.withValues(alpha: .58)),
          ),
        ],
      ),
    );
  }
}
