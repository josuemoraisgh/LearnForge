import 'package:desktop_drop/desktop_drop.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gap/gap.dart';
import '../../domain/entities/question.dart';
import '../providers/questions_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/question_card.dart';
import 'question_editor_screen.dart';

/// Tela de listagem e gerenciamento de questões.
class QuestionListScreen extends ConsumerStatefulWidget {
  const QuestionListScreen({super.key});

  @override
  ConsumerState<QuestionListScreen> createState() => _QuestionListScreenState();
}

class _QuestionListScreenState extends ConsumerState<QuestionListScreen> {
  String _searchQuery = '';
  String _filterDifficulty = 'Todas';
  bool _isDragging = false;
  final _searchController = TextEditingController();

  static const _difficulties = ['Todas', 'Fácil', 'Média', 'Difícil'];

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<({int index, dynamic q})> get _filtered {
    final questions = ref.read(questionsProvider).questions;
    return questions.asMap().entries.where((e) {
      final q = e.value;
      final matchSearch = _searchQuery.isEmpty ||
          q.enunciado.toLowerCase().contains(_searchQuery.toLowerCase()) ||
          q.alternativas
              .any((a) => a.toLowerCase().contains(_searchQuery.toLowerCase()));
      final matchDiff = _filterDifficulty == 'Todas' ||
          q.dificuldade.toLowerCase() ==
              _filterDifficulty.toLowerCase();
      return matchSearch && matchDiff;
    }).map((e) => (index: e.key, q: e.value)).toList();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(questionsProvider);
    final theme = Theme.of(context);
    final filtered = _filtered;

    return DropTarget(
      onDragDone: (detail) async {
        for (final file in detail.files) {
          await ref.read(questionsProvider.notifier).addFile(file.path);
        }
      },
      onDragEntered: (_) => setState(() => _isDragging = true),
      onDragExited: (_) => setState(() => _isDragging = false),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        decoration: BoxDecoration(
          border: _isDragging
              ? Border.all(color: AppColors.primary, width: 3)
              : null,
        ),
        child: Column(
          children: [
            // ── App bar ─────────────────────────────────────────────────────
            _buildHeader(context, state, theme),

            // ── Filtros e busca ─────────────────────────────────────────────
            if (state.questions.isNotEmpty) _buildFilters(context, theme),

            // ── Lista / Estado vazio ─────────────────────────────────────────
            Expanded(
              child: state.isLoading
                  ? const Center(
                      child: CircularProgressIndicator(
                        color: AppColors.primary,
                      ),
                    )
                  : state.isEmpty
                      ? _buildEmptyState(context, theme)
                      : filtered.isEmpty
                          ? _buildNoResultsState(theme)
                          : _buildList(filtered, theme),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(
      BuildContext context, QuestionsState state, ThemeData theme) {
    return Container(
      padding: const EdgeInsets.fromLTRB(24, 20, 16, 16),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        border: Border(
          bottom: BorderSide(color: theme.colorScheme.outlineVariant),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Questões', style: theme.textTheme.titleLarge),
                Text(
                  '${state.count} questão(ões) carregada(s)',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurface.withAlpha(130),
                  ),
                ),
              ],
            ),
          ),

          // Arquivos carregados
          if (state.filePaths.isNotEmpty)
            _FilesChip(
              paths: state.filePaths,
              onRemove: (p) =>
                  ref.read(questionsProvider.notifier).removeFile(p),
            ),
          const Gap(8),

          // Adicionar arquivo
          FilledButton.icon(
            onPressed: _pickFile,
            icon: const Icon(Icons.add_rounded, size: 18),
            label: const Text('Adicionar JSON'),
          ),

          if (state.questions.isNotEmpty) ...[
            const Gap(8),
            OutlinedButton.icon(
              onPressed: _addNewQuestion,
              icon: const Icon(Icons.post_add_rounded, size: 18),
              label: const Text('Nova questão'),
            ),
            const Gap(8),
            IconButton(
              icon: const Icon(Icons.delete_sweep_outlined),
              tooltip: 'Limpar tudo',
              onPressed: () => _confirmClear(context),
              color: AppColors.hard.withAlpha(180),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildFilters(BuildContext context, ThemeData theme) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      color: theme.colorScheme.surface,
      child: Row(
        children: [
          // Busca
          Expanded(
            child: SizedBox(
              height: 40,
              child: TextField(
                controller: _searchController,
                onChanged: (v) => setState(() => _searchQuery = v),
                decoration: InputDecoration(
                  hintText: 'Buscar questões…',
                  prefixIcon: const Icon(Icons.search_rounded, size: 18),
                  suffixIcon: _searchQuery.isNotEmpty
                      ? IconButton(
                          icon: const Icon(Icons.clear_rounded, size: 16),
                          onPressed: () {
                            _searchController.clear();
                            setState(() => _searchQuery = '');
                          },
                        )
                      : null,
                  isDense: true,
                  contentPadding: EdgeInsets.zero,
                ),
              ),
            ),
          ),
          const Gap(12),

          // Filtro de dificuldade
          SegmentedButton<String>(
            segments: _difficulties.map((d) {
              final color = d == 'Todas'
                  ? theme.colorScheme.onSurface
                  : AppTheme.difficultyColor(d);
              return ButtonSegment<String>(
                value: d,
                label: Text(
                  d,
                  style: TextStyle(fontSize: 11, color: color),
                ),
              );
            }).toList(),
            selected: {_filterDifficulty},
            onSelectionChanged: (s) =>
                setState(() => _filterDifficulty = s.first),
            style: const ButtonStyle(
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              visualDensity: VisualDensity.compact,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildList(List<({int index, dynamic q})> items, ThemeData theme) {
    return ListView.builder(
      padding: const EdgeInsets.only(bottom: 80, top: 8),
      itemCount: items.length,
      itemBuilder: (context, i) {
        final item = items[i];
        return QuestionCard(
          question: item.q,
          index: item.index,
          onEdit: () => _openEditor(item.index),
          onDelete: () =>
              ref.read(questionsProvider.notifier).removeQuestion(item.index),
          onTap: () => _openEditor(item.index),
        );
      },
    );
  }

  Widget _buildEmptyState(BuildContext context, ThemeData theme) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 120,
            height: 120,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  AppColors.primary.withAlpha(30),
                  AppColors.secondary.withAlpha(20),
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              shape: BoxShape.circle,
            ),
            child: Icon(
              Icons.cloud_upload_outlined,
              size: 56,
              color: AppColors.primary.withAlpha(180),
            ),
          )
              .animate(onPlay: (c) => c.repeat(reverse: true))
              .scaleXY(begin: 1, end: 1.05, duration: 2.seconds),

          const Gap(24),
          Text(
            'Nenhuma questão carregada',
            style: theme.textTheme.titleMedium,
          ),
          const Gap(8),
          Text(
            'Arraste arquivos JSON/ZIP aqui ou clique em\n"Adicionar JSON" para começar.',
            textAlign: TextAlign.center,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurface.withAlpha(130),
            ),
          ),
          const Gap(32),
          FilledButton.icon(
            onPressed: _pickFile,
            icon: const Icon(Icons.add_rounded),
            label: const Text('Adicionar arquivo JSON'),
          ),
        ],
      ),
    ).animate().fadeIn(duration: 400.ms);
  }

  Widget _buildNoResultsState(ThemeData theme) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.search_off_rounded,
              size: 56, color: theme.colorScheme.onSurface.withAlpha(80)),
          const Gap(16),
          Text('Nenhuma questão encontrada', style: theme.textTheme.titleMedium),
          const Gap(8),
          TextButton(
            onPressed: () {
              _searchController.clear();
              setState(() {
                _searchQuery = '';
                _filterDifficulty = 'Todas';
              });
            },
            child: const Text('Limpar filtros'),
          ),
        ],
      ),
    );
  }

  // ── Ações ────────────────────────────────────────────────────────────────────

  Future<void> _pickFile() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['json', 'zip'],
      allowMultiple: true,
    );
    if (result == null) return;
    for (final file in result.files) {
      if (file.path != null) {
        await ref.read(questionsProvider.notifier).addFile(file.path!);
      }
    }
  }

  void _openEditor(int index) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => QuestionEditorScreen(questionIndex: index),
      ),
    );
  }

  void _addNewQuestion() {
    ref.read(questionsProvider.notifier).addQuestion(
          const Question(enunciado: 'Nova questão'),
        );
    final newIndex = ref.read(questionsProvider).count - 1;
    _openEditor(newIndex);
  }

  Future<void> _confirmClear(BuildContext context) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Limpar tudo?'),
        content: const Text(
          'Todas as questões serão removidas da sessão.\n'
          'Os arquivos originais não serão afetados.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancelar'),
          ),
          ElevatedButton(
            style:
                ElevatedButton.styleFrom(backgroundColor: AppColors.hard),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Limpar'),
          ),
        ],
      ),
    );
    if (confirm == true) ref.read(questionsProvider.notifier).clearAll();
  }
}

// ── Chip de arquivos carregados ───────────────────────────────────────────────

class _FilesChip extends StatelessWidget {
  final List<String> paths;
  final ValueChanged<String> onRemove;

  const _FilesChip({required this.paths, required this.onRemove});

  @override
  Widget build(BuildContext context) {
    return PopupMenuButton<String>(
      tooltip: 'Arquivos carregados',
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
        decoration: BoxDecoration(
          color: AppColors.primary.withAlpha(20),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: AppColors.primary.withAlpha(60)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.folder_open_rounded,
                size: 16, color: AppColors.primary),
            const Gap(6),
            Text(
              '${paths.length} arquivo(s)',
              style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: AppColors.primary,
              ),
            ),
            const Gap(4),
            const Icon(Icons.keyboard_arrow_down_rounded,
                size: 14, color: AppColors.primary),
          ],
        ),
      ),
      itemBuilder: (_) => paths
          .map(
            (p) => PopupMenuItem<String>(
              value: p,
              child: Row(
                children: [
                  const Icon(Icons.insert_drive_file_outlined, size: 16),
                  const Gap(8),
                  Expanded(
                    child: Text(
                      p.split(RegExp(r'[/\\]')).last,
                      style: const TextStyle(fontSize: 13),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close_rounded,
                        size: 14, color: AppColors.hard),
                    onPressed: () {
                      Navigator.pop(context);
                      onRemove(p);
                    },
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(
                        minWidth: 24, minHeight: 24),
                  ),
                ],
              ),
            ),
          )
          .toList(),
    );
  }
}
