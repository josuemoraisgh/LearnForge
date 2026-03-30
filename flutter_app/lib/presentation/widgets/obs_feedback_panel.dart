import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../theme/app_theme.dart';

/// Painel que exibe as observações/feedback de uma questão.
/// O campo `obs` contém comentários exibidos após a resolução — como gabarito
/// comentado ou dica didática. Exportado como generalfeedback no Moodle XML
/// e como frame OBS no Beamer.
class ObsFeedbackPanel extends StatefulWidget {
  final List<String> obs;
  final bool initiallyExpanded;
  final bool editable;
  final ValueChanged<List<String>>? onChanged;

  const ObsFeedbackPanel({
    super.key,
    required this.obs,
    this.initiallyExpanded = false,
    this.editable = false,
    this.onChanged,
  });

  @override
  State<ObsFeedbackPanel> createState() => _ObsFeedbackPanelState();
}

class _ObsFeedbackPanelState extends State<ObsFeedbackPanel> {
  late bool _expanded;
  late List<TextEditingController> _controllers;

  @override
  void initState() {
    super.initState();
    _expanded = widget.initiallyExpanded || widget.obs.isNotEmpty;
    _controllers = widget.obs
        .map((s) => TextEditingController(text: s))
        .toList();
  }

  @override
  void dispose() {
    for (final c in _controllers) {
      c.dispose();
    }
    super.dispose();
  }

  void _notifyChange() {
    widget.onChanged
        ?.call(_controllers.map((c) => c.text.trim()).where((s) => s.isNotEmpty).toList());
  }

  void _addItem() {
    setState(() => _controllers.add(TextEditingController()));
    _notifyChange();
  }

  void _removeItem(int index) {
    setState(() => _controllers.removeAt(index)..dispose());
    _notifyChange();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final hasObs = widget.obs.isNotEmpty || (widget.editable && _controllers.isNotEmpty);

    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      decoration: BoxDecoration(
        color: AppColors.secondary.withAlpha(12),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: AppColors.secondary.withAlpha(hasObs ? 80 : 40),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          InkWell(
            onTap: () => setState(() => _expanded = !_expanded),
            borderRadius: BorderRadius.circular(12),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: AppColors.secondary.withAlpha(30),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(
                      Icons.comment_rounded,
                      size: 16,
                      color: AppColors.secondary,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Feedback / Comentários',
                          style: theme.textTheme.labelLarge?.copyWith(
                            color: AppColors.secondary,
                          ),
                        ),
                        Text(
                          'Exibido após a resolução da questão',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.colorScheme.onSurface.withAlpha(120),
                            fontSize: 11,
                          ),
                        ),
                      ],
                    ),
                  ),
                  if (!widget.editable && widget.obs.isNotEmpty)
                    Container(
                      padding:
                          const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: AppColors.secondary.withAlpha(30),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        '${widget.obs.length}',
                        style: const TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: AppColors.secondary,
                        ),
                      ),
                    ),
                  const SizedBox(width: 8),
                  Icon(
                    _expanded
                        ? Icons.keyboard_arrow_up_rounded
                        : Icons.keyboard_arrow_down_rounded,
                    color: AppColors.secondary,
                    size: 20,
                  ),
                ],
              ),
            ),
          ),

          // Conteúdo expansível
          if (_expanded) ...[
            const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.all(16),
              child: widget.editable
                  ? _buildEditor(theme)
                  : _buildReadOnly(theme),
            ),
          ],
        ],
      ),
    ).animate().fadeIn(duration: 200.ms);
  }

  Widget _buildReadOnly(ThemeData theme) {
    if (widget.obs.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: Text(
            'Nenhum feedback cadastrado',
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurface.withAlpha(100),
              fontStyle: FontStyle.italic,
            ),
          ),
        ),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: widget.obs
          .asMap()
          .entries
          .map(
            (e) => Padding(
              padding: EdgeInsets.only(bottom: e.key < widget.obs.length - 1 ? 8 : 0),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    margin: const EdgeInsets.only(top: 4, right: 10),
                    width: 6,
                    height: 6,
                    decoration: const BoxDecoration(
                      color: AppColors.secondary,
                      shape: BoxShape.circle,
                    ),
                  ),
                  Expanded(
                    child: Text(
                      e.value,
                      style: theme.textTheme.bodyMedium,
                    ),
                  ),
                ],
              ),
            ),
          )
          .toList(),
    );
  }

  Widget _buildEditor(ThemeData theme) {
    return Column(
      children: [
        ..._controllers.asMap().entries.map((e) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: e.value,
                      onChanged: (_) => _notifyChange(),
                      maxLines: 2,
                      decoration: InputDecoration(
                        hintText: 'Item de feedback ${e.key + 1}',
                        isDense: true,
                      ),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.remove_circle_outline_rounded,
                        color: AppColors.hard),
                    onPressed: () => _removeItem(e.key),
                    tooltip: 'Remover',
                  ),
                ],
              ),
            )),
        const SizedBox(height: 4),
        TextButton.icon(
          onPressed: _addItem,
          icon: const Icon(Icons.add_rounded, size: 16),
          label: const Text('Adicionar feedback'),
          style: TextButton.styleFrom(foregroundColor: AppColors.secondary),
        ),
      ],
    );
  }
}
