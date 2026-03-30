import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gap/gap.dart';
import '../providers/questions_provider.dart';
import '../theme/app_theme.dart';
import 'export_screen.dart';
import 'question_list_screen.dart';

/// Tela principal com NavigationRail responsiva.
class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  int _selectedIndex = 0;

  static const _destinations = [
    _NavDestination(
      icon: Icons.quiz_outlined,
      selectedIcon: Icons.quiz_rounded,
      label: 'Questões',
    ),
    _NavDestination(
      icon: Icons.file_download_outlined,
      selectedIcon: Icons.file_download_rounded,
      label: 'Exportar',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(questionsProvider);
    final size = MediaQuery.sizeOf(context);
    final isCompact = size.width < 720;

    // Exibe snackbar de erro/sucesso
    ref.listen<QuestionsState>(questionsProvider, (_, next) {
      if (!mounted) return;
      if (next.error != null) {
        _showSnack(next.error!, isError: true);
        ref.read(questionsProvider.notifier).clearMessages();
      } else if (next.successMessage != null) {
        _showSnack(next.successMessage!);
        ref.read(questionsProvider.notifier).clearMessages();
      }
    });

    final screens = [
      const QuestionListScreen(),
      const ExportScreen(),
    ];

    if (isCompact) {
      // Layout mobile: BottomNavigationBar
      return Scaffold(
        body: screens[_selectedIndex],
        bottomNavigationBar: NavigationBar(
          selectedIndex: _selectedIndex,
          onDestinationSelected: (i) => setState(() => _selectedIndex = i),
          destinations: _destinations
              .map((d) => NavigationDestination(
                    icon: Icon(d.icon),
                    selectedIcon: Icon(d.selectedIcon),
                    label: d.label,
                  ))
              .toList(),
          indicatorColor: AppColors.primary.withAlpha(40),
          backgroundColor: Theme.of(context).colorScheme.surface,
        ),
      );
    }

    // Layout desktop: NavigationRail lateral
    return Scaffold(
      body: Row(
        children: [
          _SideRail(
            selectedIndex: _selectedIndex,
            destinations: _destinations,
            questionCount: state.count,
            onDestinationSelected: (i) => setState(() => _selectedIndex = i),
          ),
          const VerticalDivider(width: 1),
          Expanded(child: screens[_selectedIndex]),
        ],
      ),
    );
  }

  void _showSnack(String message, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Row(
            children: [
              Icon(
                isError ? Icons.error_outline_rounded : Icons.check_circle_outline_rounded,
                color: Colors.white,
                size: 18,
              ),
              const SizedBox(width: 8),
              Expanded(child: Text(message)),
            ],
          ),
          backgroundColor: isError ? AppColors.hard : AppColors.secondaryDark,
          duration: const Duration(seconds: 4),
        ),
      );
  }
}

// ── NavigationRail lateral ────────────────────────────────────────────────────

class _SideRail extends StatelessWidget {
  final int selectedIndex;
  final List<_NavDestination> destinations;
  final int questionCount;
  final ValueChanged<int> onDestinationSelected;

  const _SideRail({
    required this.selectedIndex,
    required this.destinations,
    required this.questionCount,
    required this.onDestinationSelected,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Container(
      width: 88,
      color: isDark ? AppColors.surfaceDark : AppColors.surfaceLight,
      child: Column(
        children: [
          const Gap(16),
          // Logo / Brand
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [AppColors.primary, AppColors.secondary],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(14),
              boxShadow: [
                BoxShadow(
                  color: AppColors.primary.withAlpha(80),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: const Icon(Icons.school_rounded, color: Colors.white, size: 26),
          )
              .animate(onPlay: (c) => c.repeat(reverse: true))
              .shimmer(duration: 3.seconds, color: Colors.white30),

          const Gap(8),
          Text(
            'Learn\nForge',
            textAlign: TextAlign.center,
            style: theme.textTheme.labelSmall?.copyWith(
              fontWeight: FontWeight.w700,
              color: AppColors.primary,
              fontSize: 10,
              height: 1.2,
            ),
          ),

          const Gap(24),
          const Divider(indent: 16, endIndent: 16),
          const Gap(8),

          // Destinos
          ...destinations.asMap().entries.map((e) {
            final isSelected = e.key == selectedIndex;
            return _NavItem(
              icon: isSelected ? e.value.selectedIcon : e.value.icon,
              label: e.value.label,
              isSelected: isSelected,
              badge: e.key == 0 && questionCount > 0 ? questionCount : null,
              onTap: () => onDestinationSelected(e.key),
            );
          }),

          const Spacer(),
          // Versão
          Padding(
            padding: const EdgeInsets.only(bottom: 16),
            child: Text(
              'v1.0',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurface.withAlpha(80),
                fontSize: 10,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool isSelected;
  final int? badge;
  final VoidCallback onTap;

  const _NavItem({
    required this.icon,
    required this.label,
    required this.isSelected,
    required this.onTap,
    this.badge,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2, horizontal: 8),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(
            color: isSelected ? AppColors.primary.withAlpha(30) : Colors.transparent,
            borderRadius: BorderRadius.circular(14),
          ),
          child: Column(
            children: [
              Stack(
                clipBehavior: Clip.none,
                children: [
                  Icon(
                    icon,
                    size: 22,
                    color: isSelected
                        ? AppColors.primary
                        : theme.colorScheme.onSurface.withAlpha(120),
                  ),
                  if (badge != null)
                    Positioned(
                      right: -6,
                      top: -4,
                      child: Container(
                        padding: const EdgeInsets.all(3),
                        decoration: const BoxDecoration(
                          color: AppColors.tertiary,
                          shape: BoxShape.circle,
                        ),
                        child: Text(
                          badge! > 99 ? '99+' : '$badge',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 9,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ),
                ],
              ),
              const Gap(4),
              Text(
                label,
                style: theme.textTheme.labelSmall?.copyWith(
                  fontSize: 10,
                  color: isSelected
                      ? AppColors.primary
                      : theme.colorScheme.onSurface.withAlpha(120),
                  fontWeight:
                      isSelected ? FontWeight.w700 : FontWeight.normal,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _NavDestination {
  final IconData icon;
  final IconData selectedIcon;
  final String label;

  const _NavDestination({
    required this.icon,
    required this.selectedIcon,
    required this.label,
  });
}
