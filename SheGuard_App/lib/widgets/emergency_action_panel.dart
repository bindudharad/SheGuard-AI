import 'package:flutter/material.dart';

import '../core/app_theme.dart';
import 'premium_ui.dart';
import 'sos_button.dart';

class EmergencyActionPanel extends StatelessWidget {
  const EmergencyActionPanel({
    super.key,
    required this.onSos,
    required this.onSilentSos,
    required this.onHelp,
    required this.silentEnabled,
    required this.loading,
    this.helpActive = false,
    this.helpCountdownSeconds = 0,
    this.onCancelHelp,
  });

  final VoidCallback onSos;
  final VoidCallback onSilentSos;
  final VoidCallback onHelp;
  final bool silentEnabled;
  final bool loading;
  final bool helpActive;
  final int helpCountdownSeconds;
  final VoidCallback? onCancelHelp;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      glowColor: AppTheme.emergency,
      margin: const EdgeInsets.symmetric(vertical: 18),
      padding: const EdgeInsets.symmetric(vertical: 28, horizontal: 18),
      width: double.infinity,
      child: Column(
        children: [
          SosButton(
            loading: loading,
            onConfirmed: onSos,
            onLongPress: silentEnabled ? onSilentSos : null,
          ),
          const SizedBox(height: 12),
          if (helpActive)
            _HelpCountdownCard(
              countdownSeconds: helpCountdownSeconds,
              onCancel: onCancelHelp,
            )
          else
            _ActionButtons(
              onHelp: onHelp,
              silentEnabled: silentEnabled,
            ),
        ],
      ),
    );
  }
}

class _HelpCountdownCard extends StatelessWidget {
  const _HelpCountdownCard({
    required this.countdownSeconds,
    this.onCancel,
  });

  final int countdownSeconds;
  final VoidCallback? onCancel;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 16),
      decoration: BoxDecoration(
        color: AppTheme.warning.withValues(alpha: .15),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.warning.withValues(alpha: .4)),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Icon(Icons.warning_amber_rounded, color: AppTheme.warning, size: 28),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  'Emergency detected',
                  style: TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w900,
                    fontSize: 18,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                decoration: BoxDecoration(
                  color: AppTheme.warning,
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  '\s',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w900,
                    fontSize: 20,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            'Tracking will start automatically',
            style: TextStyle(
              color: Colors.white.withValues(alpha: .7),
              fontWeight: FontWeight.w600,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: AppTheme.safe,
                side: BorderSide(color: AppTheme.safe.withValues(alpha: .6)),
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              onPressed: onCancel,
              icon: const Icon(Icons.close, size: 22),
              label: const Text(
                'CANCEL',
                style: TextStyle(
                  fontWeight: FontWeight.w900,
                  fontSize: 16,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ActionButtons extends StatelessWidget {
  const _ActionButtons({
    required this.onHelp,
    required this.silentEnabled,
  });

  final VoidCallback onHelp;
  final bool silentEnabled;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 16),
          decoration: BoxDecoration(
            color: AppTheme.cyan.withValues(alpha: .12),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppTheme.cyan.withValues(alpha: .3)),
          ),
          child: InkWell(
            onTap: onHelp,
            borderRadius: BorderRadius.circular(16),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.hearing, color: AppTheme.cyan, size: 24),
                const SizedBox(width: 12),
                Text(
                  'Say or tap HELP',
                  style: TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                    fontSize: 16,
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 10),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: .06),
            borderRadius: BorderRadius.circular(999),
            border: Border.all(color: Colors.white.withValues(alpha: .08)),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                silentEnabled ? Icons.visibility_off : Icons.touch_app,
                color: silentEnabled ? AppTheme.cyan : Colors.white70,
                size: 17,
              ),
              const SizedBox(width: 8),
              Flexible(
                child: Text(
                  silentEnabled
                      ? 'Long press SOS for silent emergency'
                      : 'Hold SOS to send help',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        color: Colors.white.withValues(alpha: .78),
                        fontWeight: FontWeight.w700,
                      ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}