import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../../domain/entities/question.dart';
import '../theme/app_theme.dart';
import 'difficulty_badge.dart';

/// Card responsivo que exibe o resumo de uma questão na lista.
class QuestionCard extends StatelessWidget {
  final Question question;
  final int index;
  final VoidCallback? onEdit;
  final VoidCallback? onDelete;
  final bool isSelected;
  final VoidCallback? onTap;

  const QuestionCard({
    super.key,
    required this.question,
    required this.index,
    this.onEdit,
    this.onDelete,
    this.isSelected = false,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final hasObs = question.obs.isNotEmpty;

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border: isSelected
                ? Border.all(color: AppColors.primary, width: 2)
                : null,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header colorido
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      AppColors.primary.withAlpha(isDark ? 40 : 20),
                      AppColors.secondary.withAlpha(isDark ? 20 : 10),
                    ],
                  ),
                  borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
                ),
                child: Row(
                  children: [
                    // Número
                    Container(
                      width: 28,
                      height: 28,
                      decoration: BoxDecoration(
                        color: AppColors.primary.withAlpha(isDark ? 60 : 40),
                        shape: BoxShape.circle,
                      ),
                      child: Center(
                        child: Text(
                          '${index + 1}',
                          style: theme.textTheme.labelLarge?.copyWith(
                            color: AppColors.primary,
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),

                    // Tipo
                    _TypeChip(tipo: question.tipo),
                    const SizedBox(width: 8),

                    // Dificuldade
                    DifficultyBadge(
                      dificuldade: question.dificuldade,
                      compact: true,
                    ),

                    const Spacer(),

                    // Ícone de feedback
                    if (hasObs)
                      Tooltip(
                        message: '${question.obs.length} item(s) de feedback',
                        child: Container(
                          padding: const EdgeInsets.all(4),
                          decoration: BoxDecoration(
                            color: AppColors.secondary.withAlpha(30),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: const Icon(
                            Icons.comment_rounded,
                            size: 14,
                            color: AppColors.secondary,
                          ),
                        ),
                      ),

                    if (hasObs) const SizedBox(width: 8),

                    // Ações
                    if (onEdit != null)
                      IconButton(
                        icon: const Icon(Icons.edit_rounded, size: 18),
                        onPressed: onEdit,
                        tooltip: 'Editar questão',
                        color: theme.colorScheme.onSurface.withAlpha(160),
                        padding: EdgeInsets.zero,
                        constraints:
                            const BoxConstraints(minWidth: 32, minHeight: 32),
                      ),
                    if (onDelete != null)
                      IconButton(
                        icon: const Icon(Icons.delete_outline_rounded, size: 18),
                        onPressed: onDelete,
                        tooltip: 'Remover questão',
                        color: AppColors.hard.withAlpha(180),
                        padding: EdgeInsets.zero,
                        constraints:
                            const BoxConstraints(minWidth: 32, minHeight: 32),
                      ),
                  ],
                ),
              ),

              // Corpo
              Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Enunciado
                    Text(
                      question.enunciado,
                      style: theme.textTheme.bodyLarge?.copyWith(
                        fontWeight: FontWeight.w500,
                      ),
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                    ),

                    if (question.alternativas.isNotEmpty) ...[
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 6,
                        runSpacing: 4,
                        children: question.alternativas.take(4).map((alt) {
                          final isCorrect = alt == question.correta;
                          return Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 10, vertical: 4),
                            decoration: BoxDecoration(
                              color: isCorrect
                                  ? AppColors.easy.withAlpha(30)
                                  : theme.colorScheme.surfaceContainerHighest,
                              borderRadius: BorderRadius.circular(8),
                              border: isCorrect
                                  ? Border.all(
                                      color: AppColors.easy.withAlpha(100))
                                  : null,
                            ),
                            child: Text(
                              alt.length > 40 ? '${alt.substring(0, 40)}…' : alt,
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: isCorrect ? AppColors.easy : null,
                                fontWeight: isCorrect ? FontWeight.w600 : null,
                              ),
                            ),
                          );
                        }).toList(),
                      ),
                    ],

                    if (question.variaveis.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Icon(Icons.functions_rounded,
                              size: 13,
                              color: AppColors.tertiary.withAlpha(180)),
                          const SizedBox(width: 4),
                          Text(
                            '${question.variaveis.length} variável(is) dinâmica(s)',
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: AppColors.tertiary,
                              fontStyle: FontStyle.italic,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    )
        .animate()
        .fadeIn(duration: 200.ms, delay: Duration(milliseconds: index * 30));
  }
}

class _TypeChip extends StatelessWidget {
  final int tipo;
  const _TypeChip({required this.tipo});

  @override
  Widget build(BuildContext context) {
    final (label, color) = switch (tipo) {
      1 => ('Texto', AppColors.primary),
      2 => ('Imagem', AppColors.tertiary),
      3 => ('Matemática', AppColors.secondary),
      4 => ('Afirmações', const Color(0xFF8E24AA)),
      _ => ('Tipo $tipo', Colors.grey),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
      decoration: BoxDecoration(
        color: color.withAlpha(20),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withAlpha(60)),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 10,
          fontWeight: FontWeight.w700,
          color: color,
          letterSpacing: 0.3,
        ),
      ),
    );
  }
}
