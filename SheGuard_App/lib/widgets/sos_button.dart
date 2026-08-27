import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../core/app_theme.dart';

class SosButton extends StatefulWidget {
  const SosButton({
    super.key,
    required this.onConfirmed,
    this.onLongPress,
    this.loading = false,
  });

  final VoidCallback onConfirmed;
  final VoidCallback? onLongPress;
  final bool loading;

  @override
  State<SosButton> createState() => _SosButtonState();
}

class _SosButtonState extends State<SosButton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _pulse;
  double _holdProgress = 0;
  bool _holding = false;

  @override
  void initState() {
    super.initState();
    _pulse = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
      lowerBound: .96,
      upperBound: 1.04,
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulse.dispose();
    super.dispose();
  }

  void _startHold() {
    if (widget.loading) return;
    HapticFeedback.lightImpact();
    setState(() {
      _holding = true;
      _holdProgress = 0;
    });
    _tickHold();
  }

  Future<void> _tickHold() async {
    while (mounted && _holding && _holdProgress < 1) {
      await Future.delayed(const Duration(milliseconds: 45));
      if (!mounted || !_holding) return;
      setState(() => _holdProgress += .035);
    }
    if (mounted && _holding && _holdProgress >= 1) {
      HapticFeedback.heavyImpact();
      setState(() {
        _holding = false;
        _holdProgress = 0;
      });
      widget.onConfirmed();
    }
  }

  void _cancelHold() {
    if (!_holding) return;
    setState(() {
      _holding = false;
      _holdProgress = 0;
    });
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _pulse,
      builder: (context, _) {
        final breathing = _pulse.value;
        final holdingBoost = _holding ? .14 : 0.0;
        return Transform.scale(
          scale: breathing,
          child: GestureDetector(
            onLongPress: () {
              _cancelHold();
              HapticFeedback.mediumImpact();
              widget.onLongPress?.call();
            },
            onTapDown: (_) => _startHold(),
            onTapUp: (_) => _cancelHold(),
            onTapCancel: _cancelHold,
            child: SizedBox(
              width: 218,
              height: 218,
              child: Stack(
                fit: StackFit.expand,
                children: [
                  _RippleRing(
                    scale: 1.12 + (_pulse.value - 1) * 3,
                    color: AppTheme.emergency.withValues(alpha: .16),
                  ),
                  _RippleRing(
                    scale: 1.33 + (_pulse.value - 1) * 4,
                    color: AppTheme.emergency.withValues(alpha: .07),
                  ),
                  CircularProgressIndicator(
                    value:
                        _holding ? _holdProgress.clamp(0, 1).toDouble() : null,
                    strokeWidth: 8,
                    color: Colors.white,
                    backgroundColor: AppTheme.emergency.withValues(alpha: .18),
                  ),
                  DecoratedBox(
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: const RadialGradient(
                        colors: [
                          Color(0xFFFF6A75),
                          AppTheme.emergency,
                          AppTheme.emergencyDeep,
                        ],
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: AppTheme.emergency
                              .withValues(alpha: .44 + holdingBoost),
                          blurRadius: 48 + holdingBoost * 80,
                          spreadRadius: 8 + holdingBoost * 18,
                        ),
                        BoxShadow(
                          color: Colors.black.withValues(alpha: .42),
                          blurRadius: 30,
                          offset: const Offset(0, 20),
                        ),
                      ],
                    ),
                    child: Center(
                      child: widget.loading
                          ? const _LoadingSos()
                          : Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(
                                  _holding ? Icons.bolt : Icons.shield,
                                  size: 46,
                                  color: Colors.white,
                                ),
                                const SizedBox(height: 8),
                                const Text(
                                  'SOS',
                                  style: TextStyle(
                                    color: Colors.white,
                                    fontSize: 32,
                                    fontWeight: FontWeight.w900,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  _holding
                                      ? 'Activating...'
                                      : 'Hold to send help',
                                  style: const TextStyle(
                                    color: Colors.white70,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                              ],
                            ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _RippleRing extends StatelessWidget {
  const _RippleRing({required this.scale, required this.color});

  final double scale;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Transform.scale(
      scale: scale,
      child: DecoratedBox(
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          border: Border.all(color: color, width: 2),
          boxShadow: [
            BoxShadow(color: color, blurRadius: 24, spreadRadius: 2),
          ],
        ),
      ),
    );
  }
}

class _LoadingSos extends StatelessWidget {
  const _LoadingSos();

  @override
  Widget build(BuildContext context) {
    return const Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        SizedBox(
          width: 34,
          height: 34,
          child: CircularProgressIndicator(color: Colors.white, strokeWidth: 3),
        ),
        SizedBox(height: 14),
        Text(
          'Sending help',
          style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800),
        ),
      ],
    );
  }
}
