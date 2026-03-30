import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// Badge de dificuldade com cor e ícone correspondentes.
class DifficultyBadge extends StatelessWidget {
  final String dificuldade;
  final bool compact;

  const DifficultyBadge({
    super.key,
    required this.dificuldade,
    this.compact = false,
  });

  @override
  Widget build(BuildContext context) {
    final color = AppTheme.difficultyColor(dificuldade);
    final label = _label(dificuldade);
    final icon = _icon(dificuldade);

    if (compact) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: color.withAlpha(30),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: color.withAlpha(80)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 11, color: color),
            const SizedBox(width: 4),
            Text(
              label,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: color,
              ),
            ),
          ],
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withAlpha(20),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: color.withAlpha(100)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  String _label(String d) {
    switch (d.toLowerCase()) {
      case 'fácil':
      case 'facil':
        return 'Fácil';
      case 'difícil':
      case 'dificil':
        return 'Difícil';
      default:
        return 'Média';
    }
  }

  IconData _icon(String d) {
    switch (d.toLowerCase()) {
      case 'fácil':
      case 'facil':
        return Icons.sentiment_satisfied_rounded;
      case 'difícil':
      case 'dificil':
        return Icons.local_fire_department_rounded;
      default:
        return Icons.sentiment_neutral_rounded;
    }
  }
}
