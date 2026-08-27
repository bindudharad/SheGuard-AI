import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/app_theme.dart';
import 'providers/auth_provider.dart';
import 'providers/contact_provider.dart';
import 'providers/incident_provider.dart';
import 'providers/location_provider.dart';
import 'providers/safety_provider.dart';
import 'providers/settings_provider.dart';
import 'screens/contacts_screen.dart';
import 'screens/home_screen.dart';
import 'screens/incident_history_screen.dart';
import 'screens/live_status_screen.dart';
import 'screens/login_screen.dart';
import 'screens/register_screen.dart';
import 'screens/emergency_mode_screen.dart';
import 'screens/settings_screen.dart';
import 'screens/splash_screen.dart';
import 'services/api_service.dart';
import 'services/auto_sos_manager.dart';
import 'services/auth_service.dart';
import 'services/backend_health_service.dart';
import 'services/connectivity_service.dart';
import 'services/contact_service.dart';
import 'services/emergency_call_service.dart';
import 'services/emergency_siren_service.dart';
import 'services/emergency_sms_service.dart';
import 'services/emergency_realtime_service.dart';
import 'services/evidence_capture_service.dart';
import 'services/foreground_tracking_service.dart';
import 'services/incident_service.dart';
import 'services/location_service.dart';
import 'services/local_contact_metadata_service.dart';
import 'services/motion_protection_service.dart';
import 'services/notification_service.dart';
import 'services/sos_service.dart';
import 'services/storage_service.dart';
import 'services/voice_help_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final notifications = NotificationService();
  await notifications.initialize();

  final api = ApiService();
  final storage = StorageService();
  final contactService = ContactService(api);
  final foregroundTrackingService = ForegroundTrackingService();
  await foregroundTrackingService.initialize();
  final locationService = LocationService(
    api,
    foregroundTracking: foregroundTrackingService,
  );
  final incidentService = IncidentService(api);
  final evidenceCaptureService = EvidenceCaptureService(api: api);
  final emergencyCallService = EmergencyCallService();
  final emergencySirenService = EmergencySirenService();
  final realtimeService = EmergencyRealtimeService(api, notifications);
  final sosService = SosService(
    locationService: locationService,
    incidentService: incidentService,
    smsService: EmergencySmsService(),
    callService: emergencyCallService,
    sirenService: emergencySirenService,
    apiService: api,
    evidenceCaptureService: evidenceCaptureService,
    notificationService: notifications,
  );
  final autoSosManager = AutoSosManager(
    api: api,
    realtime: realtimeService,
    contactService: contactService,
    locationService: locationService,
    sosService: sosService,
    notifications: notifications,
  );

  final voiceHelpService = VoiceHelpService();
  await voiceHelpService.initialize();
  voiceHelpService.startListening();

  runApp(SheGuardApp(
    api: api,
    storage: storage,
    notifications: notifications,
    contactService: contactService,
    locationService: locationService,
    incidentService: incidentService,
    sosService: sosService,
    emergencyCallService: emergencyCallService,
    emergencySirenService: emergencySirenService,
    motionProtectionService: MotionProtectionService(),
    autoSosManager: autoSosManager,
    voiceHelpService: voiceHelpService,
  ));
}

class SheGuardApp extends StatelessWidget {
  const SheGuardApp({
    super.key,
    required this.api,
    required this.storage,
    required this.notifications,
    required this.contactService,
    required this.locationService,
    required this.incidentService,
    required this.sosService,
    required this.emergencyCallService,
    required this.emergencySirenService,
    required this.motionProtectionService,
    required this.autoSosManager,
    required this.voiceHelpService,
  });

  final ApiService api;
  final StorageService storage;
  final NotificationService notifications;
  final ContactService contactService;
  final LocationService locationService;
  final IncidentService incidentService;
  final SosService sosService;
  final EmergencyCallService emergencyCallService;
  final EmergencySirenService emergencySirenService;
  final MotionProtectionService motionProtectionService;
  final AutoSosManager autoSosManager;
  final VoiceHelpService voiceHelpService;

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(
          create: (_) => AuthProvider(AuthService(api, storage))..restore(),
        ),
        Provider.value(value: api),
        ChangeNotifierProvider(
          create: (_) => ContactProvider(
            contactService,
            LocalContactMetadataService(),
          ),
        ),
        ChangeNotifierProvider(
          create: (_) => LocationProvider(locationService, notifications),
        ),
        ChangeNotifierProvider(
          create: (_) => IncidentProvider(incidentService, notifications),
        ),
        Provider.value(value: sosService),
        Provider.value(value: emergencyCallService),
        Provider.value(value: emergencySirenService),
        Provider.value(value: motionProtectionService),
        ChangeNotifierProvider.value(value: autoSosManager),
        ChangeNotifierProvider(
          create: (_) => SafetyProvider(
            BackendHealthService(api),
            ConnectivityService(),
            notifications,
          )..initialize(),
        ),
        ChangeNotifierProvider(create: (_) => SettingsProvider()..load()),
        Provider.value(value: voiceHelpService),
      ],
      child: MaterialApp(
        title: 'SheGuard',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light(),
        darkTheme: AppTheme.dark(),
        home: const SplashScreen(),
        routes: {
          LoginScreen.route: (_) => const LoginScreen(),
          RegisterScreen.route: (_) => const RegisterScreen(),
          HomeScreen.route: (_) => const HomeScreen(),
          ContactsScreen.route: (_) => const ContactsScreen(),
          LiveStatusScreen.route: (_) => const LiveStatusScreen(),
          IncidentHistoryScreen.route: (_) => const IncidentHistoryScreen(),
          EmergencyModeScreen.route: (_) => const EmergencyModeScreen(),
          SettingsScreen.route: (_) => const SettingsScreen(),
        },
      ),
    );
  }
}
