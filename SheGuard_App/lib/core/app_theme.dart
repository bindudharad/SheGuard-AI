import 'package:flutter/material.dart';

class AppTheme {
  static const Color navy = Color(0xFF050B18);
  static const Color navy2 = Color(0xFF0C1830);
  static const Color ink = Color(0xFF080B12);
  static const Color glass = Color(0xFF121D32);
  static const Color emergency = Color(0xFFFF3448);
  static const Color emergencyDeep = Color(0xFF9E1525);
  static const Color safe = Color(0xFF3EE68D);
  static const Color cyan = Color(0xFF4EDBFF);
  static const Color surface = Color(0xFFF7F9FC);
  static const Color warning = Color(0xFFFFC65C);

  static ThemeData light() {
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: emergency,
        brightness: Brightness.light,
        primary: navy,
        secondary: emergency,
        surface: surface,
      ),
      scaffoldBackgroundColor: surface,
      cardTheme: CardThemeData(
        elevation: 0,
        color: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: surface,
        foregroundColor: navy,
        centerTitle: false,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          minimumSize: const Size.fromHeight(48),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
        filled: true,
        fillColor: Colors.white,
      ),
    );
  }

  static ThemeData dark() {
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: emergency,
        brightness: Brightness.dark,
        primary: Colors.white,
        secondary: emergency,
        surface: navy,
      ),
      scaffoldBackgroundColor: navy,
      cardTheme: CardThemeData(
        elevation: 0,
        color: glass.withValues(alpha: .82),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.transparent,
        foregroundColor: Colors.white,
        centerTitle: false,
        elevation: 0,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          minimumSize: const Size.fromHeight(48),
          foregroundColor: Colors.white,
          backgroundColor: emergency,
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(18)),
        filled: true,
        fillColor: Colors.white.withValues(alpha: .07),
      ),
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith(
          (states) =>
              states.contains(WidgetState.selected) ? safe : Colors.white70,
        ),
        trackColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.selected)
              ? safe.withValues(alpha: .28)
              : Colors.white.withValues(alpha: .12),
        ),
      ),
    );
  }
}
