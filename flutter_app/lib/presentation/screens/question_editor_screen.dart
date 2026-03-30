import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gap/gap.dart';
import '../../domain/entities/question.dart';
import '../providers/questions_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/difficulty_badge.dart';
import '../widgets/obs_feedback_panel.dart';

/// Tela de edição de questão com abas: Formulário, Preview e JSON bruto.
class QuestionEditorScreen extends ConsumerStatefulWidget {
  final int questionIndex;

  const QuestionEditorScreen({super.key, required this.questionIndex});

  @override
  ConsumerState<QuestionEditorScreen> createState() =>
      _QuestionEditorScreenState();
}

class _QuestionEditorScreenState extends ConsumerState<QuestionEditorScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabs;
  late int _currentIndex;
  late Question _local; // cópia local editável

  // Controllers — nullable para evitar LateInitializationError
  TextEditingController? _enunciadoCtrl;
  TextEditingController? _corretaCtrl;
  TextEditingController? _subenunciadoCtrl;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 3, vsync: this);
    _tabs.addListener(_onTabChanged);
    _currentIndex = widget.questionIndex;
    // NÃO chama dispose aqui — controllers ainda são null
    _initControllers();
  }

  @override
  void dispose() {
    _tabs.removeListener(_onTabChanged);
    _tabs.dispose();
    _enunciadoCtrl?.dispose();
    _corretaCtrl?.dispose();
    _subenunciadoCtrl?.dispose();
    super.dispose();
  }

  void _onTabChanged() => setState(() {});

  /// Cria os controllers para a questão atual (chamado apenas quando não há
  /// controllers anteriores — ex: initState).
  void _initControllers() {
    final q = ref.read(questionsProvider).questions[_currentIndex];
    _local = q;
    _enunciadoCtrl = TextEditingController(text: q.enunciado);
    _corretaCtrl = TextEditingController(text: q.correta);
    _subenunciadoCtrl = TextEditingController(text: q.subenunciado ?? '');
  }

  /// Troca de questão: descarta controllers existentes e cria novos.
  void _switchQuestion(int index) {
    _enunciadoCtrl?.dispose();
    _corretaCtrl?.dispose();
    _subenunciadoCtrl?.dispose();
    _currentIndex = index;
    _initControllers();
  }

  void _save() {
    final enunciado = _enunciadoCtrl?.text.trim() ?? '';
    final correta = _corretaCtrl?.text.trim() ?? '';
    final sub = _subenunciadoCtrl?.text.trim() ?? '';

    final updated = _local.copyWith(
      enunciado: enunciado,
      correta: correta,
      subenunciado: sub.isEmpty ? null : sub,
    );
    ref.read(questionsProvider.notifier).updateQuestion(_currentIndex, updated);
    setState(() => _local = updated);

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Row(
          children: [
            Icon(Icons.check_circle_outline_rounded,
                color: Colors.white, size: 16),
            Gap(8),
            Text('Questão salva'),
          ],
        ),
        backgroundColor: AppColors.secondaryDark,
        duration: Duration(seconds: 2),
      ),
    );
  }

  void _navigate(int delta) {
    _save();
    final total = ref.read(questionsProvider).count;
    final next = (_currentIndex + delta).clamp(0, total - 1);
    if (next == _currentIndex) return;
    setState(() => _switchQuestion(next));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final total = ref.watch(questionsProvider).count;
    final hasPrev = _currentIndex > 0;
    final hasNext = _currentIndex < total - 1;

    return CallbackShortcuts(
      bindings: {
        const SingleActivator(LogicalKeyboardKey.keyS, control: true): _save,
        const SingleActivator(LogicalKeyboardKey.arrowLeft, control: true): () {
          if (hasPrev) _navigate(-1);
        },
        const SingleActivator(LogicalKeyboardKey.arrowRight, control: true): () {
          if (hasNext) _navigate(1);
        },
      },
      child: Focus(
        autofocus: true,
        child: Scaffold(
          appBar: AppBar(
            title: Row(
              children: [
                Text(
                  'Q${_currentIndex + 1}/$total',
                  style: theme.textTheme.titleMedium?.copyWith(
                    color: AppColors.primary,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const Gap(12),
                DifficultyBadge(dificuldade: _local.dificuldade),
              ],
            ),
            actions: [
              // Navegação
              IconButton(
                icon: const Icon(Icons.chevron_left_rounded),
                onPressed: hasPrev ? () => _navigate(-1) : null,
                tooltip: 'Anterior (Ctrl+←)',
              ),
              // Dropdown de questão
              PopupMenuButton<int>(
                tooltip: 'Ir para questão',
                icon: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.swap_vert_rounded, size: 18),
                    const Gap(4),
                    Text('${_currentIndex + 1}/$total',
                        style: const TextStyle(fontSize: 13)),
                  ],
                ),
                itemBuilder: (_) => List.generate(
                  total,
                  (i) => PopupMenuItem<int>(
                    value: i,
                    child: Text(
                      'Q${i + 1}: ${ref.read(questionsProvider).questions[i].enunciado.take(40)}',
                      style: TextStyle(
                        fontWeight: i == _currentIndex ? FontWeight.w700 : null,
                        color: i == _currentIndex ? AppColors.primary : null,
                      ),
                    ),
                  ),
                ),
                onSelected: (i) {
                  _save();
                  if (i != _currentIndex) setState(() => _switchQuestion(i));
                },
              ),
              IconButton(
                icon: const Icon(Icons.chevron_right_rounded),
                onPressed: hasNext ? () => _navigate(1) : null,
                tooltip: 'Próxima (Ctrl+→)',
              ),
              const Gap(8),
              FilledButton.icon(
                onPressed: _save,
                icon: const Icon(Icons.save_rounded, size: 16),
                label: const Text('Salvar'),
              ),
              const Gap(16),
            ],
            bottom: TabBar(
              controller: _tabs,
              tabs: const [
                Tab(icon: Icon(Icons.edit_note_rounded, size: 18), text: 'Formulário'),
                Tab(icon: Icon(Icons.preview_rounded, size: 18), text: 'Preview'),
                Tab(icon: Icon(Icons.code_rounded, size: 18), text: 'JSON'),
              ],
            ),
          ),
          body: TabBarView(
            controller: _tabs,
            children: [
              _FormTab(
                // key garante que os sub-widgets stateful (StringListEditor,
                // KeyValueEditor) são recriados ao trocar de questão
                key: ValueKey(_currentIndex),
                question: _local,
                enunciadoCtrl: _enunciadoCtrl!,
                corretaCtrl: _corretaCtrl!,
                subenunciadoCtrl: _subenunciadoCtrl!,
                onChanged: (q) => setState(() => _local = q),
              ),
              _PreviewTab(question: _local),
              _RawJsonTab(question: _local),
            ],
          ),
        ),
      ),
    );
  }
}

// ── Aba Formulário ────────────────────────────────────────────────────────────

class _FormTab extends StatelessWidget {
  final Question question;
  final TextEditingController enunciadoCtrl;
  final TextEditingController corretaCtrl;
  final TextEditingController subenunciadoCtrl;
  final ValueChanged<Question> onChanged;

  const _FormTab({
    super.key,
    required this.question,
    required this.enunciadoCtrl,
    required this.corretaCtrl,
    required this.subenunciadoCtrl,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 900),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Linha 1: Tipo e Dificuldade ──
            Row(
              children: [
                Expanded(child: _buildTipoSelector(context)),
                const Gap(16),
                Expanded(child: _buildDificuldadeSelector(context)),
                const Gap(16),
                Expanded(child: _buildIdField(context)),
              ],
            ),
            const Gap(20),

            // ── Enunciado ──
            const _SectionLabel(label: 'Enunciado', icon: Icons.article_outlined),
            const Gap(8),
            TextFormField(
              controller: enunciadoCtrl,
              maxLines: 4,
              decoration: const InputDecoration(
                hintText: 'Texto da questão…',
              ),
            ),
            const Gap(20),

            // ── Subenunciado (opcional) ──
            const _SectionLabel(
                label: 'Subenunciado (opcional)',
                icon: Icons.subdirectory_arrow_right_rounded),
            const Gap(8),
            TextFormField(
              controller: subenunciadoCtrl,
              maxLines: 2,
              decoration: const InputDecoration(
                hintText: 'Texto complementar da questão…',
              ),
            ),
            const Gap(20),

            // ── Alternativas ──
            const _SectionLabel(
                label: 'Alternativas', icon: Icons.format_list_bulleted_rounded),
            const Gap(8),
            _StringListEditor(
              items: question.alternativas,
              hintText: 'Alternativa',
              onChanged: (alts) => onChanged(question.copyWith(alternativas: alts)),
            ),
            const Gap(20),

            // ── Resposta correta ──
            const _SectionLabel(
                label: 'Resposta correta', icon: Icons.check_circle_outline_rounded),
            const Gap(8),
            TextFormField(
              controller: corretaCtrl,
              decoration: const InputDecoration(
                hintText: 'Texto da alternativa correta…',
                prefixIcon: Icon(Icons.check_rounded,
                    color: AppColors.easy, size: 18),
              ),
            ),
            const Gap(20),

            // ── Imagens ──
            const _SectionLabel(
                label: 'Imagens (opcional)', icon: Icons.image_outlined),
            const Gap(8),
            _StringListEditor(
              items: question.imagens,
              hintText: 'caminho/imagem.png ou caminho.png|640x480',
              onChanged: (imgs) => onChanged(question.copyWith(imagens: imgs)),
            ),
            const Gap(20),

            // ── Afirmações (tipo 4) ──
            if (question.tipo == 4) ...[
              const _SectionLabel(
                  label: 'Afirmações (Tipo 4)',
                  icon: Icons.format_list_numbered_rounded),
              const Gap(8),
              _KeyValueEditor(
                data: question.afirmacoes,
                keyHint: 'I / II / III…',
                valueHint: 'Texto da afirmação',
                onChanged: (m) => onChanged(question.copyWith(afirmacoes: m)),
              ),
              const Gap(20),
            ],

            // ── Variáveis ──
            const _SectionLabel(
                label: 'Variáveis dinâmicas (opcional)',
                icon: Icons.functions_rounded),
            const Gap(4),
            Text(
              'Formato: NOME → min:step:max   ex: X → 1:0.5:10',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context)
                        .colorScheme
                        .onSurface
                        .withAlpha(130),
                  ),
            ),
            const Gap(8),
            _KeyValueEditor(
              data: question.variaveis,
              keyHint: 'NOME',
              valueHint: 'min:step:max',
              onChanged: (m) => onChanged(question.copyWith(variaveis: m)),
            ),
            const Gap(20),

            // ── Resoluções ──
            const _SectionLabel(
                label: 'Resoluções / Expressões (opcional)',
                icon: Icons.calculate_outlined),
            const Gap(4),
            Text(
              'Expressões aritméticas usando as variáveis. ex: SOMA → X + Y',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context)
                        .colorScheme
                        .onSurface
                        .withAlpha(130),
                  ),
            ),
            const Gap(8),
            _KeyValueEditor(
              data: question.resolucoes,
              keyHint: 'NOME',
              valueHint: 'expressão',
              onChanged: (m) => onChanged(question.copyWith(resolucoes: m)),
            ),
            const Gap(28),

            // ── OBS / Feedback ──
            ObsFeedbackPanel(
              obs: question.obs,
              editable: true,
              initiallyExpanded: true,
              onChanged: (obs) => onChanged(question.copyWith(obs: obs)),
            ),

            const Gap(40),
          ],
        ),
      ),
    );
  }

  Widget _buildTipoSelector(BuildContext context) {
    return DropdownButtonFormField<int>(
      initialValue: question.tipo,
      decoration: const InputDecoration(
        labelText: 'Tipo',
        prefixIcon: Icon(Icons.category_outlined, size: 18),
      ),
      items: const [
        DropdownMenuItem(value: 1, child: Text('1 – Texto')),
        DropdownMenuItem(value: 2, child: Text('2 – Imagem')),
        DropdownMenuItem(value: 3, child: Text('3 – Matemática')),
        DropdownMenuItem(value: 4, child: Text('4 – Afirmações')),
      ],
      onChanged: (v) => onChanged(question.copyWith(tipo: v)),
    );
  }

  Widget _buildDificuldadeSelector(BuildContext context) {
    return DropdownButtonFormField<String>(
      initialValue: question.dificuldade,
      decoration: const InputDecoration(
        labelText: 'Dificuldade',
        prefixIcon: Icon(Icons.speed_rounded, size: 18),
      ),
      items: const [
        DropdownMenuItem(value: 'fácil', child: Text('Fácil')),
        DropdownMenuItem(value: 'média', child: Text('Média')),
        DropdownMenuItem(value: 'difícil', child: Text('Difícil')),
      ],
      onChanged: (v) => onChanged(question.copyWith(dificuldade: v)),
    );
  }

  Widget _buildIdField(BuildContext context) {
    return TextFormField(
      initialValue: question.id?.toString() ?? '',
      keyboardType: TextInputType.number,
      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
      decoration: const InputDecoration(
        labelText: 'ID (opcional)',
        prefixIcon: Icon(Icons.tag_rounded, size: 18),
      ),
      onChanged: (v) =>
          onChanged(question.copyWith(id: v.isEmpty ? null : int.tryParse(v))),
    );
  }
}

// ── Aba Preview ───────────────────────────────────────────────────────────────

class _PreviewTab extends StatelessWidget {
  final Question question;
  const _PreviewTab({required this.question});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 800),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    AppColors.primary.withAlpha(20),
                    AppColors.secondary.withAlpha(10),
                  ],
                ),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  if (question.id != null)
                    Text(
                      'Q${question.id}',
                      style: theme.textTheme.titleLarge?.copyWith(
                        color: AppColors.primary,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  if (question.id != null) const Gap(12),
                  Expanded(
                    child: Text(
                      question.enunciado,
                      style: theme.textTheme.bodyLarge?.copyWith(
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                  const Gap(12),
                  DifficultyBadge(dificuldade: question.dificuldade),
                ],
              ),
            ),

            if (question.subenunciado != null) ...[
              const Gap(12),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4),
                child: Text(
                  question.subenunciado!,
                  style: theme.textTheme.bodyMedium
                      ?.copyWith(fontStyle: FontStyle.italic),
                ),
              ),
            ],

            // Afirmações (tipo 4)
            if (question.afirmacoes.isNotEmpty) ...[
              const Gap(16),
              ...question.afirmacoes.entries.map(
                (e) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('${e.key}. ',
                          style: theme.textTheme.bodyMedium
                              ?.copyWith(fontWeight: FontWeight.w700)),
                      Expanded(child: Text(e.value)),
                    ],
                  ),
                ),
              ),
            ],

            // Alternativas
            if (question.alternativas.isNotEmpty) ...[
              const Gap(16),
              ...question.alternativas.asMap().entries.map((e) {
                final label =
                    String.fromCharCode('a'.codeUnitAt(0) + e.key);
                final isCorrect = e.value == question.correta;
                return Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding:
                      const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  decoration: BoxDecoration(
                    color: isCorrect
                        ? AppColors.easy.withAlpha(25)
                        : theme.colorScheme.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: isCorrect
                          ? AppColors.easy.withAlpha(100)
                          : theme.colorScheme.outlineVariant,
                    ),
                  ),
                  child: Row(
                    children: [
                      Text(
                        '$label)',
                        style: TextStyle(
                          fontWeight: FontWeight.w700,
                          color: isCorrect ? AppColors.easy : null,
                        ),
                      ),
                      const Gap(10),
                      Expanded(
                        child: Text(
                          e.value,
                          style: TextStyle(
                            color: isCorrect ? AppColors.easy : null,
                            fontWeight:
                                isCorrect ? FontWeight.w600 : FontWeight.normal,
                          ),
                        ),
                      ),
                      if (isCorrect)
                        const Icon(Icons.check_circle_rounded,
                            color: AppColors.easy, size: 16),
                    ],
                  ),
                );
              }),
            ],

            const Gap(24),

            // Feedback / OBS
            ObsFeedbackPanel(
              obs: question.obs,
              initiallyExpanded: true,
            ),

            if (question.variaveis.isNotEmpty) ...[
              const Gap(24),
              _InfoSection(
                label: 'Variáveis dinâmicas',
                icon: Icons.functions_rounded,
                color: AppColors.tertiary,
                content: question.variaveis.entries
                    .map((e) => '${e.key} ∈ [${e.value}]')
                    .join('\n'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _InfoSection extends StatelessWidget {
  final String label;
  final IconData icon;
  final Color color;
  final String content;

  const _InfoSection({
    required this.label,
    required this.icon,
    required this.color,
    required this.content,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withAlpha(15),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withAlpha(60)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 16, color: color),
              const Gap(8),
              Text(
                label,
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: 13,
                  color: color,
                ),
              ),
            ],
          ),
          const Gap(8),
          Text(content,
              style: const TextStyle(
                  fontFamily: 'monospace', fontSize: 12, height: 1.6)),
        ],
      ),
    );
  }
}

// ── Aba JSON ──────────────────────────────────────────────────────────────────

class _RawJsonTab extends StatelessWidget {
  final Question question;
  const _RawJsonTab({required this.question});

  @override
  Widget build(BuildContext context) {
    final json = const JsonEncoder.withIndent('  ').convert(question.toJson());
    return Stack(
      children: [
        SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: SelectableText(
            json,
            style: const TextStyle(
              fontFamily: 'monospace',
              fontSize: 13,
              height: 1.6,
            ),
          ),
        ),
        Positioned(
          top: 16,
          right: 16,
          child: IconButton.filled(
            onPressed: () {
              Clipboard.setData(ClipboardData(text: json));
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('JSON copiado!'),
                  duration: Duration(seconds: 2),
                ),
              );
            },
            icon: const Icon(Icons.copy_rounded, size: 18),
            tooltip: 'Copiar JSON',
            style: IconButton.styleFrom(backgroundColor: AppColors.primary),
          ),
        ),
      ],
    );
  }
}

// ── Widgets auxiliares ────────────────────────────────────────────────────────

class _SectionLabel extends StatelessWidget {
  final String label;
  final IconData icon;

  const _SectionLabel({required this.label, required this.icon});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 16, color: AppColors.primary),
        const Gap(8),
        Text(
          label,
          style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: AppColors.primary,
              ),
        ),
      ],
    );
  }
}

class _StringListEditor extends StatefulWidget {
  final List<String> items;
  final String hintText;
  final ValueChanged<List<String>> onChanged;

  const _StringListEditor({
    required this.items,
    required this.hintText,
    required this.onChanged,
  });

  @override
  State<_StringListEditor> createState() => _StringListEditorState();
}

class _StringListEditorState extends State<_StringListEditor> {
  late List<TextEditingController> _controllers;

  @override
  void initState() {
    super.initState();
    _controllers = widget.items
        .map((s) => TextEditingController(text: s))
        .toList();
    if (_controllers.isEmpty) _controllers.add(TextEditingController());
  }

  @override
  void dispose() {
    for (final c in _controllers) {
      c.dispose();
    }
    super.dispose();
  }

  void _notify() {
    widget.onChanged(
        _controllers.map((c) => c.text).where((s) => s.isNotEmpty).toList());
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        ..._controllers.asMap().entries.map(
              (e) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  children: [
                    Container(
                      width: 24,
                      height: 24,
                      decoration: BoxDecoration(
                        color: AppColors.primary.withAlpha(20),
                        shape: BoxShape.circle,
                      ),
                      child: Center(
                        child: Text(
                          String.fromCharCode(
                              'a'.codeUnitAt(0) + e.key),
                          style: const TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                            color: AppColors.primary,
                          ),
                        ),
                      ),
                    ),
                    const Gap(8),
                    Expanded(
                      child: TextField(
                        controller: e.value,
                        onChanged: (_) => _notify(),
                        decoration: InputDecoration(
                          hintText: '${widget.hintText} ${e.key + 1}',
                          isDense: true,
                        ),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.remove_circle_outline_rounded,
                          size: 18, color: AppColors.hard),
                      onPressed: () {
                        setState(() => _controllers.removeAt(e.key)..dispose());
                        _notify();
                      },
                      padding: EdgeInsets.zero,
                      constraints:
                          const BoxConstraints(minWidth: 32, minHeight: 32),
                    ),
                  ],
                ),
              ),
            ),
        TextButton.icon(
          onPressed: () {
            setState(() => _controllers.add(TextEditingController()));
          },
          icon: const Icon(Icons.add_rounded, size: 16),
          label: Text('Adicionar ${widget.hintText.toLowerCase()}'),
          style: TextButton.styleFrom(foregroundColor: AppColors.primary),
        ),
      ],
    );
  }
}

class _KeyValueEditor extends StatefulWidget {
  final Map<String, String> data;
  final String keyHint;
  final String valueHint;
  final ValueChanged<Map<String, String>> onChanged;

  const _KeyValueEditor({
    required this.data,
    required this.keyHint,
    required this.valueHint,
    required this.onChanged,
  });

  @override
  State<_KeyValueEditor> createState() => _KeyValueEditorState();
}

class _KeyValueEditorState extends State<_KeyValueEditor> {
  late List<(TextEditingController, TextEditingController)> _pairs;

  @override
  void initState() {
    super.initState();
    _pairs = widget.data.entries
        .map((e) => (
              TextEditingController(text: e.key),
              TextEditingController(text: e.value),
            ))
        .toList();
  }

  @override
  void dispose() {
    for (final (k, v) in _pairs) {
      k.dispose();
      v.dispose();
    }
    super.dispose();
  }

  void _notify() {
    final map = <String, String>{};
    for (final (k, v) in _pairs) {
      if (k.text.isNotEmpty) map[k.text] = v.text;
    }
    widget.onChanged(map);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        ..._pairs.asMap().entries.map(
              (e) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  children: [
                    Expanded(
                      flex: 2,
                      child: TextField(
                        controller: e.value.$1,
                        onChanged: (_) => _notify(),
                        decoration: InputDecoration(
                          hintText: widget.keyHint,
                          isDense: true,
                        ),
                      ),
                    ),
                    const Padding(
                      padding: EdgeInsets.symmetric(horizontal: 8),
                      child: Text('→',
                          style: TextStyle(fontWeight: FontWeight.w700)),
                    ),
                    Expanded(
                      flex: 3,
                      child: TextField(
                        controller: e.value.$2,
                        onChanged: (_) => _notify(),
                        decoration: InputDecoration(
                          hintText: widget.valueHint,
                          isDense: true,
                        ),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.remove_circle_outline_rounded,
                          size: 18, color: AppColors.hard),
                      onPressed: () {
                        setState(() {
                          final pair = _pairs.removeAt(e.key);
                          pair.$1.dispose();
                          pair.$2.dispose();
                        });
                        _notify();
                      },
                      padding: EdgeInsets.zero,
                      constraints:
                          const BoxConstraints(minWidth: 32, minHeight: 32),
                    ),
                  ],
                ),
              ),
            ),
        TextButton.icon(
          onPressed: () {
            setState(() => _pairs.add((
                  TextEditingController(),
                  TextEditingController(),
                )));
          },
          icon: const Icon(Icons.add_rounded, size: 16),
          label: const Text('Adicionar par'),
          style: TextButton.styleFrom(foregroundColor: AppColors.primary),
        ),
      ],
    );
  }
}

// ── Extension helper ──────────────────────────────────────────────────────────

extension StringTruncate on String {
  String take(int max) => length > max ? '${substring(0, max)}…' : this;
}
