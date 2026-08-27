import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/app_theme.dart';
import '../providers/auth_provider.dart';
import '../providers/location_provider.dart';
import '../providers/safety_provider.dart';
import 'home_screen.dart';
import 'login_screen.dart';

enum StartupState {
  starting,
  checkingPermissions,
  checkingAuth,
  checkingNetwork,
  ready,
  loginRequired,
  permissionRequired,
  offline,
}

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  StartupState _startupState = StartupState.starting;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();

    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1100),
      lowerBound: .92,
      upperBound: 1,
    )..repeat(reverse: true);

    WidgetsBinding.instance.addPostFrameCallback((_) {
      _boot();
    });
  }

  Future<void> _boot() async {
    final safetyProvider = context.read<SafetyProvider>();
    final locationProvider = context.read<LocationProvider>();
    final auth = context.read<AuthProvider>();

    _setState(StartupState.checkingPermissions);

    // Check permissions
    await locationProvider.requestPermission();
    final permissionGranted = locationProvider.permissionGranted;
    if (!permissionGranted && mounted) {
      _setState(StartupState.permissionRequired);
      return;
    }

    _setState(StartupState.checkingAuth);

    // Check auth - restore session
    await auth.restore();

    _setState(StartupState.checkingNetwork);

    // Check network - don't block on this
    try {
      await Future.any([
        safetyProvider.refreshBackendStatus(),
        Future.delayed(const Duration(seconds: 3)),
      ]);
    } catch (_) {}

    // Small splash delay for UX
    await Future.delayed(const Duration(seconds: 1));

    if (!mounted) return;

    // Determine final state
    if (!safetyProvider.online) {
      _setState(StartupState.offline);
    } else if (!auth.isAuthenticated) {
      _setState(StartupState.loginRequired);
    } else {
      _setState(StartupState.ready);
    }

    // Navigate based on state
    await Future.delayed(const Duration(milliseconds: 500));
    if (!mounted) return;

    switch (_startupState) {
      case StartupState.ready:
        Navigator.pushReplacementNamed(context, HomeScreen.route);
        break;
      case StartupState.loginRequired:
        Navigator.pushReplacementNamed(context, LoginScreen.route);
        break;
      case StartupState.permissionRequired:
        Navigator.pushReplacementNamed(context, LoginScreen.route);
        break;
      case StartupState.offline:
        Navigator.pushReplacementNamed(context, HomeScreen.route);
        break;
      default:
        Navigator.pushReplacementNamed(context, LoginScreen.route);
    }
  }

  void _setState(StartupState state) {
    if (!mounted) return;
    setState(() {
      _startupState = state;
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final needsPermission = _startupState == StartupState.permissionRequired;
    final needsLogin = _startupState == StartupState.loginRequired;

    return Scaffold(
      backgroundColor: AppTheme.navy,
      body: SafeArea(
        child: Center(
          child: ScaleTransition(
            scale: _controller,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 104,
                    height: 104,
                    decoration: BoxDecoration(
                      color: AppTheme.emergency,
                      borderRadius: BorderRadius.circular(28),
                      boxShadow: [
                        BoxShadow(
                          color: AppTheme.emergency.withValues(alpha: .34),
                          blurRadius: 34,
                          spreadRadius: 6,
                        ),
                      ],
                    ),
                    child: const Icon(
                      Icons.shield,
                      color: Colors.white,
                      size: 58,
                    ),
                  ),
                  const SizedBox(height: 22),
                  const Text(
                    'SheGuard',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 32,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'AI-powered emergency protection',
                    style: TextStyle(
                      color: Colors.white70,
                    ),
                  ),
                  const SizedBox(height: 28),
                  _StartupStatusIndicator(state: _startupState),
                  const SizedBox(height: 24),
                  if (_errorMessage != null) ...[
                    Text(
                      _errorMessage!,
                      style: TextStyle(color: AppTheme.warning, fontSize: 14),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 16),
                  ],
                  if (needsPermission)
                    FilledButton.icon(
                      onPressed: () => _boot(),
                      icon: const Icon(Icons.gps_fixed),
                      label: const Text('Grant Location Permission'),
                      style: FilledButton.styleFrom(
                        backgroundColor: AppTheme.safe,
                        minimumSize: const Size.fromHeight(50),
                      ),
                    )
                  else if (needsLogin)
                    FilledButton.icon(
                      onPressed: () => _boot(),
                      icon: const Icon(Icons.login),
                      label: const Text('Sign In'),
                      style: FilledButton.styleFrom(
                        backgroundColor: AppTheme.cyan,
                        minimumSize: const Size.fromHeight(50),
                      ),
                    )
                  else
                    const SizedBox(
                      width: 150,
                      child: LinearProgressIndicator(
                        color: Colors.white,
                        backgroundColor: Colors.white24,
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _StartupStatusIndicator extends StatelessWidget {
  const _StartupStatusIndicator({required this.state});

  final StartupState state;

  @override
  Widget build(BuildContext context) {
    String label;
    Color color = AppTheme.cyan;

    switch (state) {
      case StartupState.starting:
        label = 'Initializing...';
        break;
      case StartupState.checkingPermissions:
        label = 'Checking permissions...';
        break;
      case StartupState.checkingAuth:
        label = 'Restoring session...';
        break;
      case StartupState.checkingNetwork:
        label = 'Checking connection...';
        break;
      case StartupState.ready:
        label = 'Ready';
        color = AppTheme.safe;
        break;
      case StartupState.loginRequired:
        label = 'Sign in required';
        color = AppTheme.warning;
        break;
      case StartupState.permissionRequired:
        label = 'Location permission needed';
        color = AppTheme.warning;
        break;
      case StartupState.offline:
        label = 'Offline mode';
        color = AppTheme.warning;
        break;
    }

    return Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 10,
              height: 10,
              decoration: BoxDecoration(
                color: color,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 10),
            Text(
              label,
              style: TextStyle(
                color: color,
                fontWeight: FontWeight.w700,
                fontSize: 15,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        SizedBox(
          width: 200,
          child: LinearProgressIndicator(
            value: _progressForState(state),
            color: color,
            backgroundColor: color.withValues(alpha: .2),
            minHeight: 4,
          ),
        ),
      ],
    );
  }

  double _progressForState(StartupState state) {
    switch (state) {
      case StartupState.starting:
        return 0.1;
      case StartupState.checkingPermissions:
        return 0.3;
      case StartupState.checkingAuth:
        return 0.5;
      case StartupState.checkingNetwork:
        return 0.7;
      case StartupState.ready:
      case StartupState.loginRequired:
      case StartupState.permissionRequired:
      case StartupState.offline:
        return 1.0;
    }
  }
}
