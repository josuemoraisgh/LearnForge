import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gap/gap.dart';
import '../../export/beamer_exporter.dart';
import '../../export/exporter_interface.dart';
import '../../export/moodle_xml_exporter.dart';
import '../providers/questions_provider.dart';
import '../theme/app_theme.dart';

/// Tela de exportação — suporta Moodle XML e LaTeX Beamer.
/// Aberta / Fechada para novos formatos: basta adicionar um IExporter.
class ExportScreen extends ConsumerStatefulWidget {
  const ExportScreen({super.key});

  @override
  ConsumerState<ExportScreen> createState() => _ExportScreenState();
}

class _ExportScreenState extends ConsumerState<ExportScreen> {
  // Exportadores disponíveis (Open/Closed Principle)
  static const _exporters = <IExporter>[
    MoodleXmlExporter(),
    BeamerExporter(),
  ];

  int _selectedExporter = 0;
  String _outputPath = '';

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(questionsProvider);
    final config = ref.watch(exportConfigProvider);
    final theme = Theme.of(context);
    final isEmpty = state.isEmpty;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 900),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Título ──────────────────────────────────────────────────────
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [AppColors.primary, AppColors.secondary],
                    ),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.file_download_rounded,
                      color: Colors.white, size: 22),
                ),
                const Gap(14),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Exportar Questões', style: theme.textTheme.titleLarge),
                    Text(
                      '${state.count} questão(ões) disponível(is)',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurface.withAlpha(130),
                      ),
                    ),
                  ],
                ),
              ],
            ),
            const Gap(32),

            // ── Aviso sem questões ───────────────────────────────────────────
            if (isEmpty) _buildEmptyWarning(context),

            // ── Seleção de formato ───────────────────────────────────────────
            Text('Formato de exportação', style: theme.textTheme.titleMedium),
            const Gap(12),
            Row(
              children: _exporters.asMap().entries.map((e) {
                final exporter = e.value;
                final isSelected = e.key == _selectedExporter;
                return Expanded(
                  child: GestureDetector(
                    onTap: () => setState(() => _selectedExporter = e.key),
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 180),
                      margin: EdgeInsets.only(
                          right: e.key < _exporters.length - 1 ? 12 : 0),
                      padding: const EdgeInsets.all(20),
                      decoration: BoxDecoration(
                        color: isSelected
                            ? AppColors.primary.withAlpha(20)
                            : theme.colorScheme.surface,
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(
                          color: isSelected
                              ? AppColors.primary
                              : theme.colorScheme.outlineVariant,
                          width: isSelected ? 2 : 1,
                        ),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Icon(
                                _exporterIcon(e.key),
                                color: isSelected
                                    ? AppColors.primary
                                    : theme.colorScheme.onSurface.withAlpha(160),
                                size: 28,
                              ),
                              const Spacer(),
                              if (isSelected)
                                const Icon(Icons.check_circle_rounded,
                                    color: AppColors.primary, size: 20),
                            ],
                          ),
                          const Gap(12),
                          Text(
                            exporter.label,
                            style: theme.textTheme.titleMedium?.copyWith(
                              color: isSelected ? AppColors.primary : null,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const Gap(4),
                          Text(
                            _exporterDescription(e.key),
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: theme.colorScheme.onSurface.withAlpha(130),
                            ),
                          ),
                          const Gap(8),
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: AppColors.primary.withAlpha(15),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              exporter.fileExtension,
                              style: const TextStyle(
                                fontFamily: 'monospace',
                                fontSize: 11,
                                fontWeight: FontWeight.w700,
                                color: AppColors.primary,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
            const Gap(28),

            // ── Configurações comuns ─────────────────────────────────────────
            Text('Configurações', style: theme.textTheme.titleMedium),
            const Gap(12),
            _buildConfigSection(context, config),
            const Gap(28),

            // ── Configurações específicas por formato ────────────────────────
            if (_selectedExporter == 1) ...[
              Text('Configurações Beamer', style: theme.textTheme.titleMedium),
              const Gap(12),
              _buildBeamerConfig(context, config),
              const Gap(28),
            ],

            // ── Saída ────────────────────────────────────────────────────────
            Text('Arquivo de saída', style: theme.textTheme.titleMedium),
            const Gap(12),
            _buildOutputPicker(context, config),
            const Gap(32),

            // ── Botão exportar ───────────────────────────────────────────────
            SizedBox(
              width: double.infinity,
              height: 52,
              child: ElevatedButton.icon(
                onPressed: (isEmpty || _outputPath.isEmpty)
                    ? null
                    : () => _export(config),
                icon: state.isLoading
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : Icon(_exporterIcon(_selectedExporter)),
                label: Text(
                  state.isLoading
                      ? 'Exportando…'
                      : 'Exportar ${_exporters[_selectedExporter].label}',
                  style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
                ),
              ),
            ).animate().fadeIn(duration: 300.ms),

            if (isEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  'Carregue questões antes de exportar',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: AppColors.medium,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),

            const Gap(40),

            // ── Nota sobre o campo OBS ───────────────────────────────────────
            _buildObsNote(context),
          ],
        ),
      ),
    );
  }

  Widget _buildConfigSection(BuildContext context, ExportConfig config) {
    final notifier = ref.read(exportConfigProvider.notifier);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    initialValue: config.title,
                    decoration: const InputDecoration(
                      labelText: 'Título da apresentação / prova',
                      prefixIcon: Icon(Icons.title_rounded, size: 18),
                    ),
                    onChanged: (v) => notifier.update(title: v),
                  ),
                ),
                const Gap(16),
                SizedBox(
                  width: 120,
                  child: TextFormField(
                    initialValue: config.seed.toString(),
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Seed',
                      prefixIcon: Icon(Icons.shuffle_rounded, size: 18),
                      hintText: '42',
                    ),
                    onChanged: (v) =>
                        notifier.update(seed: int.tryParse(v) ?? 42),
                  ),
                ),
              ],
            ),
            const Gap(12),
            Row(
              children: [
                Expanded(
                  child: CheckboxListTile(
                    value: config.shuffle,
                    onChanged: (v) => notifier.update(shuffle: v),
                    title: const Text('Embaralhar questões'),
                    subtitle: const Text(
                        'Usa a seed para ordem reprodutível'),
                    controlAffinity: ListTileControlAffinity.leading,
                    contentPadding: EdgeInsets.zero,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBeamerConfig(BuildContext context, ExportConfig config) {
    final notifier = ref.read(exportConfigProvider.notifier);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            Expanded(
              child: TextFormField(
                initialValue: config.fontSizeQuestion.toString(),
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Fonte questão (pt)',
                  prefixIcon: Icon(Icons.format_size_rounded, size: 18),
                ),
                onChanged: (v) => notifier.update(
                    fontSizeQuestion: int.tryParse(v) ?? 12),
              ),
            ),
            const Gap(16),
            Expanded(
              child: TextFormField(
                initialValue: config.fontSizeAnswer.toString(),
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Fonte alternativas (pt)',
                  prefixIcon: Icon(Icons.text_fields_rounded, size: 18),
                ),
                onChanged: (v) => notifier.update(
                    fontSizeAnswer: int.tryParse(v) ?? 11),
              ),
            ),
            const Gap(16),
            Expanded(
              child: DropdownButtonFormField<String>(
                initialValue: config.alertColor,
                decoration: const InputDecoration(
                  labelText: 'Cor do gabarito',
                  prefixIcon: Icon(Icons.color_lens_outlined, size: 18),
                ),
                items: const [
                  DropdownMenuItem(value: 'red', child: Text('Vermelho')),
                  DropdownMenuItem(value: 'blue', child: Text('Azul')),
                  DropdownMenuItem(value: 'green', child: Text('Verde')),
                  DropdownMenuItem(value: 'orange', child: Text('Laranja')),
                  DropdownMenuItem(value: 'violet', child: Text('Violeta')),
                ],
                onChanged: (v) => notifier.update(alertColor: v),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildOutputPicker(BuildContext context, ExportConfig config) {
    final exporter = _exporters[_selectedExporter];
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (_outputPath.isEmpty)
                    Text(
                      'Nenhum caminho selecionado',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: Theme.of(context)
                                .colorScheme
                                .onSurface
                                .withAlpha(100),
                            fontStyle: FontStyle.italic,
                          ),
                    )
                  else ...[
                    Text(
                      _outputPath.split(RegExp(r'[/\\]')).last,
                      style: const TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 14,
                      ),
                    ),
                    Text(
                      _outputPath,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Theme.of(context)
                                .colorScheme
                                .onSurface
                                .withAlpha(120),
                          ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ],
              ),
            ),
            const Gap(12),
            OutlinedButton.icon(
              onPressed: () => _pickOutputPath(exporter),
              icon: const Icon(Icons.folder_open_rounded, size: 18),
              label: const Text('Escolher caminho'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyWarning(BuildContext context) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 24),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.medium.withAlpha(20),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.medium.withAlpha(80)),
      ),
      child: Row(
        children: [
          const Icon(Icons.warning_amber_rounded,
              color: AppColors.medium, size: 20),
          const Gap(12),
          Expanded(
            child: Text(
              'Carregue questões na aba "Questões" antes de exportar.',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppColors.medium,
                  ),
            ),
          ),
        ],
      ),
    ).animate().shake(duration: 500.ms);
  }

  Widget _buildObsNote(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.secondary.withAlpha(12),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.secondary.withAlpha(60)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.info_outline_rounded,
                  size: 16, color: AppColors.secondary),
              const Gap(8),
              Text(
                'Campo "Feedback / Obs" nas exportações',
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      color: AppColors.secondary,
                    ),
              ),
            ],
          ),
          const Gap(10),
          Text(
            '• Moodle XML → Exportado como <generalfeedback>: texto exibido ao aluno após responder a questão.\n'
            '• LaTeX Beamer → Gera um frame extra com "OBS.:" entre a questão sem gabarito e com gabarito.\n'
            '\nEdite o campo "Feedback / Comentários" de cada questão para adicionar explicações e dicas.',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurface.withAlpha(160),
                  height: 1.7,
                ),
          ),
        ],
      ),
    );
  }

  // ── Ações ────────────────────────────────────────────────────────────────────

  Future<void> _pickOutputPath(IExporter exporter) async {
    final path = await FilePicker.platform.saveFile(
      dialogTitle: 'Salvar ${exporter.label}',
      fileName: 'questoes${exporter.fileExtension}',
      type: FileType.custom,
      allowedExtensions: [exporter.fileExtension.replaceAll('.', '')],
    );
    if (path != null) setState(() => _outputPath = path);
  }

  Future<void> _export(ExportConfig config) async {
    if (_outputPath.isEmpty) return;
    await ref.read(questionsProvider.notifier).exportTo(
          _exporters[_selectedExporter],
          _outputPath,
          config,
        );
  }

  IconData _exporterIcon(int index) {
    return switch (index) {
      0 => Icons.quiz_rounded,
      1 => Icons.slideshow_rounded,
      _ => Icons.file_download_rounded,
    };
  }

  String _exporterDescription(int index) {
    return switch (index) {
      0 => 'Importa no Moodle via Banco de Questões. Inclui feedback após resolução.',
      1 => 'Apresentação LaTeX com slides por questão e frame de observações.',
      _ => '',
    };
  }
}
