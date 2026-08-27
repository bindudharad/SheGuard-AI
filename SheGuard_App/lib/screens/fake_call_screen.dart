import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../core/app_theme.dart';

class FakeCallScreen extends StatefulWidget {
  const FakeCallScreen({super.key, this.callerName = 'Amma'});

  final String callerName;

  @override
  State<FakeCallScreen> createState() => _FakeCallScreenState();
}

class _FakeCallScreenState extends State<FakeCallScreen> {
  Timer? _pulse;

  @override
  void initState() {
    super.initState();
    _pulse = Timer.periodic(const Duration(milliseconds: 900), (_) {
      HapticFeedback.mediumImpact();
    });
  }

  @override
  void dispose() {
    _pulse?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.navy,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(
            children: [
              const Spacer(),
              CircleAvatar(
                radius: 54,
                backgroundColor: AppTheme.safe.withValues(alpha: .22),
                child: const Icon(Icons.person, color: Colors.white, size: 62),
              ),
              const SizedBox(height: 24),
              Text(
                widget.callerName,
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.w900,
                    ),
              ),
              const SizedBox(height: 8),
              const Text('Incoming call',
                  style: TextStyle(color: Colors.white70)),
              const Spacer(),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  FloatingActionButton.large(
                    heroTag: 'decline_fake_call',
                    backgroundColor: AppTheme.emergency,
                    onPressed: () => Navigator.pop(context),
                    child: const Icon(Icons.call_end),
                  ),
                  FloatingActionButton.large(
                    heroTag: 'answer_fake_call',
                    backgroundColor: AppTheme.safe,
                    onPressed: () => Navigator.pop(context),
                    child: const Icon(Icons.call),
                  ),
                ],
              ),
              const SizedBox(height: 34),
            ],
          ),
        ),
      ),
    );
  }
}
