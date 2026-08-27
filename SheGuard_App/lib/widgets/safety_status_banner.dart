import 'package:flutter/material.dart';

import '../core/app_theme.dart';
import '../core/safety_types.dart';
import 'premium_ui.dart';

class SafetyStatusBanner extends StatelessWidget {
  const SafetyStatusBanner({
    super.key,
    required this.protectionStatus,
    required this.backendStatus,
    this.message,
  });

  final ProtectionStatus protectionStatus;
  final BackendStatus backendStatus;
  final String? message;

  @override
  Widget build(BuildContext context) {
    final emergency = protectionStatus == ProtectionStatus.emergency ||
        protectionStatus == ProtectionStatus.silentEmergency;
    final color = emergency
        ? AppTheme.emergency
        : backendStatus == BackendStatus.connected
            ? AppTheme.safe
            : AppTheme.warning;
    return GlassCard(
      width: double.infinity,
      glowColor: color,
      padding: const EdgeInsets.all(18),
      child: Row(
        children: [
          Stack(
            alignment: Alignment.center,
            children: [
              GlowIcon(
                icon: emergency ? Icons.emergency : Icons.shield,
                color: color,
                size: 52,
              ),
              Positioned(
                right: 3,
                top: 3,
                child: PulsingDot(color: color),
              ),
            ],
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  emergency ? 'Emergency Active' : 'Protected',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.w900,
                      ),
                ),
                const SizedBox(height: 3),
                Text(
                  message ??
                      (backendStatus == BackendStatus.connected
                          ? 'SheGuard is watching over you.'
                          : 'Reconnecting to safety network...'),
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: .72),
                    height: 1.35,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
