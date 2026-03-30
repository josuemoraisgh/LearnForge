import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Paleta de cores vigorosa do LearnForge.
class AppColors {
  AppColors._();

  // Primária: roxo elétrico
  static const primary = Color(0xFF6C63FF);
  static const primaryLight = Color(0xFF9C94FF);
  static const primaryDark = Color(0xFF3D35CC);

  // Secundária: teal vibrante
  static const secondary = Color(0xFF00BFA5);
  static const secondaryLight = Color(0xFF5DF2D6);
  static const secondaryDark = Color(0xFF008E76);

  // Terciária: laranja quente
  static const tertiary = Color(0xFFFF6B35);
  static const tertiaryLight = Color(0xFFFF9A65);
  static const tertiaryDark = Color(0xFFC43D07);

  // Dificuldade
  static const easy = Color(0xFF43A047);
  static const medium = Color(0xFFFFA000);
  static const hard = Color(0xFFE53935);

  // Superfícies
  static const backgroundLight = Color(0xFFF5F4FF);
  static const surfaceLight = Color(0xFFFFFFFF);
  static const backgroundDark = Color(0xFF0F0E1A);
  static const surfaceDark = Color(0xFF1C1B2E);
  static const cardDark = Color(0xFF252438);

  // Texto
  static const onPrimary = Color(0xFFFFFFFF);
  static const onSecondary = Color(0xFF003C33);
}

class AppTheme {
  AppTheme._();

  static ThemeData get light => _buildTheme(Brightness.light);
  static ThemeData get dark => _buildTheme(Brightness.dark);

  static ThemeData _buildTheme(Brightness brightness) {
    final isDark = brightness == Brightness.dark;

    final colorScheme = ColorScheme(
      brightness: brightness,
      primary: AppColors.primary,
      onPrimary: AppColors.onPrimary,
      primaryContainer: isDark ? AppColors.primaryDark : AppColors.primaryLight,
      onPrimaryContainer: isDark ? AppColors.primaryLight : AppColors.primaryDark,
      secondary: AppColors.secondary,
      onSecondary: AppColors.onSecondary,
      secondaryContainer: isDark ? AppColors.secondaryDark : AppColors.secondaryLight,
      onSecondaryContainer: isDark ? AppColors.secondaryLight : AppColors.secondaryDark,
      tertiary: AppColors.tertiary,
      onTertiary: AppColors.onPrimary,
      tertiaryContainer: isDark ? AppColors.tertiaryDark : AppColors.tertiaryLight,
      onTertiaryContainer: isDark ? AppColors.tertiaryLight : AppColors.tertiaryDark,
      error: const Color(0xFFCF6679),
      onError: AppColors.onPrimary,
      errorContainer: const Color(0xFF8C1D18),
      onErrorContainer: const Color(0xFFF9DEDC),
      surface: isDark ? AppColors.surfaceDark : AppColors.surfaceLight,
      onSurface: isDark ? Colors.white : Colors.black87,
      surfaceContainerHighest:
          isDark ? AppColors.cardDark : const Color(0xFFEDECFF),
      onSurfaceVariant: isDark ? Colors.white70 : Colors.black54,
      outline: isDark ? Colors.white24 : Colors.black12,
      outlineVariant: isDark ? Colors.white12 : Colors.black26,
      shadow: Colors.black,
      scrim: Colors.black,
      inverseSurface: isDark ? AppColors.surfaceLight : AppColors.surfaceDark,
      onInverseSurface: isDark ? Colors.black : Colors.white,
      inversePrimary: AppColors.primaryLight,
    );

    final base = ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      scaffoldBackgroundColor:
          isDark ? AppColors.backgroundDark : AppColors.backgroundLight,
    );

    return base.copyWith(
      textTheme: GoogleFonts.interTextTheme(base.textTheme).copyWith(
        displayLarge: GoogleFonts.poppins(
          fontSize: 32,
          fontWeight: FontWeight.w700,
          color: colorScheme.onSurface,
        ),
        titleLarge: GoogleFonts.poppins(
          fontSize: 20,
          fontWeight: FontWeight.w600,
          color: colorScheme.onSurface,
        ),
        titleMedium: GoogleFonts.poppins(
          fontSize: 16,
          fontWeight: FontWeight.w500,
          color: colorScheme.onSurface,
        ),
        bodyLarge: GoogleFonts.inter(fontSize: 15, color: colorScheme.onSurface),
        bodyMedium: GoogleFonts.inter(fontSize: 14, color: colorScheme.onSurface),
        labelLarge: GoogleFonts.inter(
          fontSize: 14,
          fontWeight: FontWeight.w600,
          color: colorScheme.onSurface,
        ),
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: colorScheme.outlineVariant),
        ),
        color: isDark ? AppColors.cardDark : AppColors.surfaceLight,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: isDark
            ? Colors.white.withAlpha(13)
            : AppColors.primary.withAlpha(8),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: colorScheme.outline),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: colorScheme.outline),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.primary, width: 2),
        ),
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: AppColors.onPrimary,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          textStyle: GoogleFonts.inter(
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: AppColors.secondary,
          foregroundColor: AppColors.onPrimary,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.primary,
          side: const BorderSide(color: AppColors.primary),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
      chipTheme: ChipThemeData(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        padding: const EdgeInsets.symmetric(horizontal: 8),
      ),
      navigationRailTheme: NavigationRailThemeData(
        backgroundColor: isDark ? AppColors.surfaceDark : AppColors.surfaceLight,
        selectedIconTheme:
            const IconThemeData(color: AppColors.primary, size: 24),
        unselectedIconTheme:
            IconThemeData(color: colorScheme.onSurface.withAlpha(130), size: 22),
        selectedLabelTextStyle: GoogleFonts.inter(
          color: AppColors.primary,
          fontWeight: FontWeight.w600,
          fontSize: 12,
        ),
        unselectedLabelTextStyle: GoogleFonts.inter(
          color: colorScheme.onSurface.withAlpha(130),
          fontSize: 12,
        ),
        indicatorColor: AppColors.primary.withAlpha(30),
      ),
      tabBarTheme: TabBarThemeData(
        labelColor: AppColors.primary,
        unselectedLabelColor: colorScheme.onSurface.withAlpha(130),
        indicator: const UnderlineTabIndicator(
          borderSide: BorderSide(color: AppColors.primary, width: 2.5),
        ),
        labelStyle: GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 13),
        unselectedLabelStyle: GoogleFonts.inter(fontSize: 13),
      ),
      dividerTheme: DividerThemeData(
        color: colorScheme.outlineVariant,
        thickness: 1,
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        backgroundColor: isDark ? AppColors.cardDark : AppColors.primaryDark,
        contentTextStyle:
            GoogleFonts.inter(color: Colors.white, fontSize: 14),
      ),
    );
  }

  /// Cor associada à dificuldade.
  static Color difficultyColor(String dificuldade) {
    switch (dificuldade.toLowerCase()) {
      case 'fácil':
      case 'facil':
        return AppColors.easy;
      case 'difícil':
      case 'dificil':
        return AppColors.hard;
      default:
        return AppColors.medium;
    }
  }
}
